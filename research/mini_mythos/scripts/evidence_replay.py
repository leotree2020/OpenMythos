#!/usr/bin/env python3
"""ACT-003: replay three ACT-002 GQA/MLA cases against archived evidence.

This is a deterministic re-execution of the SAME implementation, not an
independent scientific replication. Refuses source/environment drift unless
explicitly permitted. It never downloads data or uploads experiment results.
"""
import argparse
import importlib.metadata
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

from evidence_archive import (
    DEFAULT_ARCHIVE, sha256_file, verify_archive, package_version,
)
from common import atomic_json

CASES = {
    "gqa22": "results/act002_gqa_seed22.json",
    "mla22": "results/act002_mla_seed22.json",
    "mla44": "results/act002_mla_seed44.json",
}
HELDOUT_KEYS = (
    "original_weights_original_act",
    "original_weights_forced_act",
    "forced_weights_original_act",
    "forced_weights_forced_act",
    "total_deployed_delta",
    "direct_mechanism_same_original_weights_delta",
    "parameter_history_under_original_act_delta",
    "policy_parameter_interaction_delta",
)


def compare_case(archived, replayed, atol=1e-4, rtol=1e-4):
    """Compare identity, exact first-event steps, and heldout numeric values."""
    discrepancies = []
    for key in ("experiment", "seed", "steps", "lr", "device"):
        if archived.get(key) != replayed.get(key):
            discrepancies.append(f"{key}: {archived.get(key)!r} != {replayed.get(key)!r}")
    prior = archived.get("results", [])
    after = replayed.get("results", [])
    if len(prior) != 1 or len(after) != 1:
        return ["expected exactly one experiment result per ACT-002 case"]
    a, b = prior[0], after[0]
    for key in ("attention", "requested_depth"):
        if a.get(key) != b.get(key):
            discrepancies.append(f"{key}: {a.get(key)!r} != {b.get(key)!r}")
    if a.get("events") != b.get("events"):
        discrepancies.append(
            f"first-event mismatch: archived={a.get('events')} vs rerun={b.get('events')}"
        )
    original_heldout, new_heldout = a.get("heldout", {}), b.get("heldout", {})
    if original_heldout.get("heldout_batches") != new_heldout.get("heldout_batches"):
        discrepancies.append("heldout_batches mismatch")
    for key in HELDOUT_KEYS:
        x, y = original_heldout.get(key), new_heldout.get(key)
        if (not isinstance(x, (int, float)) or isinstance(x, bool)
                or not isinstance(y, (int, float)) or isinstance(y, bool)
                or not (math.isfinite(x) and math.isfinite(y))
                or not math.isclose(x, y, rel_tol=rtol, abs_tol=atol)):
            discrepancies.append(f"heldout {key}: archived={x!r}, rerun={y!r}")
    original_trace, replay_trace = a.get("train_trace", []), b.get("train_trace", [])
    if len(original_trace) != len(replay_trace):
        discrepancies.append(
            f"train_trace length: archived={len(original_trace)} vs rerun={len(replay_trace)}"
        )
    return discrepancies


def guard_environment(manifest, repo, *, allow_source_drift=False, allow_env_drift=False):
    snapshot = manifest.get("snapshot", {})
    if not isinstance(snapshot, dict):
        raise ValueError("Archive has no valid snapshot provenance")
    recorded = snapshot.get("source_sha256_at_pack_time", {})
    if not isinstance(recorded, dict) or not recorded:
        raise ValueError("Archive has no recorded source hashes")
    changed = []
    for name, expected in recorded.items():
        path = repo / name
        if (not path.is_file() or path.is_symlink()
                or sha256_file(path) != expected):
            changed.append(name)
    if changed and not allow_source_drift:
        raise ValueError(
            "Code differs from archive snapshot: " + ", ".join(changed)
            + "; refuse replay unless --allow-source-drift is explicitly selected"
        )
    environment = []
    if snapshot.get("python") != sys.version.split()[0]:
        environment.append("Python")
    if snapshot.get("torch_distribution") != package_version("torch"):
        environment.append("PyTorch")
    if environment and not allow_env_drift:
        raise ValueError(
            "Environment differs from archive snapshot: "
            + ", ".join(environment)
            + "; refuse replay unless --allow-env-drift is explicitly selected"
        )
    return changed, environment


