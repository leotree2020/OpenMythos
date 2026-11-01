"""CPU decoding controls using only the official model forward implementation.

Token selection uses a separate CPU Generator. The model's default CPU RNG is
seeded once per complete continuation; no model forward or buffer is patched.
No numerical dependency is imported at module import time.
"""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import traceback


VOCAB_SIZE = 32768
NUM_STEPS = 8
MAX_NEW_TOKENS = 64
MODEL_SEED_BASE = 731000
SAMPLER_SEED_BASE = 841000
EOS_ID = 1  # Established by the separate frozen tokenizer validation.
CHUNK_BYTES = 1024 * 1024
PROBABILITY_SUM_TOLERANCE = 1e-6
POLICIES = {
    "G": {"temperature": 1.0, "top_p": None, "sample": False},
    "S": {"temperature": 1.0, "top_p": None, "sample": True},
    "P": {"temperature": 0.8, "top_p": 0.9, "sample": True},
}


class GenerationStop(RuntimeError):
    def __init__(self, status, reason, actual=None, phase="D2"):
        super().__init__(reason)
        self.status = status
        self.reason = reason
        self.actual = actual
        self.phase = phase


def _json_bytes(value):
    # Matches the frozen historical prefix hashing convention exactly.
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       allow_nan=False) + "\n").encode("utf-8")


def _save_json(path, value):
    with path.open("xb") as stream:
        stream.write(_json_bytes(value))
        stream.flush()
        os.fsync(stream.fileno())


def _append_json(stream, value):
    stream.write(_json_bytes(value))
    stream.flush()
    os.fsync(stream.fileno())


def _read_json(path):
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def _file_digest(path):
    digest = hashlib.sha256()
    total = 0
    with path.open("rb") as stream:
        while True:
            block = stream.read(CHUNK_BYTES)
            if not block:
                break
            digest.update(block)
            total += len(block)
    return {"sha256": digest.hexdigest(), "bytes": total}


def _byte_compare(left, right, expected_bytes):
    lengths = {"left_bytes": left.stat().st_size, "right_bytes": right.stat().st_size,
               "expected_bytes": expected_bytes}
    if lengths["left_bytes"] != expected_bytes or lengths["right_bytes"] != expected_bytes:
        return {"equal": False, "compared_bytes": 0, **lengths}
    compared = 0
    with left.open("rb") as first, right.open("rb") as second:
        while True:
            a, b = first.read(CHUNK_BYTES), second.read(CHUNK_BYTES)
            if a != b:
                return {"equal": False, "compared_bytes": compared, **lengths}
            if not a:
                break
            compared += len(a)
    return {"equal": compared == expected_bytes, "compared_bytes": compared, **lengths}


def _tensor_digest(torch, tensor, path=None):
    raw = tensor.detach().contiguous().reshape(-1).view(torch.uint8)
    digest = hashlib.sha256()
    count = 0
    stream = path.open("xb") if path is not None else None
    try:
        for start in range(0, raw.numel(), CHUNK_BYTES):
            view = raw[start:start + CHUNK_BYTES]
            block = view.numpy().tobytes(order="C")
            if len(block) != view.numel():
                raise GenerationStop("FAIL", "raw tensor block length is inconsistent")
            count += len(block)
            digest.update(block)
            if stream is not None:
                stream.write(block)
        if stream is not None:
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        if stream is not None:
            stream.close()
    expected = tensor.numel() * tensor.element_size()
    if count != expected:
        raise GenerationStop("FAIL", "raw tensor byte coverage is incomplete",
                             {"bytes": count, "expected": expected})
    return {"sha256": digest.hexdigest(), "bytes": count}


def _rng_state(torch, generator=None):
    state = torch.get_rng_state() if generator is None else generator.get_state()
    return state.contiguous().numpy().tobytes(order="C")


