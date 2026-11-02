"""Independent, read-only post-publication V7 timing/custody review (stdlib).

Prints one JSON report. No model/project imports, writes, git mutations or network.
Recorded whole-custody assertions are checked; old target files are not rehashed.
"""
from __future__ import annotations
import argparse
import collections
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
import subprocess
import sys
import zlib

FREEZE = "6a87446f8a146f62cae30ae75f986d2b30d30f60"
RUN = "/workspaces/mythos-evidence/base_v01/moda_fresh/attempt-v7"
PACKAGE = "research/mini_mythos/base_v01/moda_fresh_v1"
ARMS = (("fixed32", None), ("shared", 4101), ("depth", 4101), ("shared", 4202), ("depth", 4202))
EXPECTED = dict(model_loads=1, calls_started=405, calls_completed=405, bridge_calls=5,
                quality_rows=200, repeat_rows=200, train_steps=0, backward_calls=0, optimizer_steps=0)
REQUIRED = (
    "summary.json", "custody.json", "closed_storage_outputs_before.json", "closed_storage_outputs_after.json",
    "protected_scope.json", "protected_before.json.gz", "protected_before_receipt.json",
    "artifact_budget_after.json", "publication_quiescence.json", "audit.json.gz",
    "worker/public/completion.json", "worker/public/checks.jsonl.gz", "worker/public/evaluation.json.gz",
    "worker/public/timing.json.gz", "worker/public/results.json", "worker/public/oldbridges.json",
    "worker/public/base_state_before.json", "worker/public/base_state_after.json",
    "worker/public/adapters_before.json", "worker/public/adapters_after.json", "worker/public/sentinel.json")

def unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value: raise ValueError("Duplicate JSON key: " + key)
        value[key] = item
    return value

def loads(raw):
    return json.loads(raw, object_pairs_hook=unique_object,
        parse_constant=lambda x: (_ for _ in ()).throw(ValueError("Nonfinite JSON: " + x)))

def pin(raw):
    return dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())

def raw_read(path, limit=32 * 1024**2):
    if path.is_symlink() or not path.is_file(): raise ValueError("Regular file required: " + str(path))
    with path.open("rb") as stream: raw = stream.read(limit + 1)
    if len(raw) > limit: raise ValueError("Read bound exceeded: " + str(path))
    return raw

def decoded(path):
    raw = raw_read(path)
    if path.name.endswith(".gz"):
        inflater = zlib.decompressobj(31)
        raw = inflater.decompress(raw, 32 * 1024**2 + 1)
        if len(raw) > 32 * 1024**2 or not inflater.eof or inflater.unused_data or inflater.unconsumed_tail:
            raise ValueError("Bounded single gzip stream required: " + str(path))
    return raw

def read(path): return loads(decoded(path))
def model_name(arm, seed): return arm if seed is None else arm + "_" + str(seed)
def row_key(row): return row["arm"], row["train_seed"], row["article_id"], row["eval_seed"]
def stable(observer): return {key: observer[key] for key in ("h0_sha256", "rng_before_sha256", "rng_after_sha256", "seed")}
def equal_nested(a, b):
    if type(a) is dict: return type(b) is dict and set(a) == set(b) and all(equal_nested(v, b[k]) for k, v in a.items())
    if type(a) is list: return type(b) is list and len(a) == len(b) and all(equal_nested(x, y) for x, y in zip(a, b))
    if type(a) is float: return type(b) in (int, float) and math.isfinite(a) and math.isfinite(b) and abs(a - b) <= 1e-10
    return type(a) is type(b) and a == b

