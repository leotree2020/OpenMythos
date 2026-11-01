"""Frozen inference observations; numerical dependencies are supplied at runtime.

Only official model methods execute the model or generation loop. Temporary
observers return the original output object unchanged and are always removed.
"""

import hashlib
import json
import os
from pathlib import Path
import traceback


VOCAB_SIZE = 32768
NUM_STEPS = 8
MAX_NEW_TOKENS = 64
EOS_ID = 1  # Independently established by the mandatory tokenizer_checks gate.
SEED_BASE = 731000
CHUNK_BYTES = 1024 * 1024
FORWARD_IDS = (1, 4, 7)


class InferenceStop(RuntimeError):
    def __init__(self, status, reason, actual=None, phase="F2"):
        super().__init__(reason)
        self.status = status
        self.reason = reason
        self.actual = actual
        self.phase = phase


def _json_bytes(value):
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


def _compare_files(left, right, expected_bytes):
    """Actual bounded byte comparison; hashes never replace equality."""
    sizes = {"left_bytes": left.stat().st_size,
             "right_bytes": right.stat().st_size,
             "expected_bytes": expected_bytes}
    if sizes["left_bytes"] != expected_bytes or sizes["right_bytes"] != expected_bytes:
        return {"equal": False, "compared_bytes": 0, **sizes}
    compared = 0
    with left.open("rb") as a, right.open("rb") as b:
        while True:
            x, y = a.read(CHUNK_BYTES), b.read(CHUNK_BYTES)
            if x != y:
                return {"equal": False, "compared_bytes": compared, **sizes}
            if not x:
                break
            compared += len(x)
    return {"equal": compared == expected_bytes, "compared_bytes": compared, **sizes}


def _byte_chunks(torch, tensor):
    raw = tensor.detach().contiguous().reshape(-1).view(torch.uint8)
    for start in range(0, raw.numel(), CHUNK_BYTES):
        block = raw[start:start + CHUNK_BYTES]
        payload = block.numpy().tobytes(order="C")
        if len(payload) != block.numel():
            raise InferenceStop("FAIL", "tensor serialization block has wrong length")
        yield payload


def _tensor_digest(torch, tensor, output=None):
    digest = hashlib.sha256()
    total = 0
    stream = output.open("xb") if output is not None else None
    try:
        for block in _byte_chunks(torch, tensor):
            digest.update(block)
            total += len(block)
            if stream is not None:
                stream.write(block)
        if stream is not None:
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        if stream is not None:
            stream.close()
    expected = tensor.numel() * tensor.element_size()
    if total != expected:
        raise InferenceStop("FAIL", "tensor serialization coverage is incomplete",
                            {"actual_bytes": total, "expected_bytes": expected})
    return {"sha256": digest.hexdigest(), "bytes": total}


def _rng_bytes(torch):
    state = torch.get_rng_state()
    return state.contiguous().numpy().tobytes(order="C")


def _bound_identity(method):
    return (getattr(method, "__self__", None), getattr(method, "__func__", method))