def _rng_digest(raw):
    return None if raw is None else {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


def _quality_loader():
    """Explicitly load the frozen sibling's pure quality helper, never its runner."""
    path = Path(__file__).resolve().parent.parent / "cpu_inference_v1" / "tokenizer_checks.py"
    name = "mythos_decode_frozen_quality_helper"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GenerationStop("BLOCKED", "frozen quality helper cannot be resolved", str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module.compute_quality, {"path": str(path), **_file_digest(path)}


def run_generation(torch, model, tokenizer, prompts, output, history):
    """Execute G12, then S/P x three panels x 12 prompts exactly once.

    history is the frozen first/inference directory, including public and private
    evidence. Only engineering failures stop computation. Quality is descriptive
    until all 84 outputs and the later external AI review have been collected.
    """
    output, history = Path(output), Path(history)
    output.mkdir(exist_ok=False)
    public, private = output / "public", output / "private"
    public.mkdir()
    private.mkdir()
    phase = "D2"
    summary = {
        "status": "NOT TESTED", "gates": {"D2": "NOT TESTED", "D3": "NOT TESTED"},
        "history": str(history), "policies": POLICIES, "conditions_expected": 84,
        "forward_calls_expected": 5376, "official_forward_calls": 0,
        "official_generate_calls": 0, "checks": 0, "conditions": [],
        "model_seed_formula": "731000 + prompt_id",
        "sampler_seed_formula": "841000 + 100 * panel + prompt_id; S/P share seeds",
        "schedule": "G prompts1..12; S panels1..3/prompts1..12; P panels1..3/prompts1..12",
        "quality_status": "PENDING AI REVIEW", "quality_rule": "each of three panels joint >=9/12",
        "sampling_repeatability": "NOT TESTED; no additional replay",
        "default_rng_reference": "exact per-step bytes from current G control, also saved privately",
    }
    checks = (public / "checks.jsonl").open("xb")
    greedy_rng = {}
    greedy_traces = {}

    def require(ok, purpose, actual, expected=True, failure="FAIL", identity=None):
        row = {
            "Purpose": purpose,
            "Environment": {"pid": os.getpid(), "device": "cpu", "dtype": "float32",
                            "backend": "MATH", "batch_size": 1, "num_steps": NUM_STEPS,
                            "grad_enabled": False},
            "Input": identity if identity is not None else "frozen model, inputs, and history",
            "Expected": expected, "Actual": actual, "Status": "PASS" if ok else failure,
            "phase": phase,
        }
        _append_json(checks, row)
        summary["checks"] += 1
        if not ok:
            raise GenerationStop(failure, purpose, actual, phase)

    def logits_check(logits, length, identity):
        require(isinstance(logits, torch.Tensor), "official forward returns tensor logits",
                type(logits).__name__, identity=identity)
        actual = {"shape": list(logits.shape), "dtype": str(logits.dtype),
                  "device": str(logits.device), "layout": str(logits.layout),
                  "grad_enabled": torch.is_grad_enabled(), "requires_grad": logits.requires_grad}
        expected = {"shape": [1, length, VOCAB_SIZE], "dtype": "torch.float32", "device": "cpu",
                    "layout": "torch.strided", "grad_enabled": False, "requires_grad": False}
        require(actual == expected, "complete FP32 CPU logits metadata", actual, expected, identity=identity)
        finite = bool(torch.isfinite(logits).all().item())
        require(finite, "all unfiltered model logits finite", finite, identity=identity)

    def select_token(last, policy, generator, identity):
        config = POLICIES[policy]
        if policy == "G":
            return int(last.argmax(dim=-1).item()), {
                "method": "argmax", "temperature": 1.0, "top_p": None,
                "filtered_tokens": 0, "sampler_used": False,
            }
        require(generator is not None and str(generator.device) == "cpu",
                "dedicated CPU sampling generator", str(getattr(generator, "device", None)),
                "cpu", identity=identity)
        # Division creates a separate tensor, so masking never changes model logits.
        selection_logits = last / config["temperature"]
        scaled_finite = bool(torch.isfinite(selection_logits).all().item())
        require(scaled_finite, "temperature-scaled logits remain finite", scaled_finite, identity=identity)
        masked = torch.zeros_like(selection_logits, dtype=torch.bool)
        if config["top_p"] is not None:
            # Same ordering, right-shift and scatter semantics as pinned upstream.
            sorted_logits, sorted_indices = torch.sort(selection_logits, descending=True)
            cumulative = torch.cumsum(torch.nn.functional.softmax(sorted_logits, dim=-1), dim=-1)
            sorted_mask = cumulative > config["top_p"]
            sorted_mask[:, 1:] = sorted_mask[:, :-1].clone()
            sorted_mask[:, 0] = False
            masked = sorted_mask.scatter(1, sorted_indices, sorted_mask)
            selection_logits[masked] = float("-inf")
        filtered_count = int(masked.sum().item())
        allowed = (torch.isfinite(selection_logits) & ~masked) | (torch.isneginf(selection_logits) & masked)
        require(bool(allowed.all().item()) and filtered_count < VOCAB_SIZE,
                "only explicitly masked logits may be negative infinity",
                {"allowed": bool(allowed.all().item()), "filtered_tokens": filtered_count},
                identity=identity)
        probabilities = torch.nn.functional.softmax(selection_logits, dim=-1)
        finite_nonnegative = bool((torch.isfinite(probabilities) & (probabilities >= 0)).all().item())
        require(finite_nonnegative, "sampling probabilities finite and nonnegative",
                finite_nonnegative, identity=identity)
        probability_sum = float(probabilities.double().sum().item())
        require(abs(probability_sum - 1.0) <= PROBABILITY_SUM_TOLERANCE,
                "probability mass normalized before sampling", probability_sum,
                {"target": 1.0, "absolute_tolerance": PROBABILITY_SUM_TOLERANCE}, identity=identity)
        probability_record = _tensor_digest(torch, probabilities)
        sampled = torch.multinomial(probabilities, num_samples=1, generator=generator)
        token = int(sampled.item())
        require(0 <= token < VOCAB_SIZE and not bool(masked[0, token].item()),
                "sampled token belongs to retained vocabulary", token, identity=identity)
        return token, {"method": "multinomial", "temperature": config["temperature"],
                       "top_p": config["top_p"], "filtered_tokens": filtered_count,
                       "retained_tokens": VOCAB_SIZE - filtered_count,
                       "probability_sum_fp64": probability_sum,
                       "probabilities": probability_record, "sampler_used": True}

    def run_condition(prompt, policy, panel):
        prompt_id = prompt["id"]
        sampler_seed = (SAMPLER_SEED_BASE + 100 * panel + prompt_id) if policy != "G" else None
        identity = {"policy": policy, "panel": panel, "prompt_id": prompt_id,
                    "model_seed": prompt["seed"], "sampler_seed": sampler_seed}
        stem = "%s_panel%d_prompt%02d" % (policy, panel, prompt_id)
        trace_path = public / (stem + "_trace.jsonl")
        historical = None
        if policy == "G":
            with (history / "public" / ("pass1_prompt%02d_trace.jsonl" % prompt_id)).open("r", encoding="utf-8") as stream:
                historical = [json.loads(line) for line in stream]
            require(len(historical) == MAX_NEW_TOKENS and
                    [row.get("step") for row in historical] == list(range(MAX_NEW_TOKENS)),
                    "historical greedy trace complete and ordered", {"rows": len(historical)},
                    MAX_NEW_TOKENS, failure="BLOCKED", identity=identity)
        else:
            require(prompt_id in greedy_rng and len(greedy_rng[prompt_id]) == MAX_NEW_TOKENS,
                    "completed greedy RNG control available before sampling", prompt_id,
                    failure="BLOCKED", identity=identity)
        generator = None
        if policy != "G":
            generator = torch.Generator(device="cpu")
            generator.manual_seed(sampler_seed)
        prefix = list(prompt["input_ids"])
        condition_rows = []
        rng_rows = []
        trace_stream = None
        rng_stream = None
        primary_error = None
        cleanup_errors = []
        try:
            trace_stream = trace_path.open("xb")
            rng_stream = (private / (stem + "_default_rng.bin")).open("xb") if policy == "G" else None
            # Exactly one reset per complete continuation, after generator setup.
            torch.manual_seed(prompt["seed"])
            for step in range(MAX_NEW_TOKENS):
                info = {**identity, "step": step}
                x = torch.tensor([prefix], dtype=torch.long, device="cpu")
                default_before = _rng_state(torch)
                sampler_before = _rng_state(torch, generator) if generator is not None else None
                if policy != "G":
                    expected_before, expected_after = greedy_rng[prompt_id][step]
                    require(default_before == expected_before,
                            "model default RNG before forward matches greedy exact bytes",
                            {"actual": _rng_digest(default_before), "greedy": _rng_digest(expected_before)},
                            identity=info)
                summary["official_forward_calls"] += 1
                result = model.forward_for_generation(x, num_steps=NUM_STEPS,
                                                      attention_mask=None, past_key_values=None)
                default_after_forward = _rng_state(torch)
                sampler_after_forward = _rng_state(torch, generator) if generator is not None else None
                require(sampler_before == sampler_after_forward,
                        "model forward does not consume the dedicated sampler RNG",
                        {"before": _rng_digest(sampler_before), "after": _rng_digest(sampler_after_forward)},
                        identity=info)
                if policy != "G":
                    require(default_after_forward == expected_after,
                            "model default RNG after forward matches greedy exact bytes",
                            {"actual": _rng_digest(default_after_forward), "greedy": _rng_digest(expected_after)},
                            identity=info)
                require(isinstance(result, dict) and "logits" in result,
                        "official forward output structure", type(result).__name__, identity=info)
                logits = result["logits"]
                logits_check(logits, len(prefix), info)
                require(result.get("past_key_values") is None, "no cache created by official forward",
                        result.get("past_key_values") is None, identity=info)
                full = _tensor_digest(torch, logits)
                last_path = private / (stem + "_step%02d_last.bin" % step)
                last = _tensor_digest(torch, logits[:, -1, :], last_path)
                require(last["bytes"] == VOCAB_SIZE * 4, "complete last-position vector saved",
                        last["bytes"], VOCAB_SIZE * 4, identity=info)
                prefix_hash = hashlib.sha256(_json_bytes(prefix)).hexdigest()
                # Immutable pre-selection record preserves evidence even if a
                # subsequent bridge, selector, or RNG guard stops this condition.
                observation = {**info, "prefix_ids": list(prefix), "prefix_ids_sha256": prefix_hash,
                               "prefix_hash_encoding": "UTF-8 json.dumps(sort_keys=True, ensure_ascii=False) plus LF",
                               "input_length": len(prefix), "full_logits_shape": list(logits.shape),
                               "dtype": str(logits.dtype), "cache_none": True, "num_steps": NUM_STEPS,
                               "all_logits_finite": True, "full_logits": full, "last_logits": last,
                               "last_logits_file": "private/" + last_path.name,
                               "default_rng_before_forward": _rng_digest(default_before),
                               "default_rng_after_forward": _rng_digest(default_after_forward),
                               "sampler_rng_before_forward": _rng_digest(sampler_before),
                               "sampler_rng_after_forward": _rng_digest(sampler_after_forward)}
                _save_json(public / (stem + "_step%02d_observation.json" % step), observation)
                if policy == "G":
                    baseline = historical[step]
                    bridge_keys = ("prefix_ids_sha256", "input_length", "full_logits_shape",
                                   "dtype", "cache_none", "num_steps", "full_logits", "last_logits")
                    mismatches = [key for key in bridge_keys if observation[key] != baseline.get(key)]
                    require(not mismatches, "greedy adapter reproduces full historical logits and prefix trace",
                            {"mismatches": mismatches}, [], identity=info)
                    exact = _byte_compare(last_path, history / "private" / (
                        "pass1_prompt%02d_step%02d_last.bin" % (prompt_id, step)), VOCAB_SIZE * 4)
                    require(exact["equal"], "greedy last logits equal historical actual bytes",
                            exact, "byte equality, not only hashes", identity=info)
                elif step == 0:
                    # Identical initial prompt and h0 stream precede token policy.
                    first_g = greedy_traces[prompt_id][0]
                    require(full == first_g["full_logits"],
                            "sampling starts from the same full first-step logits as G",
                            {"actual": full, "greedy": first_g["full_logits"]}, identity=info)
                    exact = _byte_compare(last_path, private / (
                        "G_panel0_prompt%02d_step00_last.bin" % prompt_id), VOCAB_SIZE * 4)
                    require(exact["equal"], "sampling first-step last logits equal G actual bytes",
                            exact, identity=info)
                default_before_selector = _rng_state(torch)
                sampler_before_selector = _rng_state(torch, generator) if generator is not None else None
                require(default_before_selector == default_after_forward and
                        sampler_before_selector == sampler_after_forward,
                        "logit observation consumes neither RNG stream",
                        {"default_unchanged": default_before_selector == default_after_forward,
                         "sampler_unchanged": sampler_before_selector == sampler_after_forward}, identity=info)
                token, selection = select_token(logits[:, -1, :], policy, generator, info)
                default_after_selector = _rng_state(torch)
                sampler_after_selector = _rng_state(torch, generator) if generator is not None else None
                require(default_after_selector == default_before_selector,
                        "token selector never consumes the model default RNG",
                        {"before": _rng_digest(default_before_selector),
                         "after": _rng_digest(default_after_selector)}, identity=info)
                after_selection_last = _tensor_digest(torch, logits[:, -1, :])
                require(after_selection_last == last,
                        "token selector leaves original model logits unchanged",
                        {"before": last, "after": after_selection_last}, identity=info)
                if policy == "G":
                    require(token == historical[step].get("expected_greedy_token_id"),
                            "greedy token equals historical token", token,
                            historical[step].get("expected_greedy_token_id"), identity=info)
                    rng_rows.append((default_before, default_after_forward))
                    rng_stream.write(default_before)
                    rng_stream.write(default_after_forward)
                    rng_stream.flush()
                    os.fsync(rng_stream.fileno())
                require(0 <= token < VOCAB_SIZE, "selected token is in vocabulary", token, identity=info)
                row = {**observation, "selected_token_id": token, "selection": selection,
                       "default_rng_before_selector": _rng_digest(default_before_selector),
                       "default_rng_after_selector": _rng_digest(default_after_selector),
                       "sampler_rng_before_selector": _rng_digest(sampler_before_selector),
                       "sampler_rng_after_selector": _rng_digest(sampler_after_selector)}
                _append_json(trace_stream, row)
                condition_rows.append(row)
                prefix.append(token)
                # Includes serialization, checksum and bookkeeping after selection.
                end_default = _rng_state(torch)
                end_sampler = _rng_state(torch, generator) if generator is not None else None
                require(end_default == default_after_selector and end_sampler == sampler_after_selector,
                        "step evidence recording consumes neither RNG stream",
                        {"default_unchanged": end_default == default_after_selector,
                         "sampler_unchanged": end_sampler == sampler_after_selector}, identity=info)
        except BaseException as exc:
            primary_error = exc
        finally:
            for action, stream in (("close condition trace", trace_stream), ("close G RNG evidence", rng_stream)):
                if stream is not None:
                    try:
                        stream.close()
                    except BaseException as exc:
                        cleanup_errors.append({"action": action, "error": repr(exc), **identity})
        if cleanup_errors:
            summary.setdefault("cleanup_errors", []).extend(cleanup_errors)
        if primary_error is not None:
            status = getattr(primary_error, "status", "BLOCKED")
            if status not in ("FAIL", "BLOCKED"):
                status = "BLOCKED"
            raise GenerationStop(status, getattr(primary_error, "reason", str(primary_error)),
                                 {"first_failure": getattr(primary_error, "actual", None),
                                  "cleanup_errors": cleanup_errors}, phase) from primary_error
        if cleanup_errors:
            raise GenerationStop("BLOCKED", "Condition evidence cleanup failed", cleanup_errors, phase)
        require(len(condition_rows) == MAX_NEW_TOKENS and len(prefix) == len(prompt["input_ids"]) + MAX_NEW_TOKENS,
                "complete frozen 64-step continuation", {"steps": len(condition_rows), "tokens": len(prefix)},
                identity=identity)
        quality = compute_quality(tokenizer, prompt, prefix)
        quality["eos_positions_all_64"] = [i for i, token in enumerate(quality["raw_new_ids"]) if token == EOS_ID]
        generation = {**identity, "observed_steps": len(condition_rows), "quality": quality,
                      "trace": _file_digest(trace_path), "generation_structure_status": "PASS"}
        _save_json(public / (stem + "_generation.json"), generation)
        if policy == "G":
            old_generation = _read_json(history / "public" / ("pass1_prompt%02d_generation.json" % prompt_id))
            require(quality == old_generation.get("quality"),
                    "greedy tokens, text, EOS and automatic descriptors equal history",
                    {"equal": quality == old_generation.get("quality")}, identity=identity)
            greedy_rng[prompt_id] = rng_rows
            greedy_traces[prompt_id] = condition_rows
        summary["conditions"].append(generation)
        print("DECODE policy=%s panel=%d prompt=%02d steps=64 completed" %
              (policy, panel, prompt_id), flush=True)

    terminal_error = None
    try:
        compute_quality, helper_source = _quality_loader()
        summary["quality_helper"] = helper_source
        require([row.get("id") for row in prompts] == list(range(1, 13)),
                "twelve fixed prompts in order", [row.get("id") for row in prompts],
                list(range(1, 13)), failure="BLOCKED")
        for prompt in prompts:
            ids = prompt.get("input_ids")
            require(isinstance(ids, list) and bool(ids) and
                    all(type(token) is int and 0 <= token < VOCAB_SIZE for token in ids)
                    and len(ids) + MAX_NEW_TOKENS <= model.config.block_size
                    and prompt.get("seed") == MODEL_SEED_BASE + prompt["id"],
                    "validated prompt IDs, model seed and context limit",
                    {"prompt_id": prompt["id"], "seed": prompt.get("seed"),
                     "prompt_tokens": len(ids) if isinstance(ids, list) else None}, failure="BLOCKED")
        require(all(not module.training for module in model.modules()),
                "all model modules remain in evaluation mode", model.training, failure="BLOCKED")
        with torch.no_grad(), torch.nn.attention.sdpa_kernel(torch.nn.attention.SDPBackend.MATH):
            backend = {"math": torch.backends.cuda.math_sdp_enabled(),
                       "flash": torch.backends.cuda.flash_sdp_enabled(),
                       "efficient": torch.backends.cuda.mem_efficient_sdp_enabled(),
                       "cudnn": torch.backends.cuda.cudnn_sdp_enabled(), "grad": torch.is_grad_enabled()}
            require(backend == {"math": True, "flash": False, "efficient": False,
                                "cudnn": False, "grad": False},
                    "explicit CPU math-only no-grad context", backend, failure="BLOCKED")
            for prompt in prompts:
                run_condition(prompt, "G", 0)
            require(len(summary["conditions"]) == 12 and len(greedy_rng) == 12,
                    "all twelve historical greedy bridges complete before any sampling",
                    {"conditions": len(summary["conditions"]), "rng_controls": len(greedy_rng)})
            summary["gates"]["D2"] = "PASS"
            phase = "D3"
            for policy in ("S", "P"):
                for panel in (1, 2, 3):
                    for prompt in prompts:
                        run_condition(prompt, policy, panel)
            identities = [(row["policy"], row["panel"], row["prompt_id"]) for row in summary["conditions"]]
            require(len(identities) == 84 and len(set(identities)) == 84 and
                    summary["official_forward_calls"] == summary["forward_calls_expected"],
                    "complete unique 84-condition matrix without additional forwards",
                    {"conditions": len(identities), "unique": len(set(identities)),
                     "forwards": summary["official_forward_calls"]},
                    {"conditions": 84, "unique": 84, "forwards": 5376})
            summary["gates"]["D3"] = "PASS"
        summary["automatic_panels"] = {}
        for policy, panels in (("G", (0,)), ("S", (1, 2, 3)), ("P", (1, 2, 3))):
            summary["automatic_panels"][policy] = {
                str(panel): {"passed": sum(row["quality"]["auto"]["passed"] for row in summary["conditions"]
                                          if row["policy"] == policy and row["panel"] == panel),
                             "total": 12, "joint_after_ai_review": "NOT TESTED"}
                for panel in panels
            }
        summary["status"] = "PASS"
    except BaseException as exc:
        terminal_error = exc
        status = getattr(exc, "status", "BLOCKED")
        if status not in ("FAIL", "BLOCKED"):
            status = "BLOCKED"
        summary["status"] = status
        summary["gates"][phase] = status
        summary["stop"] = {"status": status, "phase": phase,
                           "reason": getattr(exc, "reason", str(exc)),
                           "actual": getattr(exc, "actual", None),
                           "exception_type": type(exc).__name__, "traceback": traceback.format_exc()}
    finally:
        try:
            checks.close()
        except BaseException as close_exc:
            detail = {"action": "close check stream", "error": repr(close_exc)}
            summary.setdefault("cleanup_errors", []).append(detail)
            if terminal_error is None:
                terminal_error = close_exc
                summary["status"] = "BLOCKED"
                summary["gates"][phase] = "BLOCKED"
                summary["stop"] = {"status": "BLOCKED", "phase": phase,
                                   "reason": "Check stream close failed", "actual": detail,
                                   "exception_type": type(close_exc).__name__}
            else:
                summary["stop"].setdefault("cleanup_errors", []).append(detail)
    # Terminal serialization happens after cleanup. An I/O failure may prevent
    # this file from being complete, but cannot replace the first numerical FAIL.
    try:
        _save_json(public / "summary.json", summary)
    except BaseException as save_exc:
        if terminal_error is None:
            terminal_error = save_exc
            summary["status"] = "BLOCKED"
            summary["gates"][phase] = "BLOCKED"
            summary["stop"] = {"status": "BLOCKED", "phase": phase,
                               "reason": "Terminal summary save failed", "actual": repr(save_exc),
                               "exception_type": type(save_exc).__name__}
        else:
            summary["stop"]["terminal_save_error"] = repr(save_exc)
    if terminal_error is not None:
        raise GenerationStop(summary["status"], summary["stop"]["reason"],
                             summary["stop"], phase) from terminal_error
    return summary
