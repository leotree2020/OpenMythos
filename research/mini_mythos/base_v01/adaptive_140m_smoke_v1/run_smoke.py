"""One target-only, CPU correctness smoke. No training, quality score or retry.

All imports at module scope are standard library. Numerical execution requires
explicit --spec and --out, a pinned clean Codespace checkout and frozen inputs.
Raw model outputs stay in private/; public records contain metadata and hashes.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import re
import signal
import subprocess
import sys
import time
import traceback

SPACE = "bookish-pancake-vwqx7rr9x5w3wxjr"
PYTHON = "/workspaces/mythos-base-v01-cpu312/bin/python"
UPSTREAM = "69284c13746e849104f738d6d1a347b1f457df76"
WEIGHTS = "ed6eb306464dd0d694e9eacd58f7e06ac3e44b43cb7c5c79dbcb1543059c6621"
CONFIG = "5c8fc785c2f6dba67d0370ad715034860e3b22bfce850da825c06baa03923c13"
INPUTS = "3abb324ea2876abb78e18d86ec257a9e1d388f9501bd8cdd6c99011ac11cf41e"
LIBRARY = "daa6b5b014f9d5f77cc47e2ba14a7027065c135b2cac7f6bcda58d0e6d6457b8"
HELPERS = "02fcaae5a7a09ede68a662592668099ad60f08af51aad683c5c7d37926163a68"
DEPTHS, LENGTHS, SEEDS = (8, 16, 32), (1, 16, 64), (3101, 3202)
ENV = {"OMP_NUM_THREADS": "2", "MKL_NUM_THREADS": "2", "OPENBLAS_NUM_THREADS": "1",
       "RAYON_NUM_THREADS": "1", "TOKENIZERS_PARALLELISM": "false", "CUDA_VISIBLE_DEVICES": "",
       "PYTHONDONTWRITEBYTECODE": "1", "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"}


class Stop(Exception):
    def __init__(self, status, reason, actual=None):
        super().__init__(reason)
        self.status, self.reason, self.actual = status, reason, actual


def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def json_hash(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def info(path):
    h, size = hashlib.sha256(), 0
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
            size += len(block)
    return {"bytes": size, "sha256": h.hexdigest()}


def save(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")


def git(path, *args):
    result = subprocess.run(["git", "-C", str(path), *args], capture_output=True, text=True,
                            timeout=60, env=dict(os.environ, GIT_OPTIONAL_LOCKS="0"))
    if result.returncode:
        raise Stop("BLOCKED", "Git read failed", {"args": args, "stderr": result.stderr})
    return result.stdout.strip()


def git_state(path):
    return {"head": git(path, "rev-parse", "HEAD"), "branch": git(path, "branch", "--show-current"),
            "status": git(path, "status", "--porcelain=v1", "--untracked-files=all")}


def load_module(name, path, expected_sha):
    if info(path)["sha256"] != expected_sha:
        raise Stop("FAIL", "Imported helper bytes differ from pin", str(path))
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise Stop("BLOCKED", "Cannot import pinned helper", str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def expected_counts(depth, readouts):
    return {"embedding": 1, "prelude": 2, "prelude_norm": 1, "adapter": depth,
            "core": 2 * depth, "projection": readouts, "coda": 2 * readouts,
            "final_norm": readouts, "head": readouts, "value_embedding": 1 + depth + readouts}


def group_plan():
    return [(length, seed) for length in LENGTHS for seed in SEEDS]


def call_plan():
    return [("native", depth) for depth in DEPTHS] + [("fixed", depth) for depth in DEPTHS] + [
        ("diagnostic", None), ("adaptive", None), ("adaptive_repeat", None)]


def model_config(model):
    return {"serialized": model.config.__getstate__(), "emb_scale": model.emb_scale,
            "init_logit_scale": model.config.init.logit_scale,
            "init_embedding_std": model.config.init.get_std("embedding"),
            "recurrent_iteration_method": model.recurrent_iteration_method,
            "gradient_checkpointing": model.gradient_checkpointing,
            "monitoring": model.monitoring, "extreme_monitoring": model.extreme_monitoring}


class Run:
    def __init__(self, spec, out):
        self.spec, self.out = spec, out
        self.public, self.private = out / "public", out / "private"
        self.public.mkdir()
        self.private.mkdir()
        self.checks = (self.public / "checks.jsonl").open("x", encoding="utf-8", buffering=1)
        self.rows = (self.public / "calls.jsonl").open("x", encoding="utf-8", buffering=1)
        self.phase, self.context = "S0", {}
        self.environment = {"planned": "CPU FP32; threads2; interop1; no autocast/cache"}
        self.check_counts = {"PASS": 0, "FAIL": 0, "BLOCKED": 0}
        self.calls_started = self.calls_completed = self.groups_completed = 0
        self.loader_attempts = self.loader_returns = 0
        self.protected_before = self.git_before = self.packages_before = None
        self.state_before = self.config_before = self.model = self.helper = self.torch = None
        self.runtime_before = None
        self.model_attribute_before = None
        self.preservation = "NOT TESTED"
        self.save_errors = []

    def check(self, purpose, okay, actual=None, expected=True, failure="FAIL"):
        status = "PASS" if okay else failure
        row = {"Purpose": purpose, "Environment": self.environment,
               "Input": {"phase": self.phase, **self.context}, "Expected": expected,
               "Actual": actual, "Status": status, "utc": utc()}
        self.checks.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
        self.check_counts[status] += 1
        if not okay:
            raise Stop(failure, purpose, actual)

    def raw(self, name, value):
        data = self.helper.tensor_bytes(value)
        path = self.private / name
        with path.open("xb") as stream:
            stream.write(data)
        return {"path": str(path.relative_to(self.out)).replace("\\", "/"),
                "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
                "shape": list(value.shape), "dtype": str(value.dtype), "byteorder": sys.byteorder}

    def finite(self, value, name, expected_shape=None):
        t = self.torch
        okay = (isinstance(value, t.Tensor) and value.device.type == "cpu" and value.dtype == t.float32
                and not value.requires_grad and bool(t.isfinite(value).all()))
        if expected_shape is not None:
            okay = okay and tuple(value.shape) == tuple(expected_shape)
        self.check(name, okay, {"shape": list(value.shape), "dtype": str(value.dtype),
                              "requires_grad": value.requires_grad}, list(expected_shape) if expected_shape else "finite CPU FP32")

    def call(self, model, library, ids, rng, mode, depth=None, capture_prefix=False):
        t, h = self.torch, self.helper
        self.calls_started += 1
        number = self.calls_started
        label = f"call_{number:03d}"
        self.context = {**self.context, "call": number, "mode": mode, "requested_depth": depth}
        print(f"{utc()} {label} start {self.context}", flush=True)
        t.set_rng_state(rng.clone())
        before_rng = h.tensor_bytes(t.get_rng_state())
        before_input = h.tensor_bytes(ids)
        old_exists = hasattr(model, "_current_input_ids")
        old_ids = getattr(model, "_current_input_ids", None)
        previous_profile = sys.getprofile()
        counts = {key: 0 for key in expected_counts(0, 0)}
        observed = {"h0": [], "readout_states": [], "head_outputs": [], "head_prefixes": [], "head_suffixes": []}
        record = {"call": number, "mode": mode, "requested_depth": depth, "context": dict(self.context),
                  "started_utc": utc(), "status": "NOT TESTED", "observed": observed,
                  "actual_counts": counts, "outputs": {}, "error": None, "cleanup_errors": [],
                  "input_sha256": hashlib.sha256(before_input).hexdigest(),
                  "input_ids_json_sha256": json_hash(ids.tolist()), "input_shape": list(ids.shape),
                  "rng_before_sha256": hashlib.sha256(before_rng).hexdigest()}
        handles, outputs, prefixes, suffixes = [], {}, {}, {}
        first_error, result, returned_attribute_okay = None, None, None
        init_code = model.initialize_state.__func__.__code__
        def profile(frame, event, value):
            if frame.f_code is init_code and event == "return" and frame.f_locals.get("self") is model:
                prior = h.tensor_bytes(t.get_rng_state())
                self.check("no repeated h0 initialization", len(observed["h0"]) == 0, len(observed["h0"]), 0)
                if isinstance(value, t.Tensor):
                    self.finite(value, "actual h0 finite", (1, ids.shape[1], 768))
                    observed["h0"].append({**self.raw(label + "_h0.bin", value),
                                           "rng_after_init_sha256": hashlib.sha256(prior).hexdigest()})
                else:
                    observed["h0"].append({"invalid_return": type(value).__name__})
                self.check("h0 observation consumes no RNG", h.tensor_bytes(t.get_rng_state()) == prior)
        def hook(category):
            def observe(module, args, value):
                counts[category] += 1
                if category == "head":
                    self.finite(value, "full prefix head output finite", (1, ids.shape[1], 32768))
                    observed["head_outputs"].append({"shape": list(value.shape), "dtype": str(value.dtype),
                        "sha256": h.tensor_hash(value), "last_raw_sha256": h.tensor_hash(value[:, -1, :])})
                    if capture_prefix:
                        observed["head_prefixes"].append(self.raw(f"{label}_head{counts['head']}_prefix.bin", value[:, :32, :]))
                        observed["head_suffixes"].append({"sha256": h.tensor_hash(value[:, 32:, :]), "shape": list(value[:, 32:, :].shape)})
                        prefixes[counts["head"]] = h.tensor_bytes(value[:, :32, :])
                        suffixes[counts["head"]] = h.tensor_bytes(value[:, 32:, :])
            return observe
        def projection_pre(module, args):
            value = args[0]
            self.finite(value, "readout recurrence state finite", (1, ids.shape[1], 768))
            observed["readout_states"].append({"sha256": h.tensor_hash(value), "shape": list(value.shape)})
        start = time.perf_counter()
        try:
            self.check("no pre-existing Python profiler", previous_profile is None, failure="BLOCKED")
            modules = {"embedding": [model.transformer.wte], "prelude": model.transformer.prelude,
                       "prelude_norm": [model.transformer.ln_prelude], "adapter": [model.transformer.adapter],
                       "core": model.transformer.core_block, "projection": [model.transformer.C],
                       "coda": model.transformer.coda, "final_norm": [model.transformer.ln_f], "head": [model.lm_head],
                       "value_embedding": list(model.value_embeds.values())}
            for category, group in modules.items():
                handles.extend(module.register_forward_hook(hook(category)) for module in group)
            handles.append(model.transformer.C.register_forward_pre_hook(projection_pre))
            sys.setprofile(profile)
            if mode == "native":
                result = model(ids, attention_mask=None, position_ids=None, labels=None, return_logits=True,
                               num_steps_pair=t.tensor([depth, 0], dtype=t.long))
                self.finite(result["logits"], "full native final logits finite", (1, ids.shape[1], 32768))
                outputs = {depth: result["logits"][:, -1, :].clone()}
                selected = depth
            elif mode == "fixed":
                result = library.fixed_next_token(model, ids, depth=depth)
            elif mode in ("diagnostic", "causal_mutated"):
                result = library.diagnostic_checkpoints(model, ids)
            elif mode in ("adaptive", "adaptive_repeat"):
                result = library.adaptive_next_token(model, ids)
            else:
                raise Stop("FAIL", "Unknown frozen call mode", mode)
            if mode != "native":
                returned_attribute_okay = (hasattr(model, "_current_input_ids") == old_exists
                                          and (not old_exists or model._current_input_ids is old_ids))
                self.check("library restores native bookkeeping itself", returned_attribute_okay)
                outputs = result.checkpoint_logits
                selected = result.selected_depth
                record.update(library_counts=result.counts, policy_seconds=result.policy_seconds,
                              tv_8_16=result.tv_8_16, library_h0_sha256=result.h0_sha256,
                              library_state_sha256=result.recurrent_state_sha256,
                              library_rng_before_sha256=result.rng_before_sha256,
                              library_rng_after_sha256=result.rng_after_sha256)
            record["selected_depth"] = selected
        except BaseException as exc:
            if isinstance(exc, ValueError) or (isinstance(exc, RuntimeError) and str(exc) in (
                    "readout mutated recurrence state", "readout consumed CPU RNG", "policy consumed CPU RNG")):
                first_error = Stop("FAIL", "Frozen call invariant rejected", {"type": type(exc).__name__, "reason": str(exc)})
            else:
                first_error = exc
        finally:
            for cleanup in ([lambda: sys.setprofile(previous_profile)] + [handle.remove for handle in handles]):
                try:
                    cleanup()
                except BaseException as exc:
                    record["cleanup_errors"].append(repr(exc))
            try:
                if old_exists:
                    model._current_input_ids = old_ids
                elif hasattr(model, "_current_input_ids"):
                    delattr(model, "_current_input_ids")
            except BaseException as exc:
                record["cleanup_errors"].append(repr(exc))
            record["api_observed_seconds"] = time.perf_counter() - start
            record["ended_utc"] = utc()
        try:
            if first_error is not None:
                raise first_error
            self.check("observer and bookkeeping cleanup", not record["cleanup_errors"], record["cleanup_errors"], failure="BLOCKED")
            self.check("input bytes unchanged", h.tensor_bytes(ids) == before_input)
            self.check("temporary input ID attribute restored", hasattr(model, "_current_input_ids") == old_exists
                       and (not old_exists or model._current_input_ids is old_ids))
            after_rng = h.tensor_bytes(t.get_rng_state())
            record["rng_after_sha256"] = hashlib.sha256(after_rng).hexdigest()
            record["rng_before"] = self.raw(label + "_rng_before.bin", rng)
            record["rng_after"] = self.raw(label + "_rng_after.bin", t.get_rng_state())
            self.check("actual h0 exactly once", len(observed["h0"]) == 1 and "sha256" in observed["h0"][0], observed["h0"])
            self.check("observed exact module calls", counts == expected_counts(selected, len(outputs)), counts,
                       expected_counts(selected, len(outputs)))
            self.check("readout order and count", len(observed["head_outputs"]) == len(outputs)
                       and len(observed["readout_states"]) == len(outputs))
            if mode != "native":
                expected_keys = [depth] if mode == "fixed" else ([8, 16] if selected == 16 else [8, 16, 32])
                self.check("exact library readout keys", list(outputs) == expected_keys, list(outputs), expected_keys)
                self.check("library observations agree with independent observer",
                           result.h0_sha256 == observed["h0"][0]["sha256"]
                           and result.rng_before_sha256 == record["rng_before_sha256"]
                           and result.rng_after_sha256 == record["rng_after_sha256"]
                           and all(result.recurrent_state_sha256[d] == observed["readout_states"][i]["sha256"]
                                   for i, d in enumerate(outputs)))
                mapping = {"embedding": "embedding_calls", "prelude": "prelude_block_calls",
                           "prelude_norm": "prelude_norm_calls", "adapter": "adapter_calls", "core": "core_block_calls",
                           "projection": "projection_calls", "coda": "coda_block_calls", "final_norm": "final_norm_calls", "head": "head_calls",
                           "value_embedding": "value_embedding_calls"}
                self.check("library call counters agree with hooks", all(result.counts[b] == counts[a] for a, b in mapping.items()))
                adaptive = mode in ("adaptive", "adaptive_repeat")
                self.check("policy count and threshold are frozen", result.counts["policy_evaluations"] == int(adaptive)
                           and result.counts["policy_softmax_calls"] == 2 * int(adaptive)
                           and (not adaptive or selected == (16 if result.tv_8_16 <= 0.01 else 32)))
                self.check("selected last logits match selected checkpoint bytes", h.tensor_bytes(result.last_logits) == h.tensor_bytes(outputs[selected]))
            for d, value in outputs.items():
                self.finite(value, "final next-token logits finite", (1, 32768))
                record["outputs"][str(d)] = self.raw(f"{label}_depth{d}_last_logits.bin", value)
            self.check("postprocessing consumes no CPU RNG", h.tensor_bytes(t.get_rng_state()) == after_rng)
            record["status"] = "PASS"
            self.calls_completed += 1
        except BaseException as exc:
            if first_error is None:
                first_error = exc
            record["status"] = getattr(first_error, "status", "BLOCKED")
            record["error"] = {"type": type(first_error).__name__, "reason": str(first_error),
                               "traceback": traceback.format_exc()}
        finally:
            record["call_total_seconds"] = time.perf_counter() - start
            try:
                save(self.public / (label + ".json"), record)
                self.rows.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")
            except BaseException as exc:
                self.save_errors.append({"call": number, "error": repr(exc)})
                if first_error is None:
                    first_error = Stop("BLOCKED", "call evidence could not be saved", repr(exc))
        if first_error is not None:
            raise first_error
        print(f"{utc()} {label} PASS depth={selected} observed_seconds={record['api_observed_seconds']:.6f}", flush=True)
        return record, outputs, prefixes, suffixes


def execute(run):
    spec = run.spec
    repo, upstream, model_dir = (Path(spec[key]).resolve() for key in ("repo", "upstream", "model_dir"))
    inputs, manifest_path = (Path(spec[key]).resolve() for key in ("inputs_path", "source_manifest_path"))
    run.check("designated Codespace", os.environ.get("CODESPACE_NAME") == SPACE, os.environ.get("CODESPACE_NAME"), SPACE, "BLOCKED")
    run.check("target Linux interpreter", platform.system() == "Linux" and sys.executable == PYTHON
              and platform.python_version() == "3.12.3" and sys.flags.isolated and sys.dont_write_bytecode,
              {"python": sys.version, "executable": sys.executable, "isolated": sys.flags.isolated}, failure="BLOCKED")
    run.check("full frozen identities", all(re.fullmatch("[0-9a-f]{40}", spec.get(k, "")) for k in ("freeze_commit", "expected_head")))
    run.git_before = {"repo": git_state(repo), "upstream": git_state(upstream)}
    run.check("frozen clean execution checkout", run.git_before["repo"] == {"head": spec["expected_head"], "branch": spec["branch"], "status": ""}, run.git_before["repo"])
    run.check("pinned clean upstream", run.git_before["upstream"]["head"] == UPSTREAM and run.git_before["upstream"]["status"] == "", run.git_before["upstream"])
    git(repo, "merge-base", "--is-ancestor", spec["freeze_commit"], spec["expected_head"])
    run.check("source manifest SHA", info(manifest_path)["sha256"] == spec["source_manifest_sha256"], info(manifest_path), spec["source_manifest_sha256"])
    library_path = repo / "research/mini_mythos/base_v01/adaptive_depth_v1/adaptive_depth.py"
    helper_path = Path(spec.get("depth_helper_path", str(repo / "research/mini_mythos/base_v01/depth_16_32_v1/run_depth_budget.py"))).resolve()
    protected = {model_dir / "pytorch_model.bin": {"sha256": WEIGHTS}, model_dir / "config.json": {"sha256": CONFIG},
                 inputs: {"sha256": INPUTS}, library_path: {"sha256": LIBRARY}, helper_path: {"sha256": HELPERS}}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for name, expected in manifest.items():
        path = Path(name)
        path = path.resolve() if path.is_absolute() else (repo / path).resolve()
        if path in protected and protected[path]["sha256"] != expected["sha256"]:
            raise Stop("FAIL", "Source manifest conflicts with fixed pin", str(path))
        protected[path] = expected
    before = {}
    for path, expected in protected.items():
        actual = info(path)
        run.check("protected source/input exact hash", actual["sha256"] == expected["sha256"]
                  and ("bytes" not in expected or actual["bytes"] == expected["bytes"]), {"path": str(path), "actual": actual}, expected)
        before[str(path)] = actual
    before[str(manifest_path)] = info(manifest_path)
    save(run.public / "protected_before.json", {"files": before, "git": run.git_before})
    run.protected_before = before
    samples = json.loads(inputs.read_text(encoding="utf-8"))["samples"]
    sample = samples[0]
    tokens = sample.get("tokens")
    run.check("frozen first corrected sample", len(samples) == 32 and sample.get("index") == 0
              and isinstance(tokens, list) and len(tokens) == 257
              and all(type(v) is int and 0 <= v < 32768 for v in tokens),
              {"index": sample.get("index"), "source_article_key": sample.get("source_article_key"), "heading_row": sample.get("heading_row")})
    save(run.private / "prefix_tokens.json", {"source_article_key": sample["source_article_key"], "original64": tokens[:64],
                                             "causal_mutated64": tokens[:32] + [(v + 1) % 32768 for v in tokens[32:64]]})
    run.helper = load_module("mythos_smoke_frozen_helpers", helper_path, HELPERS)
    h = run.helper
    run.packages_before = h.package_inventory()
    save(run.public / "packages_before.json", run.packages_before)
    before_environment = {k: os.environ.get(k) for k in ENV}
    for key, value in ENV.items():
        os.environ[key] = value
    sys.path.insert(0, str(upstream))
    import torch
    run.torch = torch
    torch.set_default_device("cpu")
    torch.set_default_dtype(torch.float32)
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True, warn_only=False)
    run.runtime_before = h.runtime_snapshot(torch)
    run.check("actual CPU runtime", h.runtime_matches(run.runtime_before), run.runtime_before, failure="BLOCKED")
    library = load_module("mythos_frozen_adaptive_depth", library_path, LIBRARY)
    run.check("frozen policy constant and source pin", library.TV_THRESHOLD == 0.01 and library.DEPTHS == DEPTHS and library.UPSTREAM_COMMIT == UPSTREAM)
    from receval.models.parcae import ModelingParcae
    run.phase = "S1"
    raw = torch.load(model_dir / "pytorch_model.bin", map_location="cpu", weights_only=True)
    normalized = h.normalize_checkpoint(raw)
    run.loader_attempts += 1
    run.model = model = ModelingParcae.from_pretrained(model_dir, device="cpu", dtype=None)
    run.loader_returns += 1
    run.model_attribute_before = (hasattr(model, "_current_input_ids"), getattr(model, "_current_input_ids", None))
    run.check("official loader returned exact type in eval", type(model) is ModelingParcae and all(not m.training for m in model.modules()))
    run.check("post-load CPU runtime", h.runtime_matches(h.runtime_snapshot(torch)), h.runtime_snapshot(torch), failure="BLOCKED")
    parameters = h.parameter_inventory(model)
    run.check("parameter and registered buffer inventory", parameters["parameter_count"] == 144323136
              and parameters["unique_parameter_tensors"] == 61 and len(list(model.named_parameters(remove_duplicate=False))) == 62
              and list(dict(model.named_buffers(remove_duplicate=False))) == ["freqs_cis"]
              and sorted(model.value_embeds.keys()) == ["1", "3", "5"]
              and model.lm_head.weight is model.transformer.wte.weight, parameters)
    with torch.no_grad():
        state = h.state_snapshot(torch, model, normalized)
        for name, value in model.state_dict().items():
            flat = value.detach().reshape(-1)
            run.check("loaded tensor finite", all(bool(torch.isfinite(flat[i:i+262144]).all()) for i in range(0, flat.numel(), 262144)), {"name": name})
    save(run.public / "state_before.json", state)
    del raw, normalized
    config = model_config(model)
    save(run.public / "config_before.json", config)
    run.state_before, run.config_before = state, config
    try:
        library._validate_model(model)
    except ValueError as exc:
        raise Stop("FAIL", "Frozen library does not support this native model", str(exc)) from exc
    run.check("fresh model has no instrumentation", sys.getprofile() is None and all(not m._forward_hooks and not m._forward_pre_hooks for m in model.modules()), failure="BLOCKED")
    run.environment = {"python": sys.version, "platform": platform.platform(), "torch": str(torch.__version__),
                       "torch_file": torch.__file__, "executable": sys.executable, "prefix": sys.prefix,
                       "runtime": h.runtime_snapshot(torch), "environment_before": before_environment,
                       "environment_active": {k: os.environ.get(k) for k in ENV},
                       "freeze_commit": spec["freeze_commit"], "execution_head": spec["expected_head"],
                       "library_sha256": LIBRARY, "helper_sha256": HELPERS, "upstream": UPSTREAM,
                       "timing": "observed end-to-end API cost includes guards/readouts/policy/hooks; not pure model latency"}
    save(run.public / "environment.json", run.environment)
    causal_reference = None
    with torch.no_grad():
        run.phase = "S2"
        for length, seed in group_plan():
            run.context = {"prefix_length": length, "seed": seed, "source_article_key": sample["source_article_key"]}
            ids = torch.tensor([tokens[:length]], dtype=torch.long)
            torch.manual_seed(seed)
            rng = torch.get_rng_state().clone()
            natives, native_states, identity, byte_identity, first_adaptive = {}, {}, None, None, None
            for mode, depth in call_plan():
                record, outputs, prefixes, suffixes = run.call(model, library, ids, rng, mode, depth,
                    capture_prefix=(length == 64 and seed == 3101 and mode == "diagnostic"))
                actual_identity = (record["observed"]["h0"][0]["sha256"], record["rng_before_sha256"],
                                   record["rng_after_sha256"], record["observed"]["h0"][0]["rng_after_init_sha256"])
                if identity is None:
                    identity = actual_identity
                run.check("paired actual h0/RNG within group", actual_identity == identity, actual_identity, identity)
                actual_bytes = tuple((run.out / item["path"]).read_bytes() for item in
                                     (record["observed"]["h0"][0], record["rng_before"], record["rng_after"]))
                if byte_identity is None:
                    byte_identity = actual_bytes
                run.check("paired raw h0 and CPU RNG bytes within group", actual_bytes == byte_identity)
                if mode == "native":
                    natives[depth] = outputs[depth]
                    native_states[depth] = record["observed"]["readout_states"][0]["sha256"]
                else:
                    run.check("all emitted last logits match independent native depth bytes",
                              all(h.tensor_bytes(value) == h.tensor_bytes(natives[d]) for d, value in outputs.items()),
                              {str(d): h.tensor_hash(value) for d, value in outputs.items()})
                    run.check("resumed state hashes match independent native depth states", all(
                        record["observed"]["readout_states"][i]["sha256"] == native_states[d]
                        for i, d in enumerate(outputs)))
                if mode == "adaptive":
                    first_adaptive = (record["selected_depth"], record["tv_8_16"], record["library_counts"],
                                      record["library_state_sha256"],
                                      {d: h.tensor_bytes(value) for d, value in outputs.items()})
                if mode == "adaptive_repeat":
                    actual = (record["selected_depth"], record["tv_8_16"], record["library_counts"],
                              record["library_state_sha256"],
                              {d: h.tensor_bytes(value) for d, value in outputs.items()})
                    run.check("adaptive repeat exact decisions/counters/bytes", actual == first_adaptive)
                if prefixes:
                    causal_reference = (record, prefixes, suffixes, rng.clone(), ids.clone())
            run.groups_completed += 1
            print(f"{utc()} group complete length={length} seed={seed}", flush=True)
        run.check("six complete identity groups before causality", run.groups_completed == 6 and run.calls_completed == 54)
        run.phase = "S3"
        run.context = {"prefix_length": 64, "seed": 3101, "suffix_mutation_start": 32}
        base, prefix_before, suffix_before, rng, ids = causal_reference
        ids[:, 32:] = (ids[:, 32:] + 1) % 32768
        changed, _, prefix_after, suffix_after = run.call(model, library, ids, rng, "causal_mutated", capture_prefix=True)
        run.check("causal h0 and RNG exact", changed["observed"]["h0"][0]["sha256"] == base["observed"]["h0"][0]["sha256"]
                  and changed["rng_before_sha256"] == base["rng_before_sha256"] and changed["rng_after_sha256"] == base["rng_after_sha256"])
        run.check("causal raw h0 and RNG bytes exact", all(
            (run.out / left["path"]).read_bytes() == (run.out / right["path"]).read_bytes()
            for left, right in zip((base["observed"]["h0"][0], base["rng_before"], base["rng_after"]),
                                   (changed["observed"]["h0"][0], changed["rng_before"], changed["rng_after"]))))
        run.check("causal earlier prefix head bytes exact at all depths", prefix_before == prefix_after)
        run.check("causal perturbation has observable suffix contrast", any(suffix_before[d] != suffix_after[d] for d in (1, 2, 3)),
                  {str(d): suffix_before[d] != suffix_after[d] for d in (1, 2, 3)}, "at least one contrast", "BLOCKED")
        run.check("exact 55 calls complete", run.calls_started == run.calls_completed == 55)


def preserve(run):
    """Allowed after stop: read/hash only, no additional model forward."""
    run.phase, run.context = "S4", {}
    errors, proven_changes = [], []
    actual = {"state": "NOT TESTED", "files": "NOT TESTED", "git": "NOT TESTED", "packages": "NOT TESTED"}
    def inspect_one(label, action):
        try:
            action()
        except BaseException as exc:
            errors.append({"check": label, "type": type(exc).__name__, "reason": str(exc)})
            if getattr(exc, "status", None) == "FAIL":
                proven_changes.append(label + ": " + str(exc))
    if run.model is not None and run.state_before is not None and run.config_before is not None and run.model_attribute_before is not None:
        def state_check():
            with run.torch.no_grad():
                state = run.helper.state_snapshot(run.torch, run.model)
            save(run.public / "state_after.json", state)
            config = model_config(run.model)
            save(run.public / "config_after.json", config)
            before_exists, before_value = run.model_attribute_before if run.model_attribute_before is not None else (False, None)
            unchanged = (state == run.state_before and config == run.config_before
                         and hasattr(run.model, "_current_input_ids") == before_exists
                         and (not before_exists or run.model._current_input_ids is before_value)
                         and all(not m.training and not m._forward_hooks and not m._forward_pre_hooks for m in run.model.modules())
                         and run.model.lm_head.weight is run.model.transformer.wte.weight)
            actual["state"] = "PASS" if unchanged else "FAIL"
            if not unchanged:
                proven_changes.append("model state/config/attributes/mode/hooks")
        inspect_one("model state", state_check)
    if run.protected_before is not None:
        def file_check():
            after = {}
            for path, before in run.protected_before.items():
                try:
                    after[path] = info(path)
                    if after[path] != before:
                        proven_changes.append(path)
                except BaseException as exc:
                    errors.append({"check": "protected file", "path": path, "reason": repr(exc)})
            save(run.public / "protected_after.json", {"files": after})
            changed = [path for path in after if after[path] != run.protected_before[path]]
            actual["files"] = "FAIL" if changed else ("PASS" if len(after) == len(run.protected_before) else "BLOCKED")
        inspect_one("protected files", file_check)
    if run.git_before is not None:
        def git_check():
            after = {}
            for key in ("repo", "upstream"):
                try:
                    after[key] = git_state(Path(run.spec[key]))
                    if after[key] != run.git_before[key]:
                        proven_changes.append("Git state " + key)
                except BaseException as exc:
                    errors.append({"check": "Git", "key": key, "reason": repr(exc)})
            save(run.public / "git_after.json", after)
            actual["git"] = "FAIL" if any(after[k] != run.git_before[k] for k in after) else ("PASS" if len(after) == 2 else "BLOCKED")
        inspect_one("Git", git_check)
    if run.packages_before is not None:
        def package_check():
            after = run.helper.package_inventory()
            save(run.public / "packages_after.json", after)
            runtime = run.helper.runtime_snapshot(run.torch) if run.torch is not None else None
            actual["packages"] = "PASS" if after == run.packages_before and (runtime is None or run.helper.runtime_matches(runtime)) else "FAIL"
            if actual["packages"] == "FAIL":
                proven_changes.append("package inventory/runtime")
            actual["runtime_after"] = runtime
        inspect_one("packages/runtime", package_check)
    required = ("state", "files", "git", "packages")
    status = "FAIL" if proven_changes else ("BLOCKED" if errors else ("PASS" if all(actual[k] == "PASS" for k in required) else "NOT TESTED"))
    run.preservation = status
    save(run.public / "preservation.json", {"Purpose": "Post-stop preservation; no forward/retry", "Environment": run.environment,
        "Input": "loaded model and frozen sources", "Expected": "all available before baselines unchanged",
        "Actual": {**actual, "proven_changes": proven_changes, "read_errors": errors}, "Status": status})
    return status


def seal(run, status, error, started):
    for stream in (run.checks, run.rows):
        try:
            stream.close()
        except BaseException as exc:
            run.save_errors.append(repr(exc))
    if run.save_errors and status == "PASS":
        status = "BLOCKED"
    complete = run.calls_completed == 55 and run.groups_completed == 6
    if status == "PASS" and not complete:
        status = "BLOCKED"
    summary = {"Purpose": "Original 140M prefix adaptive correctness/cost smoke only", "Environment": run.environment,
               "Input": {"spec": run.spec, "weights_sha256": WEIGHTS, "inputs_sha256": INPUTS},
               "Expected": {"calls": 55, "groups": 6, "state_entries": 63, "all_identities": "bytewise equal"},
               "Actual": {"calls_started": run.calls_started, "calls_completed": run.calls_completed,
                          "groups_completed": run.groups_completed, "loader_attempts": run.loader_attempts,
                          "loader_returns": run.loader_returns, "checks": run.check_counts,
                          "preservation": run.preservation, "error": error, "save_errors": run.save_errors},
               "Status": status, "complete_coverage": complete, "ended_utc": utc(),
               "elapsed_seconds": time.monotonic() - started, "quality": "NOT TESTED", "training": "NOT TESTED",
               "hardware_efficiency_superiority": "NOT TESTED", "formal_acceptance_ready": False}
    payload = (json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode()
    entries = {str(path.relative_to(run.out)).replace("\\", "/"): info(path)
               for path in sorted(run.out.rglob("*")) if path.is_file()}
    entries["public/completion.json"] = {"bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
    save(run.out / "FULL_MANIFEST.json", {"entries": entries, "excluded": ["FULL_MANIFEST.json", "public/GIT_BUNDLE_MANIFEST.json"]})
    save(run.public / "GIT_BUNDLE_MANIFEST.json", {"entries": {k: v for k, v in entries.items() if k.startswith("public/")},
                                                 "excluded": ["public/GIT_BUNDLE_MANIFEST.json"], "private_artifacts_remain_on_target": True})
    with (run.public / "completion.json").open("xb") as stream:
        stream.write(payload)
    print(json.dumps({"status": status, "calls": run.calls_completed, "groups": run.groups_completed, "preservation": run.preservation}), flush=True)
    return 0 if status == "PASS" else 2


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    if not args.spec.is_absolute() or not args.out.is_absolute():
        parser.error("spec and out must be absolute")
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    out = args.out.resolve()
    for name in ("repo", "upstream", "model_dir", "inputs_path", "source_manifest_path"):
        path = Path(spec[name]).resolve()
        if out == path or out.is_relative_to(path if path.is_dir() else path.parent):
            parser.error("output must be outside protected inputs/source trees")
    out.mkdir(parents=True, exist_ok=False)
    run, status, error = None, "BLOCKED", None
    started = time.monotonic()
    def interrupted(signum, frame):
        raise Stop("BLOCKED", "Execution interrupted", signum)
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    try:
        run = Run(spec, out)
        save(run.public / "spec.json", spec)
        execute(run)
        status = "PASS"
    except BaseException as exc:
        status = getattr(exc, "status", "BLOCKED")
        error = {"phase": run.phase if run else "bootstrap", "reason": str(exc), "type": type(exc).__name__,
                 "actual": getattr(exc, "actual", None), "traceback": traceback.format_exc()}
    finally:
        if run is not None:
            try:
                custody = preserve(run)
                if custody == "FAIL":
                    status = "FAIL"
                elif status == "PASS" and custody != "PASS":
                    status = "BLOCKED"
            except BaseException as exc:
                run.save_errors.append({"preservation": repr(exc)})
                if status == "PASS":
                    status = "BLOCKED"
    try:
        if run is None:
            save(out / "EMERGENCY.json", {"status": status, "error": error})
            return 2
        return seal(run, status, error, started)
    except BaseException as exc:
        emergency = {"status": "BLOCKED", "original_status": status, "original_error": error,
                     "sealing_error": repr(exc), "traceback": traceback.format_exc()}
        try:
            save(out / "EMERGENCY.json", emergency)
        finally:
            print(json.dumps(emergency), file=sys.stderr, flush=True)
        return 2


if __name__ == "__main__":
    sys.exit(main())