def replay(archive_path, repo, cases, *, atol=1e-4, rtol=1e-4,
           allow_source_drift=False, allow_env_drift=False):
    repo = Path(repo).resolve()
    manifest = verify_archive(archive_path)
    changed, environment = guard_environment(
        manifest, repo, allow_source_drift=allow_source_drift,
        allow_env_drift=allow_env_drift
    )
    if manifest["completeness"] != "complete":
        raise ValueError("Refusing to replay a partial evidence archive")

    output = {
        "experiment": "ACT-003_evidence_replay",
        "archive_sha256": sha256_file(archive_path),
        "allow_source_drift": allow_source_drift,
        "allow_env_drift": allow_env_drift,
        "source_files_with_drift": changed,
        "environment_with_drift": environment,
        "absolute_tolerance": atol,
        "relative_tolerance": rtol,
        "cases": [],
    }
    with zipfile.ZipFile(archive_path) as z, tempfile.TemporaryDirectory() as temporary:
        for case in cases:
            name = CASES[case]
            archived = json.loads(z.read(name))
            if (archived.get("device") != "cpu" or archived.get("experiment")
                    != "ACT-002_same_weight_counterfactual"):
                raise ValueError(f"{name}: only the expected CPU ACT-002 run is supported")
            config = archived["results"]
            if len(config) != 1:
                raise ValueError(f"{name}: expected one result")
            config = config[0]
            attention = config["attention"]
            depth = config["requested_depth"]
            seed = archived["seed"]
            steps = archived["steps"]
            lr = archived["lr"]
            if (attention not in ("gqa", "mla") or not isinstance(depth, int)
                    or depth < 1 or depth > 8 or not isinstance(seed, int)
                    or not isinstance(steps, int) or steps < 1 or steps > 1000
                    or not isinstance(lr, (float, int)) or not 0 < lr < 1):
                raise ValueError(f"{name}: invalid replay settings")
            result_path = Path(temporary) / f"{case}.json"
            command = [
                sys.executable,
                str(repo / "research/mini_mythos/scripts/act_counterfactual.py"),
                "--repo", str(repo),
                "--device", "cpu",
                "--attentions", attention,
                "--depths", str(depth),
                "--seed", str(seed),
                "--steps", str(steps),
                "--lr", str(lr),
                "--out", str(result_path),
            ]
            completed = subprocess.run(
                command, cwd=repo, capture_output=True, text=True, check=False
            )
            if completed.returncode:
                output["cases"].append({
                    "case": case, "status": "ERROR",
                    "returncode": completed.returncode,
                    "stderr_tail": completed.stderr[-1500:],
                    "stdout_tail": completed.stdout[-1500:],
                })
                print(f"{case}: ERROR (exit {completed.returncode})", flush=True)
                continue
            replayed = json.loads(result_path.read_text(encoding="utf-8"))
            differences = compare_case(archived, replayed, atol=atol, rtol=rtol)
            status = "PASS" if not differences else "DIFF"
            output["cases"].append({
                "case": case, "status": status, "differences": differences,
                "replay_json_sha256": sha256_file(result_path),
                "archived_heldout_total_delta":
                    archived["results"][0]["heldout"]["total_deployed_delta"],
                "rerun_heldout_total_delta":
                    replayed["results"][0]["heldout"]["total_deployed_delta"],
            })
            print(
                f"{case}: {status} "
                f"(archived ΔLoss={output['cases'][-1]['archived_heldout_total_delta']:+.6f}, "
                f"replay ΔLoss={output['cases'][-1]['rerun_heldout_total_delta']:+.6f})",
                flush=True
            )
    output["all_passed"] = all(r["status"] == "PASS" for r in output["cases"])
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".")
    parser.add_argument("--archive", default=DEFAULT_ARCHIVE)
    parser.add_argument("--cases", nargs="+", choices=CASES, default=list(CASES))
    parser.add_argument("--out", default="research/mini_mythos/archives/act003_replay_summary.json")
    parser.add_argument("--atol", type=float, default=1e-4)
    parser.add_argument("--rtol", type=float, default=1e-4)
    parser.add_argument("--allow-source-drift", action="store_true")
    parser.add_argument("--allow-env-drift", action="store_true")
    args = parser.parse_args()
    if not (math.isfinite(args.atol) and math.isfinite(args.rtol)
            and args.atol >= 0 and args.rtol >= 0):
        parser.error("Tolerances must be finite nonnegative numbers")
    try:
        report = replay(
            args.archive, args.repo, args.cases,
            atol=args.atol, rtol=args.rtol,
            allow_source_drift=args.allow_source_drift,
            allow_env_drift=args.allow_env_drift
        )
        atomic_json(args.out, report)
    except (OSError, ValueError, RuntimeError, KeyError, zipfile.BadZipFile) as exc:
        parser.exit(1, f"FAIL: {exc}\n")
    print("Replay report:", args.out)
    if not report["all_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