def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--run-dir", type=Path, required=True)
    cli.add_argument("--repo-root", type=Path, required=True)
    cli.add_argument("--publication-sha", required=True)
    args = cli.parse_args()
    report = dict(Purpose="Independent V7 post-publication timing and recorded custody review",
        Environment=dict(python=sys.version, stdlib_only=True, model_imports=False),
        Input=dict(run_dir=str(args.run_dir), repo_root=str(args.repo_root), publication_sha=args.publication_sha, execution_freeze=FREEZE),
        Expected=dict(counts=EXPECTED, timed_rows=400, old_files_rehashed_by_this_review=0),
        Actual={}, checks=[], Status="NOT TESTED")
    def check(label, condition, actual=None):
        report["checks"].append(dict(Purpose=label, Expected=True, Actual=actual, Status="PASS" if condition else "FAIL"))
        if not condition: raise ValueError(label)
    try:
        check("Full publication SHA", re.fullmatch("[0-9a-f]{40}", args.publication_sha) is not None)
        check("Absolute paths", args.run_dir.is_absolute() and args.repo_root.is_absolute())
        run = args.run_dir; package = args.repo_root / PACKAGE
        def git(*argv): return subprocess.check_output(["git", "-C", str(args.repo_root), *argv], timeout=120).decode().strip()
        check("Published local HEAD", git("rev-parse", "HEAD") == args.publication_sha)
        check("Clean published tree", git("status", "--porcelain=v1", "--untracked-files=all") == "")
        check("Execution freeze is publication ancestor", git("merge-base", FREEZE, args.publication_sha) == FREEZE)
        for name in ("execute_once_v7.py", "measure_storage_v7.py", "run_fresh.py", "audit_stream.py", "storage_codec.py"):
            original = subprocess.check_output(["git", "-C", str(args.repo_root), "show", FREEZE + ":" + PACKAGE + "/" + name], timeout=120)
            check("Actual frozen source unchanged " + name, raw_read(package / name) == original)
        external = read(package / "MODEL_V7_EXTERNAL_EVIDENCE_MANIFEST.json")
        exported = read(package / "MODEL_V7_PUBLIC_EXPORT.json")
        for rel in REQUIRED:
            actual = pin(raw_read(run / rel)); key = RUN + "/" + rel
            check("Bound external evidence " + rel, external.get(key) == actual)
            check("Exact published copy " + rel, rel in exported["files"] and pin(raw_read(package / "evidence_v7" / rel)) == actual)
        summary = read(run / "summary.json"); completion = read(run / "worker/public/completion.json")
        check("Successful operator and worker", summary["Status"] == completion["Status"] == "PASS" and completion["preservation"] == "PASS")
        check("Exact 405/200/200 and zero training counts", completion["Actual"] == EXPECTED and summary["Actual"]["completion"] == completion, completion["Actual"])
        check("Exact frozen execution binding", summary["Input"]["execution_freeze"] == completion["Input"]["freeze"] == FREEZE)
        logs = [loads(line) for line in decoded(run / "worker/public/checks.jsonl.gz").splitlines() if line]
        check("Worker check count reconciliation", all(row["Status"] == "PASS" for row in logs) and completion["checks"] == dict(PASS=len(logs), FAIL=0, BLOCKED=0), completion["checks"])
        audit = read(run / "audit.json.gz")
        check("Recorded final audit reconciled", audit["Status"] == "PASS" and all(row["Status"] == "PASS" for row in audit["checks"]) and audit["check_counts"] == dict(PASS=len(audit["checks"]), FAIL=0))
        rows = read(run / "worker/public/evaluation.json.gz")["rows"]
        timings = read(run / "worker/public/timing.json.gz")["rows"]
        quality = {row_key(row): row for row in rows}
        check("200 unique quality rows and 400 timed calls", len(rows) == len(quality) == 200 and len(timings) == 400)
        article_ids = {row["article_index"]: row["article_id"] for row in rows}
        check("Exactly 20 unique articles", set(article_ids) == set(range(20)) and len(set(article_ids.values())) == 20)
        balance = collections.Counter(); paired = {}; repeat_count = 0
        for index, row in enumerate(timings):
            pass_index, within = divmod(index, 200); case, slot = divmod(within, 5)
            arm_index = (case + (slot if pass_index == 0 else 4 - slot)) % 5
            arm, train_seed = ARMS[arm_index]
            planned = dict(call_index=index, pass_index=pass_index, case=case, article_index=case // 2,
                eval_seed=(5101, 5202)[case % 2], slot=slot, arm_index=arm_index, arm=arm, train_seed=train_seed)
            if any(row[key] != value for key, value in planned.items()): raise ValueError("Frozen timing order at " + str(index))
            if row["article_id"] != article_ids[case // 2]: raise ValueError("Timing article mismatch")
            if any(type(row[key]) is not int or row[key] <= 0 for key in ("endpoint_wall_ns", "endpoint_cpu_ns")): raise ValueError("Invalid duration")
            reference = quality[row_key(row)]
            if row["logits_sha256"] != reference["logits_sha256"] or row["observer"] != reference["observer"]: raise ValueError("Repeat/quality SHA or observer mismatch")
            if pass_index == 0 and any(reference[key] != value for key, value in planned.items()): raise ValueError("Quality order mismatch")
            state = stable(row["observer"]); pair = case // 2, row["eval_seed"]
            if state["seed"] != pair[1]: raise ValueError("Wrong actual seed")
            paired.setdefault(pair, state)
            if paired[pair] != state: raise ValueError("Unpaired actual h0/RNG")
            repeat_count += pass_index; balance[pass_index, arm_index, slot] += 1
        check("200 exact SHA/observer repeats; paired and balanced 400 calls", repeat_count == 200 and len(balance) == 50 and set(balance.values()) == {8})
        models = {}; extended = {}
        for arm, seed in ARMS:
            group = [row for row in timings if (row["arm"], row["train_seed"]) == (arm, seed)]
            check("80 timings " + model_name(arm, seed), len(group) == 80)
            ns = sorted(row["endpoint_wall_ns"] for row in group)
            models[model_name(arm, seed)] = dict(calls=80, endpoint_total_seconds=sum(ns) / 1e9,
                endpoint_median_seconds=statistics.median(ns) / 1e9,
                endpoint_p95_seconds=ns[math.ceil(.95 * len(ns)) - 1] / 1e9,
                process_cpu_total_seconds=sum(row["endpoint_cpu_ns"] for row in group) / 1e9,
                per_pass_seconds={str(p): sum(row["endpoint_wall_ns"] for row in group if row["pass_index"] == p) / 1e9 for p in (0, 1)})
            extended[model_name(arm, seed)] = dict(endpoint_mean_seconds=statistics.mean(ns) / 1e9,
                endpoint_min_seconds=min(ns) / 1e9, endpoint_max_seconds=max(ns) / 1e9)
        ratios = {}; per_pass = {}; per_article = []
        for seed in (4101, 4202):
            h = "depth_" + str(seed)
            for reference in ("fixed32", "shared_" + str(seed)):
                title = h + "_vs_" + reference
                ratios[title] = models[h]["endpoint_total_seconds"] / models[reference]["endpoint_total_seconds"]
                per_pass[title] = {str(p): models[h]["per_pass_seconds"][str(p)] / models[reference]["per_pass_seconds"][str(p)] for p in (0, 1)}
                for article in sorted(article_ids.values()):
                    left = [r["endpoint_wall_ns"] for r in timings if r["article_id"] == article and model_name(r["arm"], r["train_seed"]) == h]
                    right = [r["endpoint_wall_ns"] for r in timings if r["article_id"] == article and model_name(r["arm"], r["train_seed"]) == reference]
                    if len(left) != 4 or len(right) != 4: raise ValueError("Four timing observations per article/model required")
                    per_article.append(dict(comparison=title, article_id=article, history_mean_seconds=sum(left) / 4e9,
                        reference_mean_seconds=sum(right) / 4e9, ratio=sum(left) / sum(right)))
        timing = dict(models=models, ratios=ratios, per_pass_ratios=per_pass, paired_per_article=per_article)
        saved = read(run / "worker/public/results.json")
        check("Independently recomputed timing summaries", all(equal_nested(value, saved["timing"][key]) and equal_nested(value, audit["Actual"]["timing"][key]) for key, value in timing.items()))
        report["Actual"]["timing"] = timing; report["Actual"]["additional_descriptive_timing"] = extended
        report["Actual"]["whole_worker_seconds"] = completion["seconds"]
        report["Actual"]["separate_costs"] = {k: completion[k] for k in ("load_seconds", "adapter_load_seconds", "audit_seconds", "serialization_seconds", "peak_rss_bytes")}
        bridges = read(run / "worker/public/oldbridges.json")
        check("Five recorded successful historical bridges", bridges["Status"] == "PASS" and [(r["arm"], r["train_seed"]) for r in bridges["rows"]] == list(ARMS) and all(r["Status"] == "PASS" for r in bridges["rows"]))
        base_before = read(run / "worker/public/base_state_before.json"); base_after = read(run / "worker/public/base_state_after.json")
        adapters_before = read(run / "worker/public/adapters_before.json"); adapters_after = read(run / "worker/public/adapters_after.json")
        check("Recorded 63 base states and four adapters unchanged", len(base_before) == 63 and base_before == base_after and len(adapters_before) == 4 and adapters_before == adapters_after)
        sentinel = read(run / "worker/public/sentinel.json"); final = timings[-1]
        check("Predeclared final sentinel", final["call_index"] == 399 and final["article_index"] == 19 and final["eval_seed"] == 5202 and final["arm"] == "depth" and final["train_seed"] == 4202 and sentinel["path"] == "private/final_sentinel.bin")
        check("Retained full sentinel bytes", pin(raw_read(run / "worker/private/final_sentinel.bin")) == sentinel["raw"] == dict(bytes=8 * 1024**2, sha256=final["logits_sha256"]))
        check("Honest raw evidence coverage", audit["Actual"]["live_full_audited_rows"] == 200 and audit["Actual"]["retrospective_full_rows_recomputed"] == 1 and audit["Actual"]["retrospective_full_rows_unavailable"] == 199)
        custody = read(run / "custody.json")
        fields = ("changed_files", "unreadable_files", "changed_git", "changed_environments", "active_workers", "cleanup_problems")
        check("Recorded complete custody clean", custody["Status"] == "PASS" and all(custody[key] == [] for key in fields) and summary["Actual"]["protection_complete"] is True and summary["Actual"]["custody"] == custody)
        oldout = read(run / "closed_storage_outputs_before.json"); newout = read(run / "closed_storage_outputs_after.json")
        expected_outputs = {"/workspaces/mythos-evidence/base_v01/moda_fresh/preparation-v6/MODEL_STORAGE_PREFLIGHT_V7.json", "/workspaces/mythos-moda-storage-v7.log"}
        check("Two closed outputs recorded unchanged", oldout == newout and set(oldout["outputs"]) == expected_outputs and oldout["total_bytes"] == sum(value["bytes"] for value in oldout["outputs"].values()))
        check("Closed output current bytes", all(pin(raw_read(Path(path))) == value for path, value in oldout["outputs"].items()) and pin(raw_read(package / "MODEL_STORAGE_OUTPUTS_V7.json")) == oldout["manifest_pin"])
        receipt = read(run / "protected_before_receipt.json"); compressed = raw_read(run / "protected_before.json.gz"); uncompressed = decoded(run / "protected_before.json.gz"); mapping = loads(uncompressed)
        canonical = (json.dumps(mapping, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n").encode()
        scope = read(run / "protected_scope.json")
        check("Complete lossless protected map receipt", len(compressed) <= 2 * 1024**2 and pin(compressed) == receipt["compressed"] and pin(uncompressed) == receipt["canonical"] and canonical == uncompressed and len(mapping) == receipt["record_count"] == scope["current_count"])
        check("Recorded previous scope retained", scope["original_v1_count"] == 25367 and scope["original_count"] == 25436 and scope["all_original_paths_and_pins_preserved"] is True and len(mapping) >= 32603)
        check("Current outputs absent from old map", not (set(mapping) & expected_outputs))
        never_started = (Path("/workspaces/mythos-moda-fresh-preparation-v5.log"), Path("/workspaces/mythos-evidence/base_v01/moda_fresh/preparation-v5"))
        check("Never-started V5 remains absent", all(not path.exists() and not path.is_symlink() for path in never_started))
        budget = read(run / "artifact_budget_after.json")
        check("Actual accounting and frozen budgets", budget["raw_bytes"] == 8 * 1024**2 and budget["closed_storage_output_bytes"] == oldout["total_bytes"] and budget["projected_total_nonraw_bytes"] == budget["run_bytes"] - budget["raw_bytes"] + budget["public_copy_bytes"] + budget["closed_storage_output_bytes"] + budget["git_finalization_allowance"] <= 12 * 1024**2 and budget["free_bytes"] - budget["public_copy_bytes"] - budget["git_finalization_allowance"] >= 256 * 1024**2)
        publication = read(run / "publication.json")
        check("Recorded publication complete", publication["Status"] == "PASS" and publication["head"] == publication["remote"] == args.publication_sha)
        close_budget = publication["postclosure_budget"]
        check("Postclosure budget and reserve", close_budget["projected_total_nonraw_bytes"] <= 12 * 1024**2 and close_budget["free_bytes"] - close_budget["public_copy_bytes"] - close_budget["git_finalization_allowance"] >= 256 * 1024**2)
        quiescent = read(run / "publication_quiescence.json")
        check("Recorded worker quiescence", quiescent["Status"] == "PASS" and quiescent["active_workers"] == [])
        check("Scientific screens kept separate from engineering", saved["scientific_screens"] == audit["Actual"]["scientific_screens"] == summary["scientific_screens"] and all(x in ("PASS", "FAIL") for x in saved["scientific_screens"].values()))
        report["Actual"].update(counts=completion["Actual"], protected_paths=len(mapping), repeated_rows=repeat_count,
            recorded_scientific_screens=saved["scientific_screens"], postclosure_budget=close_budget,
            old_files_rehashed_by_this_review=0, source_retokenizations=0, model_calls=0,
            limitations=["Old-byte custody is a verified pinned operator record, not a second full target-file hash pass.",
                "Two current storage outputs and the one retained raw sentinel are directly rehashed here.",
                "No 199 unavailable raw matrices, model evaluation, full-history retokenization or quality-screen recomputation here.",
                "20 texts and two h0 seeds; timing repeats do not enlarge the independent quality sample.",
                "Instrumented pretokenized CPU endpoint excludes serialization/audit/I/O; whole-worker time reported separately.",
                "Base-pretraining overlap unknown; no statistical confirmation, equal-compute claim or broad generalization."])
        report["Status"] = "PASS"
    except Exception as exc:
        report["Status"] = "BLOCKED" if isinstance(exc, (OSError, subprocess.SubprocessError)) else "FAIL"
        report["error"] = dict(type=type(exc).__name__, message=str(exc))
    report["check_counts"] = {state: sum(row["Status"] == state for row in report["checks"]) for state in ("PASS", "FAIL")}
    print(json.dumps(report, sort_keys=True, ensure_ascii=False, allow_nan=False))
    return 0 if report["Status"] == "PASS" else 2

if __name__ == "__main__": raise SystemExit(main())
