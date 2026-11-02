"""Isolated CPU depth protocol. Never edits upstream or the original artifacts."""
import argparse
import datetime
import hashlib
import importlib.metadata
import itertools
import json
import math
import os
import platform
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time
import traceback


UPSTREAM = "69284c13746e849104f738d6d1a347b1f457df76"
WEIGHTS = "ed6eb306464dd0d694e9eacd58f7e06ac3e44b43cb7c5c79dbcb1543059c6621"
CONFIG = "5c8fc785c2f6dba67d0370ad715034860e3b22bfce850da825c06baa03923c13"
TOKENIZER = "e0021e26057088d68047dbe6e77e2ba1c9fe9ae45bae3df9d67d48c82405ea77"
SEEDS = (3101, 3202, 3303)
DEPTHS = (8, 16, 32)
INPUTS_SHA = "3abb324ea2876abb78e18d86ec257a9e1d388f9501bd8cdd6c99011ac11cf41e"
ORDERS = tuple(itertools.permutations(DEPTHS))
PARAMETER_COUNT = 144323136
PARAMETER_TENSORS = 61


class Stop(Exception):
    def __init__(self, status, reason, actual=None):
        super().__init__(reason)
        self.status, self.reason, self.actual = status, reason, actual


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def json_hash(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def file_info(path):
    digest = hashlib.sha256()
    size = 0
    with Path(path).open("rb") as source:
        for data in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(data)
            size += len(data)
    return {"bytes": size, "sha256": digest.hexdigest()}


def save(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def git(path, *args):
    result = subprocess.run(["git", "-C", str(path), *args], capture_output=True, text=True, timeout=30)
    if result.returncode:
        raise Stop("BLOCKED", "Git read failed", {"args": args, "stderr": result.stderr})
    return result.stdout.strip()


def git_state(path):
    return {"head": git(path, "rev-parse", "HEAD"), "status": git(path, "status", "--porcelain=v1")}


def tensor_bytes(tensor):
    # CPU contiguous logical order. NumPy is already part of the frozen Torch
    # environment; this is a zero-copy byte view, never a numerical operation.
    return tensor.detach().contiguous().view(dtype=__import__("torch").uint8).numpy().tobytes(order="C")


def tensor_hash(tensor):
    return hashlib.sha256(tensor_bytes(tensor)).hexdigest()


def package_inventory():
    """Read distribution metadata only; retain duplicates and their actual roots."""
    entries = [{"name": dist.metadata["Name"], "version": dist.version,
                "location": str(Path(dist.locate_file("")).resolve())}
               for dist in importlib.metadata.distributions()]
    if any(not item["name"] or not item["version"] for item in entries):
        raise Stop("BLOCKED", "Incomplete installed distribution metadata")
    entries.sort(key=lambda item: (item["name"].casefold(), item["version"], item["location"]))
    return {"entries": entries, "aggregate_sha256": json_hash(entries)}


def runtime_snapshot(torch):
    return {"python_version": platform.python_version(), "torch_version": str(torch.__version__),
            "executable": sys.executable, "prefix": sys.prefix,
            "default_device": str(torch.get_default_device()), "default_dtype": str(torch.get_default_dtype()),
            "intraop_threads": torch.get_num_threads(), "interop_threads": torch.get_num_interop_threads(),
            "deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
            "deterministic_warn_only": torch.is_deterministic_algorithms_warn_only_enabled(),
            "autocast_cpu_enabled": torch.is_autocast_enabled("cpu"),
            "autocast_cuda_enabled": torch.is_autocast_enabled("cuda"),
            "cuda_available": torch.cuda.is_available()}


def runtime_matches(actual):
    expected = {"python_version": "3.12.3", "torch_version": "2.11.0+cpu", "default_device": "cpu",
                "default_dtype": "torch.float32", "intraop_threads": 2, "interop_threads": 1,
                "deterministic_algorithms": True, "deterministic_warn_only": False,
                "autocast_cpu_enabled": False, "autocast_cuda_enabled": False, "cuda_available": False}
    return all(actual.get(key) == value for key, value in expected.items())


def parameter_inventory(model):
    parameters = list(model.named_parameters(remove_duplicate=True))
    return {"parameter_count": sum(tensor.numel() for _, tensor in parameters),
            "unique_parameter_tensors": len(parameters), "parameter_names": sorted(name for name, _ in parameters)}


def normalize_checkpoint(raw):
    normalized = {}
    for key, value in raw.items():
        if not isinstance(key, str) or not key:
            raise Stop("FAIL", "Invalid checkpoint key")
        for prefix in ("module.", "_orig_mod.", "model."):
            if key.startswith(prefix):
                key = key[len(prefix):]
        if not key or key in normalized:
            raise Stop("FAIL", "Checkpoint normalized key collision", key)
        normalized[key] = value
    return normalized


def score_token_metrics(torch, logits, labels, score_start=64):
    """Labels are already next-token shifted; never shift a second time here."""
    if (logits.ndim != 3 or logits.shape[0] != 1 or labels.ndim != 1
            or logits.shape[1] != labels.numel() or not 0 <= score_start < labels.numel()):
        raise ValueError("Aligned batch-one logits/labels and a valid score window are required")
    scored = logits[0, score_start:].double()
    target = labels[score_start:]
    lse = torch.logsumexp(scored, dim=-1)
    target_logits = scored.gather(1, target[:, None]).squeeze(1)
    nll = lse - target_logits
    independent = torch.nn.functional.cross_entropy(scored, target, reduction="none")
    return {"logsumexp": lse, "target_logits": target_logits, "nll": nll, "independent": independent}


def state_snapshot(torch, model, reference=None):
    state = model.state_dict()
    if len(state) != 63 or (reference is not None and set(state) != set(reference)):
        raise Stop("FAIL", "state key coverage", {"model_keys": sorted(state), "reference_keys": sorted(reference or {})})
    entries = {}
    for name in sorted(state):
        tensor = state[name]
        if tensor.device.type != "cpu" or tensor.dtype != torch.float32 or tensor.layout != torch.strided:
            raise Stop("FAIL", "state tensor CPU FP32 dense", name)
        source = reference[name] if reference is not None else None
        if source is not None and (not isinstance(source, torch.Tensor) or source.device.type != "cpu"
                                   or source.dtype != tensor.dtype or source.shape != tensor.shape or source.layout != tensor.layout):
            raise Stop("FAIL", "state metadata restore", name)
        digest, count = hashlib.sha256(), 0
        flat = tensor.detach().contiguous().view(-1)
        source_flat = source.detach().contiguous().view(-1) if source is not None else None
        for start in range(0, flat.numel(), 262144):
            block = flat[start:start + 262144]
            raw = tensor_bytes(block)
            if len(raw) != block.numel() * block.element_size():
                raise Stop("FAIL", "state block byte coverage", name)
            if source_flat is not None and raw != tensor_bytes(source_flat[start:start + 262144]):
                raise Stop("FAIL", "state byte restore", {"name": name, "element_offset": start})
            digest.update(raw)
            count += len(raw)
        if count != tensor.numel() * tensor.element_size():
            raise Stop("FAIL", "state total byte coverage", name)
        entries[name] = {"shape": list(tensor.shape), "dtype": str(tensor.dtype),
                         "bytes": count, "sha256": digest.hexdigest()}
    return {"entries": entries, "aggregate_sha256": json_hash(entries), "state_count": len(entries)}


class Run:
    def __init__(self, spec, root):
        self.spec, self.root = spec, root
        self.control_forwards = self.total_forwards = self.formal_rows = 0
        self.control_checks, self.preservation_checks, self.control_records = [], [], []
        self.phase = "preflight"
        self.context = {}
        self.checks = (root / "checks.jsonl").open("x", encoding="utf-8", buffering=1)
        self.rows = (root / "rows.jsonl").open("x", encoding="utf-8", buffering=1)
        self.before = self.after = None

    def check(self, name, okay, actual=None, expected=True, status="FAIL"):
        row = {"name": name, "status": "PASS" if okay else status,
               "Purpose": name, "Environment": "CPU FP32; threads2 interop1; no autocast; no forced SDPA backend",
               "Input": {"phase": self.phase, **self.context}, "Expected": expected, "Actual": actual,
               "Status": "PASS" if okay else status}
        self.checks.write(json.dumps(row, allow_nan=False) + "\n")
        if self.phase == "controls":
            self.control_checks.append(row)
        if self.phase == "preservation":
            self.preservation_checks.append(row)
        if not okay:
            raise Stop(status, name, actual)

    def forward(self, torch, model, x, depth, rng, observed, wrapper=False, control_name=None):
        torch.set_rng_state(rng.clone())
        before_rng = tensor_bytes(torch.get_rng_state())
        before_sha = hashlib.sha256(before_rng).hexdigest()
        observation = {"h0_sha256": None, "h0_calls": 0, "block_calls": {"prelude": 0, "core": 0, "coda": 0}}
        previous_profile = sys.getprofile()
        handles, cleanup_errors = [], []
        first_error = None
        output = None
        init_code = model.initialize_state.__func__.__code__

        def profile(frame, event, value):
            if frame.f_code is init_code and event == "return":
                observation["h0_calls"] += 1
                pre = tensor_bytes(torch.get_rng_state())
                observation["h0_sha256"] = tensor_hash(value)
                if tensor_bytes(torch.get_rng_state()) != pre:
                    raise Stop("FAIL", "h0 observer changed CPU RNG")

        def hook_for(category):
            def hook(module, inputs, output):
                observation["block_calls"][category] += 1
                return None
            return hook

        start = None
        try:
            if observed:
                if previous_profile is not None:
                    raise Stop("BLOCKED", "A pre-existing profiler prevents isolated observation")
                for category, modules in (("prelude", model.transformer.prelude),
                                          ("core", model.transformer.core_block), ("coda", model.transformer.coda)):
                    for module in modules:
                        handles.append(module.register_forward_hook(hook_for(category)))
                sys.setprofile(profile)
            self.total_forwards += 1
            if control_name is not None:
                self.control_forwards += 1
            start = time.perf_counter()
            if wrapper:
                output = model.forward_for_generation(x, attention_mask=None, num_steps=depth, past_key_values=None)
            else:
                output = model(x, attention_mask=None, position_ids=None, labels=None,
                               return_logits=True, num_steps_pair=torch.tensor([depth, 0], device="cpu", dtype=torch.long))
            seconds = time.perf_counter() - start
        except BaseException as exc:
            first_error = exc
        finally:
            if observed:
                try:
                    sys.setprofile(previous_profile)
                except BaseException as exc:
                    cleanup_errors.append(repr(exc))
                for handle in handles:
                    try:
                        handle.remove()
                    except BaseException as exc:
                        cleanup_errors.append(repr(exc))
        if first_error is not None:
            if cleanup_errors:
                setattr(first_error, "observer_cleanup_errors", cleanup_errors)
            raise first_error
        if cleanup_errors:
            raise Stop("BLOCKED", "Observer cleanup failed", cleanup_errors)
        after_rng = tensor_bytes(torch.get_rng_state())
        logits = output["logits"]
        self.check("forward shape dtype and finite", tuple(logits.shape) == (1, 256, 32768)
                   and logits.dtype == torch.float32 and logits.device.type == "cpu"
                   and not logits.requires_grad and not torch.is_grad_enabled()
                   and bool(torch.isfinite(logits).all().item()),
                   {"shape": list(logits.shape), "dtype": str(logits.dtype), "depth": depth})
        self.check("forward validation consumes no RNG", tensor_bytes(torch.get_rng_state()) == after_rng)
        if wrapper:
            self.check("wrapper creates no cache", output.get("past_key_values") is None)
        if observed:
            expected = {"prelude": len(model.transformer.prelude), "core": len(model.transformer.core_block) * depth,
                        "coda": len(model.transformer.coda)}
            self.check("actual h0 and block coverage", observation["h0_calls"] == 1
                       and observation["block_calls"] == expected,
                       observation, {"h0_calls": 1, "block_calls": expected})
        record = {"name": control_name, "depth": depth, "h0_sha256": observation["h0_sha256"],
                  "rng_before_sha256": before_sha, "rng_after_sha256": hashlib.sha256(after_rng).hexdigest(),
                  "block_calls": observation["block_calls"] if observed else None,
                  "forward_seconds": seconds, "maxrss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
        if control_name is not None:
            record["logits_sha256"] = tensor_hash(logits)
            self.control_records.append(record)
            save(self.root / ("control_%02d.json" % self.control_forwards), record)
        return logits, record, after_rng


def execute(run):
    spec, root = run.spec, run.root
    repo, upstream = Path(spec["repo"]).resolve(), Path(spec["upstream"]).resolve()
    model_dir = Path(spec["model_dir"]).resolve()
    tokenizer = Path(spec["tokenizer_path"]).resolve()
    tokenizer = tokenizer / "tokenizer.json" if tokenizer.is_dir() else tokenizer
    inputs = Path(spec["inputs_path"]).resolve()
    manifest_path = Path(spec["source_manifest_path"]).resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    upstream_before, repo_before = git_state(upstream), git_state(repo)
    run.check("upstream frozen clean", upstream_before == {"head": UPSTREAM, "status": ""}, upstream_before)
    run.check("execution checkout frozen clean", repo_before["status"] == ""
              and repo_before["head"] == spec.get("expected_head", spec["freeze_commit"]), repo_before)
    protected = {model_dir / "pytorch_model.bin": {"sha256": WEIGHTS},
                 model_dir / "config.json": {"sha256": CONFIG}, tokenizer: {"sha256": TOKENIZER},
                 inputs: {"sha256": spec["inputs_sha256"]}}
    for name, expected in manifest.items():
        path = Path(name)
        path = path.resolve() if path.is_absolute() else (repo / path).resolve()
        if path in protected and protected[path]["sha256"] != expected["sha256"]:
            raise Stop("FAIL", "Source manifest conflicts with immutable artifact hash", str(path))
        protected[path] = expected
    protected_before = {}
    for path, expected in protected.items():
        actual = file_info(path)
        run.check("protected input hash", actual["sha256"] == expected["sha256"]
                  and ("bytes" not in expected or actual["bytes"] == expected["bytes"]),
                  {"path": str(path), "actual": actual, "expected": expected})
        protected_before[str(path)] = actual
    protected_before[str(manifest_path)] = file_info(manifest_path)
    save(root / "protected_before.json", {"files": protected_before, "upstream": upstream_before, "repo": repo_before})
    run.check("corrected source input identity", spec["inputs_sha256"] == INPUTS_SHA,
              spec["inputs_sha256"], INPUTS_SHA)
    samples = json.loads(inputs.read_text(encoding="utf-8"))["samples"]
    run.check("exact frozen sample inventory", isinstance(samples, list) and len(samples) == 32, len(samples))
    article_ids, source_keys, heading_rows = set(), set(), set()
    for index, sample in enumerate(samples):
        ids = sample.get("tokens")
        valid = (sample.get("index") == index and type(sample.get("index")) is int
                 and isinstance(sample.get("article_id"), str) and len(sample["article_id"]) == 64
                 and sample["article_id"] not in article_ids and isinstance(sample.get("title"), str)
                 and isinstance(sample.get("text_sha256"), str) and len(sample["text_sha256"]) == 64
                 and isinstance(sample.get("source_article_key"), str) and len(sample["source_article_key"]) == 64
                 and sample["source_article_key"] not in source_keys
                 and type(sample.get("heading_row")) is int and sample["heading_row"] not in heading_rows
                 and isinstance(ids, list) and len(ids) == 257
                 and all(type(value) is int and 0 <= value < 32768 for value in ids))
        run.check("valid fixed article tokens", valid, {"index": index})
        article_ids.add(sample["article_id"])
        source_keys.add(sample["source_article_key"])
        heading_rows.add(sample["heading_row"])
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    os.environ["OMP_NUM_THREADS"] = "2"
    os.environ["MKL_NUM_THREADS"] = "2"
    sys.path.insert(0, str(upstream))
    packages_before = package_inventory()
    save(root / "packages_before.json", packages_before)
    import torch
    torch.set_default_device("cpu")
    torch.set_default_dtype(torch.float32)
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True, warn_only=False)
    runtime_after_import = runtime_snapshot(torch)
    run.check("CPU runtime after import", runtime_matches(runtime_after_import), runtime_after_import)
    from receval.models.parcae import ModelingParcae
    raw = torch.load(model_dir / "pytorch_model.bin", map_location="cpu", weights_only=True)
    normalized = normalize_checkpoint(raw)
    model = ModelingParcae.from_pretrained(model_dir, device="cpu", dtype=None)
    runtime_after_load = runtime_snapshot(torch)
    run.check("CPU runtime after load", runtime_matches(runtime_after_load), runtime_after_load)
    parameters_before = parameter_inventory(model)
    run.check("actual parameter inventory", parameters_before["parameter_count"] == PARAMETER_COUNT
              and parameters_before["unique_parameter_tensors"] == PARAMETER_TENSORS,
              parameters_before, {"parameter_count": PARAMETER_COUNT, "unique_parameter_tensors": PARAMETER_TENSORS})
    run.check("official model eval configuration", type(model) is ModelingParcae and not model.training
              and all(not part.training for part in model.modules()) and model.config.mean_recurrence == 8
              and model.config.state_init == "like-init"
              and len(model.transformer.prelude) == len(model.transformer.core_block) == len(model.transformer.coda) == 2,
              {"mean_recurrence": model.config.mean_recurrence, "state_init": model.config.state_init})
    with torch.no_grad():
        run.before = state_snapshot(torch, model, normalized)
        run.before.update(parameters_before)
    run.check("state exact restore", True, {"state_count": run.before["state_count"], "aggregate_sha256": run.before["aggregate_sha256"]})
    save(root / "state_before.json", run.before)
    del raw, normalized
    environment = {"python": sys.version, "torch": torch.__version__, "device": runtime_after_load["default_device"],
                   "dtype": runtime_after_load["default_dtype"], "threads": runtime_after_load["intraop_threads"],
                   "interop": runtime_after_load["interop_threads"], "deterministic": runtime_after_load["deterministic_algorithms"],
                   "autocast": runtime_after_load["autocast_cpu_enabled"],
                   "forced_attention_backend": False, "inputs_sha256": spec["inputs_sha256"],
                   "freeze_commit": spec["freeze_commit"], "execution_head": repo_before["head"],
                   "upstream_commit": UPSTREAM, "source_manifest_sha256": protected_before[str(manifest_path)]["sha256"],
                   "state_before_sha256": run.before["aggregate_sha256"], "weights_sha256": WEIGHTS,
                   "timing_includes_readonly_observer": True,
                   "autocast_cpu_enabled": runtime_after_load["autocast_cpu_enabled"],
                   "runtime_after_import": runtime_after_import, "runtime_after_load": runtime_after_load,
                   "packages_before_sha256": packages_before["aggregate_sha256"],
                   "actual_parameter_count": parameters_before["parameter_count"],
                   "unique_parameter_tensors": parameters_before["unique_parameter_tensors"]}
    run.check("autocast remains disabled", not environment["autocast_cpu_enabled"])
    save(root / "environment.json", environment)
    with torch.no_grad():
        run.phase = "controls"
        x = torch.tensor([samples[0]["tokens"][:256]], device="cpu", dtype=torch.long)
        torch.manual_seed(SEEDS[0])
        control_rng = torch.get_rng_state().clone()
        native, native_info, native_after = run.forward(torch, model, x, 8, control_rng, False, control_name="native8")
        wrapped, wrapped_info, wrapped_after = run.forward(torch, model, x, 8, control_rng, False, True, "wrapper8")
        run.check("control native-wrapper exact", tensor_bytes(native) == tensor_bytes(wrapped) and native_after == wrapped_after)
        del wrapped
        observed, observed_info, observed_after = run.forward(torch, model, x, 8, control_rng, True, control_name="observed8")
        run.check("control observer no-op exact", tensor_bytes(native) == tensor_bytes(observed) and native_after == observed_after)
        del native
        repeat, repeat_info, repeat_after = run.forward(torch, model, x, 8, control_rng, True, control_name="observed8_repeat")
        run.check("control observed repeat exact", tensor_bytes(observed) == tensor_bytes(repeat)
                  and observed_after == repeat_after and observed_info["h0_sha256"] == repeat_info["h0_sha256"])
        del repeat
        mutated = x.clone()
        mutated[:, 128:] = (mutated[:, 128:] + 1) % 32768
        for depth in DEPTHS:
            if depth == 8:
                baseline, base_info, base_after = observed, observed_info, observed_after
            else:
                baseline, base_info, base_after = run.forward(torch, model, x, depth, control_rng, True,
                                                             control_name="causal%d_base" % depth)
            changed, changed_info, changed_after = run.forward(torch, model, mutated, depth, control_rng, True,
                                                              control_name="causal%d_mut" % depth)
            baseline_prefix = tensor_bytes(baseline[:, :128])
            mutated_prefix = tensor_bytes(changed[:, :128])
            causal_actual = {"prefix_tokens": 128,
                             "baseline_prefix_sha256": hashlib.sha256(baseline_prefix).hexdigest(),
                             "mutated_prefix_sha256": hashlib.sha256(mutated_prefix).hexdigest(),
                             "bytewise_equal": baseline_prefix == mutated_prefix,
                             "h0_equal": base_info["h0_sha256"] == changed_info["h0_sha256"],
                             "rng_after_equal": base_after == changed_after}
            run.check("control causality depth " + str(depth),
                      causal_actual["bytewise_equal"] and causal_actual["h0_equal"] and causal_actual["rng_after_equal"],
                      causal_actual)
            del baseline, changed, baseline_prefix, mutated_prefix
        del observed
        run.check("exact control forward count", run.control_forwards == 9, run.control_forwards, 9)
        run.phase = "formal"
        for sample in samples:
            index, ids = sample["index"], sample["tokens"]
            x = torch.tensor([ids[:256]], device="cpu", dtype=torch.long)
            labels = torch.tensor(ids[1:257], device="cpu", dtype=torch.long)
            for replica, base_seed in enumerate(SEEDS):
                seed = base_seed + 100000 * index
                torch.manual_seed(seed)
                rng = torch.get_rng_state().clone()
                reference = None
                order = ORDERS[(index * 3 + replica) % len(ORDERS)]
                for order_position, depth in enumerate(order):
                    run.context = {"article_index": index, "replica": replica, "depth": depth}
                    logits, info, after = run.forward(torch, model, x, depth, rng, True)
                    identity = (info["h0_sha256"], info["rng_before_sha256"], info["rng_after_sha256"])
                    if reference is None:
                        reference = identity
                    run.check("paired actual h0 and CPU RNG", identity == reference,
                              {"article_index": index, "replica": replica, "depth": depth, "identity": identity})
                    metrics = score_token_metrics(torch, logits, labels)
                    lse, target_logits, nll, independent = (metrics[name] for name in
                                                           ("logsumexp", "target_logits", "nll", "independent"))
                    run.check("independent double NLL equality", bool(torch.isfinite(nll).all().item())
                              and bool(torch.isfinite(independent).all().item())
                              and bool(torch.allclose(nll, independent, atol=1e-10, rtol=0)),
                              {"max_abs_error": float((nll-independent).abs().max().item()), "scored_tokens": nll.numel()},
                              {"atol": 1e-10, "rtol": 0, "scored_tokens": 192})
                    run.check("scoring consumes no CPU RNG", tensor_bytes(torch.get_rng_state()) == after)
                    row = {"article_index": index, "article_id": sample["article_id"],
                           "source_article_key": sample["source_article_key"], "heading_row": sample["heading_row"], "replica": replica,
                           "replica_seed": base_seed, "seed": seed, "depth": depth, "order": list(order),
                           "order_position": order_position, "input_ids_sha256": json_hash(ids[:256]),
                           "target_ids_sha256": json_hash(ids[1:257]), "scored_target_ids_sha256": json_hash(ids[65:257]),
                           **{k: info[k] for k in
                               ("h0_sha256", "rng_before_sha256", "rng_after_sha256", "block_calls", "forward_seconds", "maxrss_kib")},
                           "logsumexp": lse.tolist(), "target_logits": target_logits.tolist(), "nll": nll.tolist(),
                           "mean_nll": float(nll.mean().item())}
                    run.rows.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
                    run.rows.flush()
                    run.formal_rows += 1
                    del logits, metrics, lse, target_logits, nll, independent
            print("article %02d/32 complete; rows=%d" % (index + 1, run.formal_rows), flush=True)
        run.phase = "preservation"
        run.context = {}
        run.check("complete formal coverage", run.formal_rows == 288 and run.total_forwards == 297,
                  {"formal_rows": run.formal_rows, "control_forwards": run.control_forwards, "total_forwards": run.total_forwards},
                  {"formal_rows": 288, "control_forwards": 9, "total_forwards": 297})
        run.after = state_snapshot(torch, model)
        run.after.update(parameter_inventory(model))
        save(root / "state_after.json", run.after)
        run.check("state invariant", run.after == run.before,
                  {"before": run.before["aggregate_sha256"], "after": run.after["aggregate_sha256"]})
    runtime_after = runtime_snapshot(torch)
    run.check("CPU runtime after evaluation", runtime_matches(runtime_after), runtime_after)
    packages_after = package_inventory()
    save(root / "packages_after.json", packages_after)
    run.check("package inventory invariant", packages_after == packages_before,
              {"before": packages_before["aggregate_sha256"], "after": packages_after["aggregate_sha256"]})
    protected_after = {path: file_info(path) for path in protected_before}
    upstream_after, repo_after = git_state(upstream), git_state(repo)
    save(root / "protected_after.json", {"files": protected_after, "upstream": upstream_after, "repo": repo_after})
    run.check("protected files invariant", protected_after == protected_before)
    run.check("upstream invariant", upstream_after == upstream_before, upstream_after)
    run.check("repo invariant", repo_after == repo_before, repo_after)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", required=True, type=Path)
    args = parser.parse_args()
    if not args.spec.is_absolute():
        parser.error("--spec must be absolute")
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    root = Path(spec["run_dir"])
    if not root.is_absolute():
        parser.error("run_dir must be absolute")
    root = root.resolve()
    for key in ("repo", "upstream", "model_dir", "tokenizer_path", "inputs_path", "source_manifest_path"):
        path = Path(spec[key]).resolve()
        if root == path or (path.is_dir() and root.is_relative_to(path)):
            parser.error("run_dir must be outside protected source/input directories")
    root.mkdir(parents=True, exist_ok=False)
    save(root / "spec.json", spec)
    run = Run(spec, root)
    def interrupted(signum, frame):
        raise Stop("BLOCKED", "Execution interrupted", signum)
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    start, status, error = time.monotonic(), "NOT TESTED", None
    try:
        execute(run)
        status = "PASS"
    except BaseException as exc:
        status = getattr(exc, "status", "BLOCKED" if isinstance(exc, (OSError, MemoryError, KeyboardInterrupt, SystemExit)) else "FAIL")
        error = {"phase": run.phase, "reason": getattr(exc, "reason", str(exc)), "actual": getattr(exc, "actual", None),
                 "type": type(exc).__name__, "traceback": traceback.format_exc(),
                 "observer_cleanup_errors": getattr(exc, "observer_cleanup_errors", [])}
    cleanup = []
    for stream in (run.rows, run.checks):
        try:
            stream.close()
        except BaseException as exc:
            cleanup.append(repr(exc))
    if cleanup and status == "PASS":
        status = "BLOCKED"
    completion = {"status": status, "formal_rows": run.formal_rows, "control_forwards": run.control_forwards,
                  "total_forwards": run.total_forwards, "control_records": run.control_records,
                  "control_checks": run.control_checks, "preservation_checks": run.preservation_checks,
                  "state_before_sha256": run.before["aggregate_sha256"] if run.before else None,
                  "state_after_sha256": run.after["aggregate_sha256"] if run.after else None,
                  "error": error, "cleanup_errors": cleanup, "elapsed_seconds": time.monotonic()-start,
                  "scientific_positive_evidence": "NOT ASSESSED", "complete_coverage": run.formal_rows == 288 and run.total_forwards == 297,
                  "utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    try:
        save(root / "completion.json", completion)
    except BaseException as exc:
        print(json.dumps({"completion": completion, "sealing_error": repr(exc)}, allow_nan=False), file=sys.stderr, flush=True)
        return 2
    print(json.dumps({"status": status, "formal_rows": run.formal_rows, "total_forwards": run.total_forwards}), flush=True)
    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
