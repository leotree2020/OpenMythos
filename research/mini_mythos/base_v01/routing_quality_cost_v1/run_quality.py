"""Paired real-model quality outputs and complete CPU API timing; labels are auditor-only.

No module-scope numerical imports. Reuses the previously frozen observation and
preservation helpers without invoking, patching or rerunning their smoke driver.
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
import struct
import sys
import time
import traceback

SPACE = "bookish-pancake-vwqx7rr9x5w3wxjr"
PYTHON = "/workspaces/mythos-base-v01-cpu312/bin/python"
EXPECTED_REPO = "/workspaces/mythos-routing-quality-cost-cpu-v1"
BRANCH = "mythos-routing-quality-cost-cpu-v1"
BASE = "a4e9b27ff3c7ca8dbfd5760d5c630f59a9d0a683"
SMOKE_SHA = "f29155eb3af5989a1da1f938dc2b7e7ca894a2dc960a0eefb6e4352517d0a37c"
LIBRARY_SHA = "daa6b5b014f9d5f77cc47e2ba14a7027065c135b2cac7f6bcda58d0e6d6457b8"
HELPER_SHA = "02fcaae5a7a09ede68a662592668099ad60f08af51aad683c5c7d37926163a68"
WEIGHTS_SHA = "ed6eb306464dd0d694e9eacd58f7e06ac3e44b43cb7c5c79dbcb1543059c6621"
CONFIG_SHA = "5c8fc785c2f6dba67d0370ad715034860e3b22bfce850da825c06baa03923c13"
UPSTREAM_SHA = "69284c13746e849104f738d6d1a347b1f457df76"
SEEDS = (3101, 3202)
LENGTH, ARTICLES, CALLS = 128, 16, 32


class Stop(Exception):
    def __init__(self, status, reason, actual=None):
        super().__init__(reason)
        self.status, self.actual = status, actual


def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha(data):
    return hashlib.sha256(data).hexdigest()


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


def pinned_import(name, path, expected_sha):
    if info(path)["sha256"] != expected_sha:
        raise Stop("FAIL", "Imported source SHA differs from pin", str(path))
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise Stop("BLOCKED", "Cannot create pinned module spec", str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def validate_inputs(payload):
    if (not isinstance(payload, dict) or payload.get("context_tokens") != LENGTH
            or payload.get("seeds") != list(SEEDS)):
        raise Stop("FAIL", "Frozen input length/seed contract differs")
    samples = payload.get("samples")
    if not isinstance(samples, list) or len(samples) != ARTICLES:
        raise Stop("FAIL", "Exactly16 source samples required")
    for index, sample in enumerate(samples):
        if not isinstance(sample, dict):
            raise Stop("FAIL", "Sample metadata must be an object", index)
        tokens = sample.get("tokens")
        if (sample.get("index") != index or not isinstance(tokens, list) or len(tokens) != LENGTH
                or not all(type(x) is int and 0 <= x < 32768 for x in tokens)):
            raise Stop("FAIL", "Exact indexed128-token prefix required", index)
        if (sample.get("input_ids_sha256") != sha(canonical(tokens))
                or sample.get("raw_input_sha256") != sha(struct.pack("<" + "q" * LENGTH, *tokens))):
            raise Stop("FAIL", "Input prefix hash mismatch", index)
        if (not all(isinstance(sample.get(key), str) and sample[key] for key in ("source_article_key", "article_id"))
                or type(sample.get("heading_row")) is not int):
            raise Stop("FAIL", "Source metadata missing", index)
    for key in ("source_article_key", "article_id", "heading_row", "input_ids_sha256"):
        if len({sample[key] for sample in samples}) != ARTICLES:
            raise Stop("FAIL", "Duplicate selected source/prefix identity", key)
    if [s["article_id"] for s in samples] != sorted(s["article_id"] for s in samples):
        raise Stop("FAIL", "Selected source order differs from ascending article_id")
    return samples


def plan(samples):
    return [(sample["index"], seed) for sample in samples for seed in SEEDS]


def execute(run, smoke):
    spec = run.spec
    repo, upstream, model_dir = (Path(spec[k]).resolve() for k in ("repo", "upstream", "model_dir"))
    inputs, data_manifest, source_manifest = (Path(spec[k]).resolve() for k in (
        "inputs_path", "data_manifest_path", "source_manifest_path"))
    run.check("designated Codespace", os.environ.get("CODESPACE_NAME") == SPACE, os.environ.get("CODESPACE_NAME"), SPACE, "BLOCKED")
    run.check("target interpreter and isolated runtime", platform.system() == "Linux" and sys.executable == PYTHON
              and platform.python_version() == "3.12.3" and sys.flags.isolated and sys.dont_write_bytecode,
              {"python": sys.version, "executable": sys.executable}, failure="BLOCKED")
    run.check("designated routing worktree and branch", str(repo) == EXPECTED_REPO and spec["branch"] == BRANCH,
              {"repo": str(repo), "branch": spec["branch"]})
    run.check("fixed prior V3 evidence path", str(Path(spec["prior_run_dir"]).resolve())
              == "/workspaces/mythos-evidence/base_v01/routing_feasibility/attempt-v3")
    run.check("full frozen identities", all(re.fullmatch("[0-9a-f]{40}", spec.get(k, "")) for k in ("freeze_commit", "expected_head")))
    run.git_before = {"repo": smoke.git_state(repo), "upstream": smoke.git_state(upstream)}
    run.check("frozen clean execution checkout", run.git_before["repo"] == {
        "head": spec["expected_head"], "branch": BRANCH, "status": ""}, run.git_before["repo"])
    run.check("pinned clean upstream", run.git_before["upstream"]["head"] == UPSTREAM_SHA
              and run.git_before["upstream"]["status"] == "", run.git_before["upstream"])
    smoke.git(repo, "merge-base", "--is-ancestor", BASE, spec["freeze_commit"])
    smoke.git(repo, "merge-base", "--is-ancestor", spec["freeze_commit"], spec["expected_head"])
    run.check("source manifest hash", info(source_manifest)["sha256"] == spec["source_manifest_sha256"])
    run.check("new data manifest hash", info(data_manifest)["sha256"] == spec["data_manifest_sha256"])
    run.check("new input payload hash", info(inputs)["sha256"] == spec["inputs_sha256"])
    run.check("unchanged128-token inputs exact prior bytes", info(inputs) == {
        "bytes": 58091, "sha256": "ae5f8ad5fd53d25afaf29487a650dc0300528b0926c9883652475c4ca7db127f"})
    data = json.loads(data_manifest.read_text(encoding="utf-8"))
    if data.get("Status") != "PASS":
        raise Stop(data.get("Status") if data.get("Status") in ("FAIL", "BLOCKED") else "BLOCKED", "Data stage did not pass")
    run.check("data completion binds exact16sample32call inputs", data["Actual"]["sample_count"] == ARTICLES
              and data["Actual"]["case_count"] == CALLS
              and data["artifacts"]["private/inputs.json"] == info(inputs))
    library_path = repo / "research/mini_mythos/base_v01/adaptive_depth_v1/adaptive_depth.py"
    helper_path = repo / "research/mini_mythos/base_v01/depth_16_32_v1/run_depth_budget.py"
    smoke_path = repo / "research/mini_mythos/base_v01/adaptive_140m_smoke_v1/run_smoke.py"
    protected = {model_dir / "pytorch_model.bin": {"sha256": WEIGHTS_SHA}, model_dir / "config.json": {"sha256": CONFIG_SHA},
                 library_path: {"sha256": LIBRARY_SHA}, helper_path: {"sha256": HELPER_SHA}, smoke_path: {"sha256": SMOKE_SHA},
                 inputs: {"sha256": spec["inputs_sha256"]}, data_manifest: {"sha256": spec["data_manifest_sha256"]}}
    for name, expected in json.loads(source_manifest.read_text(encoding="utf-8")).items():
        path = Path(name).resolve() if Path(name).is_absolute() else (repo / name).resolve()
        if path in protected and protected[path]["sha256"] != expected["sha256"]:
            raise Stop("FAIL", "Source manifest conflicts with fixed input/source pin", str(path))
        protected[path] = expected
    before = {}
    for path, expected in protected.items():
        actual = info(path)
        run.check("protected source/input exact bytes", actual["sha256"] == expected["sha256"]
                  and ("bytes" not in expected or actual["bytes"] == expected["bytes"]), {"path": str(path), "actual": actual}, expected)
        before[str(path)] = actual
    before[str(source_manifest)] = info(source_manifest)
    run.protected_before = before
    save(run.public / "protected_before.json", {"files": before, "git": run.git_before})
    payload = json.loads(inputs.read_text(encoding="utf-8"))
    samples = validate_inputs(payload)
    run.check("exact16new128token inputs validated", len(samples) == ARTICLES)
    save(run.private / "input_prefixes.json", payload)
    save(run.public / "input_inventory.json", {"samples": [{k: v for k, v in s.items() if k != "tokens"} for s in samples],
                                               "context_tokens": LENGTH, "seeds": list(SEEDS), "data_manifest_sha256": spec["data_manifest_sha256"]})
    run.helper = smoke.load_module("mythos_routing_frozen_helpers", helper_path, HELPER_SHA)
    h = run.helper
    run.packages_before = h.package_inventory()
    save(run.public / "packages_before.json", run.packages_before)
    before_env = {k: os.environ.get(k) for k in smoke.ENV}
    for key, value in smoke.ENV.items():
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
    library = smoke.load_module("mythos_routing_frozen_controller", library_path, LIBRARY_SHA)
    run.check("frozen threshold/source/depths", library.TV_THRESHOLD == 0.01 and library.DEPTHS == (8, 16, 32)
              and library.UPSTREAM_COMMIT == UPSTREAM_SHA)
    from receval.models.parcae import ModelingParcae
    run.phase = "R1"
    raw = torch.load(model_dir / "pytorch_model.bin", map_location="cpu", weights_only=True)
    normalized = h.normalize_checkpoint(raw)
    run.loader_attempts += 1
    run.model = model = ModelingParcae.from_pretrained(model_dir, device="cpu", dtype=None)
    run.loader_returns += 1
    run.model_attribute_before = (hasattr(model, "_current_input_ids"), getattr(model, "_current_input_ids", None))
    run.check("one official native model in eval", type(model) is ModelingParcae and all(not m.training for m in model.modules()))
    run.check("post-load runtime", h.runtime_matches(h.runtime_snapshot(torch)), h.runtime_snapshot(torch), failure="BLOCKED")
    parameters = h.parameter_inventory(model)
    run.check("parameter/buffer inventory", parameters["parameter_count"] == 144323136 and parameters["unique_parameter_tensors"] == 61
              and len(list(model.named_parameters(remove_duplicate=False))) == 62
              and list(dict(model.named_buffers(remove_duplicate=False))) == ["freqs_cis"]
              and sorted(model.value_embeds.keys()) == ["1", "3", "5"] and model.lm_head.weight is model.transformer.wte.weight, parameters)
    with torch.no_grad():
        state = h.state_snapshot(torch, model, normalized)
        for name, value in model.state_dict().items():
            flat = value.detach().reshape(-1)
            run.check("loaded tensor finite", all(bool(torch.isfinite(flat[i:i+262144]).all()) for i in range(0, flat.numel(), 262144)), {"name": name})
    save(run.public / "state_before.json", state)
    del raw, normalized
    config = smoke.model_config(model)
    save(run.public / "config_before.json", config)
    run.state_before, run.config_before = state, config
    try:
        library._validate_model(model)
    except ValueError as exc:
        raise Stop("FAIL", "Frozen controller rejected the native model", str(exc)) from exc
    run.check("fresh model has no instrumentation", sys.getprofile() is None
              and all(not m._forward_hooks and not m._forward_pre_hooks for m in model.modules()), failure="BLOCKED")
    run.environment = {"python": sys.version, "platform": platform.platform(), "torch": str(torch.__version__),
        "torch_file": torch.__file__, "executable": sys.executable, "prefix": sys.prefix, "runtime": h.runtime_snapshot(torch),
        "environment_before": before_env, "environment_active": {k: os.environ.get(k) for k in smoke.ENV},
        "freeze_commit": spec["freeze_commit"], "execution_head": spec["expected_head"], "upstream": UPSTREAM_SHA,
        "library_sha256": LIBRARY_SHA, "helper_sha256": HELPER_SHA, "smoke_observer_sha256": SMOKE_SHA,
        "timing": "Separate uninstrumented perf_counter interval around the entire unchanged public CPU API; includes validation/hash/readouts/policy, excludes caller RNG setup and post-return evidence IO. Model/tokenization setup excluded; no tokenizer/server/generation benchmark."}
    save(run.public / "environment.json", run.environment)
    prior = Path(spec["prior_run_dir"]).resolve()
    prior_completion = json.loads((prior / "worker/public/completion.json").read_text())
    run.check("prior V3 complete PASS baseline", prior_completion["Status"] == "PASS"
              and prior_completion["Actual"]["calls_completed"] == 32)
    references, pairing = {}, {}
    with torch.no_grad():
        run.phase = "Q1"
        for sample in samples:
            ids = torch.tensor([sample["tokens"]], dtype=torch.long)
            for seed_index, seed in enumerate(SEEDS):
                case = 2 * sample["index"] + seed_index
                pair = {}
                for arm in arm_order(case, 0):
                    check_budget(run)
                    run.context = {"case_index": case, "article_index": sample["index"],
                        "source_article_key": sample["source_article_key"], "article_id": sample["article_id"],
                        "heading_row": sample["heading_row"], "prefix_length": LENGTH, "seed": seed,
                        "phase": "quality", "arm": arm}
                    torch.manual_seed(seed)
                    rng = torch.get_rng_state().clone()
                    mode, depth = ("adaptive", None) if arm == "adaptive" else ("fixed", 32)
                    record, outputs, _, _ = run.call(model, library, ids, rng, mode, depth)
                    run.check("quality runtime input equals frozen prefix", record["input_sha256"] == sample["raw_input_sha256"]
                              and record["input_ids_json_sha256"] == sha(canonical([sample["tokens"]])))
                    identity = tuple((run.out / meta["path"]).read_bytes() for meta in (
                        record["observed"]["h0"][0], record["rng_before"], record["rng_after"]))
                    identity += (record["observed"]["h0"][0]["rng_after_init_sha256"],)
                    pairing.setdefault(seed, identity)
                    run.check("same seed actual h0 and RNG bytes across all paired quality calls", identity == pairing[seed])
                    selected = record["selected_depth"]
                    selected_bytes = h.tensor_bytes(outputs[selected])
                    if arm == "adaptive":
                        old = json.loads((prior / f"worker/public/call_{case+1:03d}.json").read_text())
                        run.check("adaptive route and TV exactly reproduce V3", selected == old["selected_depth"]
                                  and record["tv_8_16"] == old["tv_8_16"])
                        run.check("adaptive old prefix and h0 exact", record["input_sha256"] == old["input_sha256"]
                                  and identity[0] == (prior / "worker" / old["observed"]["h0"][0]["path"]).read_bytes())
                        for key, value in outputs.items():
                            run.check("adaptive checkpoint logits exactly reproduce V3",
                                      h.tensor_bytes(value) == (prior / "worker" / old["outputs"][str(key)]["path"]).read_bytes(), {"depth": key})
                    references[(case, arm)] = {"record": record, "selected_bytes": selected_bytes}
                    pair[arm] = record
                adaptive, fixed = pair["adaptive"], pair["fixed32"]
                if adaptive["selected_depth"] == 32:
                    run.check("depth32 adaptive and fixed outputs byte identical", references[(case,"adaptive")]["selected_bytes"]
                              == references[(case,"fixed32")]["selected_bytes"])
                run.quality_pairs.append({"case_index": case, "article_index": sample["index"], "seed": seed,
                    "source_article_key": sample["source_article_key"], "order": list(arm_order(case, 0)),
                    "adaptive_call": adaptive["call"], "fixed32_call": fixed["call"],
                    "adaptive_depth": adaptive["selected_depth"], "tv_8_16": adaptive["tv_8_16"],
                    "adaptive_logits": adaptive["outputs"][str(adaptive["selected_depth"])],
                    "fixed32_logits": fixed["outputs"]["32"], "paired_h0_sha256": adaptive["library_h0_sha256"],
                    "paired_rng_before_sha256": adaptive["rng_before_sha256"], "paired_rng_after_sha256": adaptive["rng_after_sha256"]})
            run.groups_completed += 1
            print(f"{utc()} quality article complete index={sample['index']}", flush=True)
        run.check("64 instrumented quality calls complete", run.calls_started == run.calls_completed == 64
                  and run.groups_completed == 16 and len(run.quality_pairs) == 32)
        save(run.public / "quality_pairs.json", {"Purpose": "Paired logits only; targets never read by worker", "Environment": run.environment,
            "Input": {"articles": 16, "tokens": 128, "seeds": list(SEEDS)},
            "Expected": "32 same-input same-h0 pairs; one adaptive and one fixed32 call each",
            "Actual": {"pairs": run.quality_pairs}, "Status": "PASS"})
        run.phase = "T1"
        ids_by_case = {2 * sample["index"] + j: torch.tensor([sample["tokens"]], dtype=torch.long)
                       for sample in samples for j in range(2)}
        for phase, round_index, case, position, arm in timing_plan():
            timed_call(run, library, ids_by_case[case], SEEDS[case % 2], references[(case, arm)],
                       phase, round_index, case, position, arm)
        run.check("exact full194 call coverage", total_started(run) == total_completed(run) == 194
                  and run.warmup_started == run.warmup_completed == 2 and run.timed_started == run.timed_completed == 128)
        save(run.public / "timing_summary.json", {"Purpose": "Complete current CPU API wall-time comparison", "Environment": run.environment,
            "Input": {"rounds": 2, "cases": 32, "arms": ["adaptive", "fixed32"]},
            "Expected": "Two opposite-order timed pairs per case, all outputs/h0/RNG exactly match instrumented reference",
            "Actual": {"warmup_calls": run.warmup_completed, "timed_calls": run.timed_completed,
                       "timing_rows": run.timing_records}, "Status": "PASS"})


def arm_order(case, round_index):
    if type(case) is not int or not 0 <= case < 32 or round_index not in (0, 1):
        raise ValueError("Invalid frozen case/round")
    return ("adaptive", "fixed32") if (case + round_index) % 2 == 0 else ("fixed32", "adaptive")


def timing_plan():
    result = [("warmup", None, 0, 0, "fixed32"), ("warmup", None, 0, 1, "adaptive")]
    for round_index in (0, 1):
        for case in range(32):
            result.extend(("timed", round_index, case, position, arm)
                          for position, arm in enumerate(arm_order(case, round_index)))
    return result


def total_started(run):
    return run.calls_started + run.warmup_started + run.timed_started


def total_completed(run):
    return run.calls_completed + run.warmup_completed + run.timed_completed


def check_budget(run):
    run.check("194 total model-call ceiling before invocation", total_started(run) < 194, total_started(run), "<194")


def measure_api(invoke, clock=time.perf_counter, cpu_clock=time.process_time):
    cpu_start = cpu_clock()
    start = clock()
    result = invoke()
    elapsed = clock() - start
    cpu_elapsed = cpu_clock() - cpu_start
    return result, elapsed, cpu_elapsed


def reference_matches(result, recorded, selected_bytes, actual_bytes):
    return (actual_bytes == selected_bytes and result.selected_depth == recorded["selected_depth"]
            and result.h0_sha256 == recorded["library_h0_sha256"]
            and result.rng_before_sha256 == recorded["rng_before_sha256"]
            and result.rng_after_sha256 == recorded["rng_after_sha256"]
            and result.prefix_sha256 == recorded["input_sha256"]
            and result.tv_8_16 == recorded["tv_8_16"] and result.counts == recorded["library_counts"])


def timed_call(run, library, ids, seed, reference, phase, round_index, case, position, arm):
    t, h, model = run.torch, run.helper, run.model
    run.context = {"phase": phase, "round": round_index, "case_index": case, "article_index": case // 2,
                   "seed": seed, "position": position, "arm": arm}
    check_budget(run)
    run.check("timing phase has no observer hooks or profiler", sys.getprofile() is None
              and all(not m._forward_hooks and not m._forward_pre_hooks for m in model.modules()), failure="BLOCKED")
    run.check("timing CPU runtime unchanged", h.runtime_matches(h.runtime_snapshot(t)), failure="BLOCKED")
    t.manual_seed(seed)
    before_rng = h.tensor_bytes(t.get_rng_state())
    before_input = h.tensor_bytes(ids)
    before_attribute = (hasattr(model, "_current_input_ids"), getattr(model, "_current_input_ids", None))
    label = f"{phase}_{len(run.timing_records)+1:03d}"
    counter = "warmup" if phase == "warmup" else "timed"
    setattr(run, counter + "_started", getattr(run, counter + "_started") + 1)
    row = {**run.context, "ordinal": len(run.timing_records)+1, "status": "NOT TESTED", "elapsed_seconds": None, "cpu_seconds": None,
           "started_utc": utc(), "quality_reference_call": reference["record"]["call"], "error": None}
    error = None
    try:
        # The timer wraps the unchanged public API, including its source/model
        # validation, state hashes, finite checks, policy and all readouts.
        # No profiler, observer hook or file writing occurs inside this interval.
        invoke = (lambda: library.adaptive_next_token(model, ids)) if arm == "adaptive" else (
            lambda: library.fixed_next_token(model, ids, depth=32))
        result, elapsed, cpu_elapsed = measure_api(invoke)
        row["elapsed_seconds"] = elapsed
        row["cpu_seconds"] = cpu_elapsed
        run.check("positive finite complete API elapsed", math.isfinite(elapsed) and elapsed > 0
                  and math.isfinite(cpu_elapsed) and cpu_elapsed > 0)
        actual_bytes = h.tensor_bytes(result.last_logits)
        run.check("timed output routing h0 RNG counters exactly match quality reference",
                  reference_matches(result, reference["record"], reference["selected_bytes"], actual_bytes))
        run.check("timed actual RNG equals library annotation", sha(before_rng) == result.rng_before_sha256
                  and h.tensor_hash(t.get_rng_state()) == result.rng_after_sha256)
        run.check("timed input unchanged", h.tensor_bytes(ids) == before_input)
        run.check("timed API restores temporary input attribute", hasattr(model, "_current_input_ids") == before_attribute[0]
                  and (not before_attribute[0] or model._current_input_ids is before_attribute[1]))
        run.check("timed call leaves no observation hooks", sys.getprofile() is None
                  and all(not m._forward_hooks and not m._forward_pre_hooks for m in model.modules()))
        row.update(selected_depth=result.selected_depth, tv_8_16=result.tv_8_16, h0_sha256=result.h0_sha256,
                   input_sha256=result.prefix_sha256, rng_before_sha256=result.rng_before_sha256,
                   rng_after_sha256=result.rng_after_sha256, library_counts=result.counts,
                   selected_logits=run.raw(label + "_last_logits.bin", result.last_logits), status="PASS")
        setattr(run, counter + "_completed", getattr(run, counter + "_completed") + 1)
    except BaseException as exc:
        error = exc
        row["status"] = getattr(exc, "status", "FAIL" if isinstance(exc, ValueError) else "BLOCKED")
        row["error"] = {"type": type(exc).__name__, "reason": str(exc), "traceback": traceback.format_exc()}
    finally:
        row["ended_utc"] = utc()
        run.timing_records.append(row)
        run.timing_rows.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
        print(f"{utc()} {label} {row['status']} case={case} arm={arm}", flush=True)
    if error is not None:
        raise error


def seal(run, status, error, started):
    for stream in (run.checks, run.rows, run.timing_rows):
        try:
            stream.close()
        except BaseException as exc:
            run.save_errors.append(repr(exc))
    complete = (run.calls_started == run.calls_completed == 64 and run.groups_completed == 16
                and len(run.quality_pairs) == 32 and run.warmup_started == run.warmup_completed == 2
                and run.timed_started == run.timed_completed == 128 and len(run.timing_records) == 130)
    if status == "PASS" and (not complete or run.save_errors or run.preservation != "PASS"):
        status = "BLOCKED"
    summary = {"Purpose": "Paired quality logits and complete CPU API timings; labels are independent-auditor-only", "Environment": run.environment,
        "Input": {"spec": run.spec, "weights_sha256": WEIGHTS_SHA, "inputs_sha256": run.spec.get("inputs_sha256")},
        "Expected": {"instrumented_calls": 64, "warmup_calls": 2, "timed_calls": 128, "total_model_calls": 194,
                     "articles": 16, "tokens": 128, "seeds": list(SEEDS), "threshold": 0.01},
        "Actual": {"calls_started": run.calls_started, "calls_completed": run.calls_completed, "groups_completed": run.groups_completed,
            "warmup_calls_started": run.warmup_started, "warmup_calls_completed": run.warmup_completed,
            "timed_calls_started": run.timed_started, "timed_calls_completed": run.timed_completed,
            "total_model_calls_started": total_started(run), "total_model_calls_completed": total_completed(run),
            "loader_attempts": run.loader_attempts, "loader_returns": run.loader_returns, "checks": run.check_counts,
            "preservation": run.preservation, "error": error, "save_errors": run.save_errors},
        "Status": status, "complete_coverage": complete, "ended_utc": utc(), "elapsed_seconds": time.monotonic() - started,
        "quality_analysis": "Auditor only", "training": "NOT TESTED", "formal_acceptance_ready": False}
    payload = (json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
    entries = {str(path.relative_to(run.out)).replace("\\", "/"): info(path) for path in sorted(run.out.rglob("*")) if path.is_file()}
    entries["public/completion.json"] = {"bytes": len(payload), "sha256": sha(payload)}
    save(run.out / "FULL_MANIFEST.json", {"entries": entries, "excluded": ["FULL_MANIFEST.json", "public/GIT_BUNDLE_MANIFEST.json"]})
    save(run.public / "GIT_BUNDLE_MANIFEST.json", {"entries": {k: v for k, v in entries.items() if k.startswith("public/")},
        "excluded": ["public/GIT_BUNDLE_MANIFEST.json"], "private_artifacts_remain_on_target": True})
    with (run.public / "completion.json").open("xb") as stream:
        stream.write(payload)
    print(json.dumps({"Status": status, "instrumented_calls": run.calls_completed,
                      "timed_calls": run.timed_completed, "total_model_calls": total_completed(run)}), flush=True)
    return 0 if status == "PASS" else 2


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    if not args.spec.is_absolute() or not args.out.is_absolute():
        parser.error("spec/out must be absolute")
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    out = args.out.resolve()
    for name in ("repo", "upstream", "model_dir", "inputs_path", "data_manifest_path", "source_manifest_path", "prior_run_dir"):
        path = Path(spec[name]).resolve()
        if out == path or out.is_relative_to(path if path.is_dir() else path.parent):
            parser.error("output must be outside protected input/source directories")
    out.mkdir(parents=True, exist_ok=False)
    started, run, smoke = time.monotonic(), None, None
    status, error = "BLOCKED", None
    def interrupted(signum, frame):
        raise Stop("BLOCKED", "Execution interrupted", signum)
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    try:
        smoke_path = Path(spec["repo"]) / "research/mini_mythos/base_v01/adaptive_140m_smoke_v1/run_smoke.py"
        smoke = pinned_import("mythos_prior_smoke_observers", smoke_path, SMOKE_SHA)
        run = smoke.Run(spec, out)
        run.quality_pairs, run.timing_records = [], []
        run.warmup_started = run.warmup_completed = run.timed_started = run.timed_completed = 0
        run.timing_rows = (run.public / "timing_calls.jsonl").open("x", encoding="utf-8", buffering=1)
        save(run.public / "spec.json", spec)
        execute(run, smoke)
        status = "PASS"
    except BaseException as exc:
        status = getattr(exc, "status", "FAIL" if isinstance(exc, (ValueError, AssertionError)) else "BLOCKED")
        error = {"phase": run.phase if run else "bootstrap", "reason": str(exc), "type": type(exc).__name__,
                 "actual": getattr(exc, "actual", None), "traceback": traceback.format_exc()}
    finally:
        if run is not None:
            try:
                custody = smoke.preserve(run)
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
            save(out / "EMERGENCY.json", {"Status": status, "error": error, "model_calls": 0})
            return 2
        return seal(run, status, error, started)
    except BaseException as exc:
        emergency = {"Status": "BLOCKED", "original_status": status, "original_error": error,
                     "sealing_error": repr(exc), "traceback": traceback.format_exc()}
        try:
            save(out / "EMERGENCY.json", emergency)
        finally:
            print(json.dumps(emergency), file=sys.stderr, flush=True)
        return 2


if __name__ == "__main__":
    sys.exit(main())