def run_worker(torch, model, tokenizer, prompts, output_dir, reference_dir=None):
    """Two parent passes, or one child pass against reference/pass1.

    Every completed observation is flushed before proceeding. On failure a
    partial public summary is saved and an InferenceStop is raised; no retry.
    """
    from tokenizer_checks import compute_quality

    output_dir = Path(output_dir)
    reference_dir = Path(reference_dir) if reference_dir is not None else None
    output_dir.mkdir(exist_ok=False)
    public = output_dir / "public"
    private = output_dir / "private"
    public.mkdir()
    private.mkdir()
    summary = {
        "status": "NOT TESTED", "gates": {"F2": "NOT TESTED", "F3": "NOT TESTED"},
        "reference_dir": str(reference_dir) if reference_dir is not None else None,
        "pass_count_expected": 1 if reference_dir is not None else 2,
        "forward_rows": [], "generation_rows": [], "checks": 0,
        "model_generate_calls": 0, "observer_forward_calls": 0,
        "language_quality": "NOT ASSESSED", "training_restore": "NOT TESTED",
    }
    phase = "F2"
    check_stream = (public / "checks.jsonl").open("xb")

    def require(condition, purpose, actual, expected=True, failure="FAIL", input_info=None):
        row = {
            "Purpose": purpose,
            "Environment": {"device": "cpu", "dtype": "float32", "batch_size": 1,
                            "backend": "SDPBackend.MATH", "num_steps": NUM_STEPS,
                            "grad_enabled": False, "pid": os.getpid()},
            "Input": input_info if input_info is not None else "frozen model and fixed prompts",
            "Expected": expected, "Actual": actual,
            "Status": "PASS" if condition else failure, "phase": phase,
        }
        _append_json(check_stream, row)
        summary["checks"] += 1
        if not condition:
            raise InferenceStop(failure, purpose, actual, phase=phase)

    def rng_observe(callback, label, input_info):
        """Exclude the actual model forward from the observer RNG control."""
        before = _rng_bytes(torch)
        caught = None
        result = None
        try:
            result = callback()
        except BaseException as exc:
            caught = exc
        if caught is not None:
            # No further torch operation after a stopping observation.
            row = {"Purpose": label, "Environment": {"device": "cpu", "pid": os.getpid()},
                   "Input": input_info, "Expected": "CPU RNG bytes unchanged",
                   "Actual": {"before_sha256": hashlib.sha256(before).hexdigest(),
                              "after": "NOT TESTED: stopped after first failure"}, "Status": "NOT TESTED",
                   "phase": phase}
            try:
                _append_json(check_stream, row)
                summary["checks"] += 1
            except BaseException:
                pass  # Outer terminal evidence retains the original failure.
            raise caught
        after = _rng_bytes(torch)
        actual = {"unchanged": before == after,
                  "before_sha256": hashlib.sha256(before).hexdigest(),
                  "after_sha256": hashlib.sha256(after).hexdigest()}
        require(before == after, label, actual, "CPU RNG bytes unchanged", input_info=input_info)
        return result

    def logits_check(logits, length, label, input_info):
        require(isinstance(logits, torch.Tensor), label + ": tensor output",
                type(logits).__name__, input_info=input_info)
        actual = {"shape": list(logits.shape), "dtype": str(logits.dtype),
                  "device": str(logits.device), "layout": str(logits.layout),
                  "grad_enabled": torch.is_grad_enabled(), "requires_grad": logits.requires_grad}
        expected = {"shape": [1, length, VOCAB_SIZE], "dtype": "torch.float32",
                    "device": "cpu", "layout": "torch.strided",
                    "grad_enabled": False, "requires_grad": False}
        require(actual == expected, label + ": full logits metadata", actual, expected,
                input_info=input_info)
        finite = bool(torch.isfinite(logits).all().item())
        require(finite, label + ": all logits finite", finite, input_info=input_info)

    def read_json(path):
        with path.open("r", encoding="utf-8") as stream:
            return json.load(stream)

    def input_tensor(prompt):
        return torch.tensor([prompt["input_ids"]], dtype=torch.long, device="cpu")

    def forward_check(prompt):
        identity = {"prompt_id": prompt["id"], "seed": prompt["seed"],
                    "input_ids": prompt["input_ids"]}
        x = input_tensor(prompt)
        torch.manual_seed(prompt["seed"])
        native_output = model(x, return_logits=True, labels=None, num_steps_pair=[0, NUM_STEPS])
        require(isinstance(native_output, dict) and "logits" in native_output,
                "native forward returns logits", type(native_output).__name__, input_info=identity)
        native = native_output["logits"]
        logits_check(native, len(prompt["input_ids"]), "native forward", identity)
        native_path = private / ("forward_%02d.bin" % prompt["id"])
        native_info = _tensor_digest(torch, native, native_path)

        torch.manual_seed(prompt["seed"])
        generated_output = model.forward_for_generation(x, num_steps=NUM_STEPS,
                                                        attention_mask=None, past_key_values=None)
        require(isinstance(generated_output, dict) and "logits" in generated_output,
                "generation forward returns logits", type(generated_output).__name__, input_info=identity)
        generated = generated_output["logits"]
        logits_check(generated, len(prompt["input_ids"]), "generation forward", identity)
        require(generated_output.get("past_key_values") is None,
                "generation forward does not create a cache", generated_output.get("past_key_values") is None,
                input_info=identity)
        generated_path = private / ("forward_generation_%02d.bin" % prompt["id"])
        generated_info = _tensor_digest(torch, generated, generated_path)
        equality = _compare_files(native_path, generated_path, native_info["bytes"])
        row = {**identity, "native": native_info, "generation": generated_info,
               "byte_comparison": equality, "native_steps_pair": [0, NUM_STEPS],
               "generation_steps": NUM_STEPS, "cross_process": None}
        summary["forward_rows"].append(row)
        _save_json(public / ("forward_%02d.json" % prompt["id"]), row)
        require(equality["equal"], "native versus generation full logits byte equality",
                equality, "exact bytes, including signed zero", input_info=identity)
        if reference_dir is not None:
            baseline = reference_dir / "private" / native_path.name
            cross = _compare_files(native_path, baseline, native_info["bytes"])
            _save_json(public / ("forward_reload_%02d.json" % prompt["id"]), cross)
            row["cross_process"] = cross
            require(cross["equal"], "new-process full native logits byte equality",
                    cross, "exact bytes", input_info=identity)

    def generate_one(prompt, pass_number, baseline_dir):
        identity = {"prompt_id": prompt["id"], "seed": prompt["seed"], "pass": pass_number}
        stem = "pass%d_prompt%02d" % (pass_number, prompt["id"])
        trace_path = public / (stem + "_trace.jsonl")
        baseline_rows = None
        if baseline_dir is not None:
            baseline_trace = baseline_dir / "public" / ("pass1_prompt%02d_trace.jsonl" % prompt["id"])
            with baseline_trace.open("r", encoding="utf-8") as stream:
                baseline_rows = [json.loads(line) for line in stream]
            require(len(baseline_rows) == MAX_NEW_TOKENS and
                    [row.get("step") for row in baseline_rows] == list(range(MAX_NEW_TOKENS)),
                    "reference trace is complete and ordered", {"rows": len(baseline_rows)},
                    MAX_NEW_TOKENS, failure="BLOCKED", input_info=identity)

        original = model.forward_for_generation
        had_attribute = "forward_for_generation" in model.__dict__
        previous_attribute = model.__dict__.get("forward_for_generation")
        original_identity = _bound_identity(original)
        expected_prefix = list(prompt["input_ids"])
        step_count = 0
        trace_stream = trace_path.open("xb")

        def observed(*args, **kwargs):
            nonlocal step_count
            current_step = step_count
            info = {**identity, "step": current_step}

            def inspect_input():
                require(current_step < MAX_NEW_TOKENS and len(args) == 1,
                        "generation call count and positional input", {"step": current_step, "args": len(args)},
                        input_info=info)
                x = args[0]
                require(isinstance(x, torch.Tensor) and x.device.type == "cpu"
                        and x.dtype == torch.long and list(x.shape) == [1, len(expected_prefix)],
                        "full-prefix generation input metadata",
                        {"shape": list(x.shape) if isinstance(x, torch.Tensor) else None,
                         "dtype": str(getattr(x, "dtype", None)), "length": len(expected_prefix)},
                        input_info=info)
                require(x.tolist() == [expected_prefix], "generation uses the exact complete prefix",
                        {"matches": x.tolist() == [expected_prefix], "tokens": len(expected_prefix)},
                        input_info=info)
                require(kwargs.get("num_steps") == NUM_STEPS and kwargs.get("past_key_values") is None
                        and kwargs.get("attention_mask") is None,
                        "eight recurrences and no cache/mask", {"num_steps": kwargs.get("num_steps"),
                        "cache_none": kwargs.get("past_key_values") is None,
                        "mask_none": kwargs.get("attention_mask") is None}, input_info=info)

            rng_observe(inspect_input, "input observer preserves CPU RNG", info)
            # Actual forward consumes the model's original h0 randomness.
            outputs = original(*args, **kwargs)

            def inspect_output():
                require(isinstance(outputs, dict) and "logits" in outputs,
                        "observed forward returns logits", type(outputs).__name__, input_info=info)
                logits = outputs["logits"]
                logits_check(logits, len(expected_prefix), "observed generation", info)
                require(outputs.get("past_key_values") is None,
                        "observed generation retains no cache", outputs.get("past_key_values") is None,
                        input_info=info)
                full = _tensor_digest(torch, logits)
                last_path = private / (stem + "_step%02d_last.bin" % current_step)
                last = _tensor_digest(torch, logits[:, -1, :], last_path)
                require(last["bytes"] == VOCAB_SIZE * 4, "complete final-position FP32 logits saved",
                        last["bytes"], VOCAB_SIZE * 4, input_info=info)
                next_id = int(logits[:, -1, :].argmax(dim=-1).item())
                row = {**info, "input_length": len(expected_prefix),
                       "prefix_ids_sha256": hashlib.sha256(_json_bytes(expected_prefix)).hexdigest(),
                       "prefix_hash_encoding": "UTF-8 json.dumps(sort_keys=True, ensure_ascii=False) plus LF",
                       "dtype": str(logits.dtype), "num_steps": NUM_STEPS,
                       "cache_none": outputs.get("past_key_values") is None,
                       "full_logits_shape": list(logits.shape), "all_logits_finite": True,
                       "full_logits": full, "last_logits": last,
                       "last_logits_file": "private/" + last_path.name,
                       "expected_greedy_token_id": next_id}
                _append_json(trace_stream, row)
                if baseline_rows is not None:
                    baseline_row = baseline_rows[current_step]
                    require(row["input_length"] == baseline_row.get("input_length")
                            and row["full_logits_shape"] == baseline_row.get("full_logits_shape"),
                            "reference and current prefix/logits dimensions agree",
                            {"current_length": row["input_length"],
                             "reference_length": baseline_row.get("input_length")}, input_info=info)
                    require(row["full_logits"] == baseline_row.get("full_logits"),
                            "full logits SHA-256 trace exactly repeats",
                            {"current": full, "reference": baseline_row.get("full_logits")}, input_info=info)
                    reference_last = baseline_dir / "private" / (
                        "pass1_prompt%02d_step%02d_last.bin" % (prompt["id"], current_step))
                    exact = _compare_files(last_path, reference_last, VOCAB_SIZE * 4)
                    require(exact["equal"], "last-position logits actual bytes exactly repeat",
                            exact, "actual byte comparison, not only SHA-256", input_info=info)
                expected_prefix.append(next_id)

            rng_observe(inspect_output, "output observer preserves CPU RNG", info)
            step_count += 1
            summary["observer_forward_calls"] += 1
            return outputs  # Same object; logits and other return values are untouched.

        primary_error = None
        cleanup_errors = []
        restored = False
        restoration = {}
        try:
            model.forward_for_generation = observed
            # All input construction precedes the one seed reset for this call.
            x = input_tensor(prompt)
            torch.manual_seed(prompt["seed"])
            summary["model_generate_calls"] += 1
            result = model.generate(x, max_new_tokens=MAX_NEW_TOKENS,
                                    temperature=1.0, top_k=None, top_p=None,
                                    do_sample=False, num_steps=NUM_STEPS, use_cache=False)
        except BaseException as exc:
            primary_error = exc
        finally:
            try:
                if had_attribute:
                    model.forward_for_generation = previous_attribute
                else:
                    delattr(model, "forward_for_generation")
                restored = (("forward_for_generation" in model.__dict__) == had_attribute
                            and _bound_identity(model.forward_for_generation) == original_identity
                            and (not had_attribute or model.__dict__["forward_for_generation"] is previous_attribute))
            except BaseException as exc:cleanup_errors.append({"action":"restore method","error":repr(exc)})
            try:trace_stream.close()
            except BaseException as exc:cleanup_errors.append({"action":"close trace","error":repr(exc)})
            restoration = {"had_instance_attribute":had_attribute,"instance_attribute_after":"forward_for_generation" in model.__dict__,
                           "restored":restored,"cleanup_errors":list(cleanup_errors)}
            try:_save_json(public / (stem + "_restoration.json"),restoration)
            except BaseException as exc:cleanup_errors.append({"action":"save restoration","error":repr(exc)})
        if primary_error is not None:
            raise InferenceStop(getattr(primary_error,"status","BLOCKED"),getattr(primary_error,"reason",str(primary_error)),
                                {"first_failure":getattr(primary_error,"actual",None),"cleanup_errors":cleanup_errors},phase=phase) from primary_error
        if cleanup_errors:
            raise InferenceStop("BLOCKED","Observer cleanup/evidence failure",cleanup_errors,phase=phase)
        require(restored, "temporary observer restored exactly", restoration, input_info=identity)
        require(step_count == MAX_NEW_TOKENS, "exactly 64 official generation forwards",
                step_count, MAX_NEW_TOKENS, input_info=identity)
        require(isinstance(result, torch.Tensor) and result.dtype == torch.long
                and result.device.type == "cpu" and list(result.shape) == [1, len(expected_prefix)],
                "official generation result metadata",
                {"shape": list(result.shape) if isinstance(result, torch.Tensor) else None,
                 "dtype": str(getattr(result, "dtype", None))}, input_info=identity)
        full_ids = result[0].tolist()
        require(full_ids == expected_prefix, "official returned IDs match observed greedy tokens",
                {"matches": full_ids == expected_prefix, "tokens": len(full_ids)}, input_info=identity)
        quality = compute_quality(tokenizer, prompt, full_ids)
        quality["eos_positions_all_64"] = [i for i, token in enumerate(quality["raw_new_ids"]) if token == EOS_ID]
        generation = {"pass": pass_number, "prompt_id": prompt["id"],
                      "trace": _file_digest(trace_path), "observed_steps": step_count,
                      "quality": quality}
        _save_json(public / (stem + "_generation.json"), generation)
        summary["generation_rows"].append(generation)
        if baseline_dir is not None:
            baseline_generation = read_json(baseline_dir / "public" / (
                "pass1_prompt%02d_generation.json" % prompt["id"]))
            baseline_quality = baseline_generation.get("quality")
            require(quality == baseline_quality,
                    "raw token IDs, text, EOS and descriptive quality exactly repeat",
                    {"equal": quality == baseline_quality, "prompt_id": prompt["id"]},
                    "all structured quality fields exact", input_info=identity)
        print("INFERENCE pass=%d prompt=%02d steps=%d completed" %
              (pass_number, prompt["id"], step_count), flush=True)

    try:
        require([row.get("id") for row in prompts] == list(range(1, 13)),
                "twelve validated prompts in frozen order", [row.get("id") for row in prompts],
                list(range(1, 13)), failure="BLOCKED")
        for prompt in prompts:
            ids = prompt.get("input_ids")
            require(isinstance(ids, list) and bool(ids) and
                    all(type(token) is int and 0 <= token < VOCAB_SIZE for token in ids)
                    and len(ids) + MAX_NEW_TOKENS <= model.config.block_size
                    and prompt.get("seed") == SEED_BASE + prompt["id"],
                    "validated IDs, frozen seed and context allowance",
                    {"prompt_id": prompt["id"], "input_length": len(ids) if isinstance(ids, list) else None,
                     "seed": prompt.get("seed")}, failure="BLOCKED")
        require(all(not module.training for module in model.modules()),
                "all modules remain in evaluation mode", model.training, failure="BLOCKED")
        with torch.no_grad(), torch.nn.attention.sdpa_kernel(torch.nn.attention.SDPBackend.MATH):
            backend = {"math": torch.backends.cuda.math_sdp_enabled(),
                       "flash": torch.backends.cuda.flash_sdp_enabled(),
                       "efficient": torch.backends.cuda.mem_efficient_sdp_enabled(),
                       "cudnn": torch.backends.cuda.cudnn_sdp_enabled(),
                       "grad_enabled": torch.is_grad_enabled()}
            require(backend == {"math": True, "flash": False, "efficient": False,
                                "cudnn": False, "grad_enabled": False},
                    "explicit math-only no-grad inference context", backend, failure="BLOCKED")
            for prompt_id in FORWARD_IDS:
                forward_check(prompts[prompt_id - 1])
            summary["gates"]["F2"] = "PASS"
            phase = "F3"
            for pass_number in range(1, summary["pass_count_expected"] + 1):
                baseline = reference_dir if reference_dir is not None else (
                    output_dir if pass_number == 2 else None)
                for prompt in prompts:
                    generate_one(prompt, pass_number, baseline)
            expected_calls = summary["pass_count_expected"] * len(prompts) * MAX_NEW_TOKENS
            require(summary["observer_forward_calls"] == expected_calls,
                    "all official generation calls observed", summary["observer_forward_calls"], expected_calls)
            summary["gates"]["F3"] = "PASS"
        summary["status"] = "PASS"
        _save_json(public / "summary.json", summary)
        return summary
    except BaseException as exc:
        status = getattr(exc, "status", "BLOCKED")
        if status not in ("FAIL", "BLOCKED"):
            status = "BLOCKED"
        # Helpers may not know the current phase; the active stage is authoritative.
        summary["status"] = status
        summary["gates"][phase] = status
        summary["stop"] = {"phase": phase, "status": status,
                           "reason": getattr(exc, "reason", str(exc)),
                           "actual": getattr(exc, "actual", None),
                           "exception_type": type(exc).__name__, "traceback": traceback.format_exc()}
        try:_save_json(public / "summary.json", summary)
        except BaseException as save_exc:summary["stop"]["terminal_save_error"]=repr(save_exc)
        raise InferenceStop(status, summary["stop"]["reason"], summary["stop"], phase=phase) from exc
    finally:
        try:check_stream.close()
        except BaseException as close_exc:
            if summary["status"]=="PASS":raise InferenceStop("BLOCKED","Check stream close failed",repr(close_exc),phase=phase)
