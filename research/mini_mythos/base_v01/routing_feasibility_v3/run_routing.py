"""Exactly32 frozen adaptive calls on16 new-to-routing128-token prefixes.

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
EXPECTED_REPO = "/workspaces/mythos-routing-feasibility-cpu-v3"
BRANCH = "mythos-routing-feasibility-cpu-v3"
BASE = "b470cec1ebc6f9a675ce5b674f2073c14d66c237"
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


def summarize_routing(records, complete):
    if not complete:
        return {"early_exit_observed": "NOT TESTED", "feasibility": "NOT TESTED", "complete_cases": len(records)}
    if len(records) != CALLS:
        raise Stop("FAIL", "Complete routing summary has wrong record count")
    counts = {"16": 0, "32": 0}
    per_article = []
    for index in range(ARTICLES):
        pair = records[2 * index:2 * index + 2]
        for seed, row in zip(SEEDS, pair):
            if (row["article_index"] != index or row["seed"] != seed or row["selected_depth"] not in (16, 32)
                    or not math.isfinite(row["tv_8_16"]) or not 0 <= row["tv_8_16"] <= 1
                    or row["selected_depth"] != (16 if row["tv_8_16"] <= 0.01 else 32)):
                raise Stop("FAIL", "Routing record violates frozen order/predicate")
            counts[str(row["selected_depth"])] += 1
        per_article.append({"article_index": index, "source_article_key": pair[0]["source_article_key"],
                            "selected_depths": [r["selected_depth"] for r in pair],
                            "both_seeds_early": all(r["selected_depth"] == 16 for r in pair),
                            "any_seed_early": any(r["selected_depth"] == 16 for r in pair)})
    return {"early_exit_observed": "YES" if counts["16"] else "NO",
            "feasibility": "EARLY_EXIT_OBSERVED" if counts["16"] else "NO_EARLY_EXIT_IN_THIS_SAMPLE",
            "selected_depth_counts": counts, "early_exit_fraction": counts["16"] / CALLS,
            "article_both_seeds_early": sum(a["both_seeds_early"] for a in per_article),
            "article_any_seed_early": sum(a["any_seed_early"] for a in per_article),
            "per_article": per_article, "threshold": 0.01, "quality_improvement": "NOT TESTED",
            "net_acceleration": "NOT TESTED", "population_generalization": "NOT TESTED"}


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
    data = json.loads(data_manifest.read_text(encoding="utf-8"))
    if data.get("Status") != "PASS":
        raise Stop(data.get("Status") if data.get("Status") in ("FAIL", "BLOCKED") else "BLOCKED", "Data stage did not pass")
    run.check("data completion binds exact16sample32call inputs", data["Actual"]["sample_count"] == ARTICLES
              and data["Actual"]["call_budget"] == CALLS
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
        "timing": "Instrumented API including guards/readouts/policy/hooks; no benchmark comparison"}
    save(run.public / "environment.json", run.environment)
    pairing = {}
    with torch.no_grad():
        run.phase = "R2"
        for sample in samples:
            ids = torch.tensor([sample["tokens"]], dtype=torch.long)
            for seed in SEEDS:
                run.check("32-call ceiling before invocation", run.calls_started < CALLS, run.calls_started, "<32")
                run.context = {"article_index": sample["index"], "source_article_key": sample["source_article_key"],
                               "article_id": sample["article_id"], "heading_row": sample["heading_row"],
                               "prefix_length": LENGTH, "seed": seed}
                torch.manual_seed(seed)
                rng = torch.get_rng_state().clone()
                record, _, _, _ = run.call(model, library, ids, rng, "adaptive")
                run.check("runtime input matches frozen prefix bytes", record["input_sha256"] == sample["raw_input_sha256"]
                          and record["input_ids_json_sha256"] == sha(canonical([sample["tokens"]])))
                identity = tuple((run.out / meta["path"]).read_bytes() for meta in (
                    record["observed"]["h0"][0], record["rng_before"], record["rng_after"]))
                identity += (record["observed"]["h0"][0]["rng_after_init_sha256"],)
                if seed not in pairing:
                    pairing[seed] = identity
                run.check("same-seed h0/RNG pairing across equal-length articles", identity == pairing[seed],
                          {"seed": seed, "h0_sha256": record["observed"]["h0"][0]["sha256"]})
                run.routing_records.append({"call": record["call"], "article_index": sample["index"],
                    "source_article_key": sample["source_article_key"], "seed": seed, "selected_depth": record["selected_depth"],
                    "tv_8_16": record["tv_8_16"], "actual_counts": record["actual_counts"],
                    "api_observed_seconds": record["api_observed_seconds"], "policy_seconds": record["policy_seconds"]})
            run.groups_completed += 1
            print(f"{utc()} article complete index={sample['index']}", flush=True)
    run.check("exact32calls16articles complete", run.calls_started == run.calls_completed == CALLS
              and run.groups_completed == ARTICLES and len(run.routing_records) == CALLS)
    save(run.public / "routing_results.json", {"Purpose": "Observed routing only; no quality score", "Environment": run.environment,
        "Input": {"articles": ARTICLES, "tokens": LENGTH, "seeds": list(SEEDS)}, "Expected": "All32 valid calls under frozen0.01 predicate",
        "Actual": {"records": run.routing_records, "routing": summarize_routing(run.routing_records, True)}, "Status": "PASS"})


def seal(run, status, error, started):
    for stream in (run.checks, run.rows):
        try:
            stream.close()
        except BaseException as exc:
            run.save_errors.append(repr(exc))
    complete = run.calls_started == run.calls_completed == CALLS and run.groups_completed == ARTICLES and len(run.routing_records) == CALLS
    if status == "PASS" and (not complete or run.save_errors or run.preservation != "PASS"):
        status = "BLOCKED"
    routing = summarize_routing(run.routing_records, complete and status == "PASS")
    summary = {"Purpose": "Normal-length new-to-routing early-exit feasibility, no quality trial", "Environment": run.environment,
        "Input": {"spec": run.spec, "weights_sha256": WEIGHTS_SHA, "inputs_sha256": run.spec.get("inputs_sha256")},
        "Expected": {"calls": CALLS, "articles": ARTICLES, "tokens": LENGTH, "seeds": list(SEEDS), "threshold": 0.01},
        "Actual": {"calls_started": run.calls_started, "calls_completed": run.calls_completed, "groups_completed": run.groups_completed,
            "loader_attempts": run.loader_attempts, "loader_returns": run.loader_returns, "checks": run.check_counts,
            "preservation": run.preservation, "routing": routing, "error": error, "save_errors": run.save_errors},
        "Status": status, "complete_coverage": complete, "ended_utc": utc(), "elapsed_seconds": time.monotonic() - started,
        "quality": "NOT TESTED", "net_acceleration": "NOT TESTED", "training": "NOT TESTED", "formal_acceptance_ready": False}
    payload = (json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
    entries = {str(path.relative_to(run.out)).replace("\\", "/"): info(path) for path in sorted(run.out.rglob("*")) if path.is_file()}
    entries["public/completion.json"] = {"bytes": len(payload), "sha256": sha(payload)}
    save(run.out / "FULL_MANIFEST.json", {"entries": entries, "excluded": ["FULL_MANIFEST.json", "public/GIT_BUNDLE_MANIFEST.json"]})
    save(run.public / "GIT_BUNDLE_MANIFEST.json", {"entries": {k: v for k, v in entries.items() if k.startswith("public/")},
        "excluded": ["public/GIT_BUNDLE_MANIFEST.json"], "private_artifacts_remain_on_target": True})
    with (run.public / "completion.json").open("xb") as stream:
        stream.write(payload)
    print(json.dumps({"Status": status, "calls": run.calls_completed, "articles": run.groups_completed,
                      "early_exit_observed": routing["early_exit_observed"]}), flush=True)
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
    for name in ("repo", "upstream", "model_dir", "inputs_path", "data_manifest_path", "source_manifest_path"):
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
        run.routing_records = []
        save(run.public / "spec.json", spec)
        execute(run, smoke)
        status = "PASS"
    except BaseException as exc:
        status = getattr(exc, "status", "BLOCKED")
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
