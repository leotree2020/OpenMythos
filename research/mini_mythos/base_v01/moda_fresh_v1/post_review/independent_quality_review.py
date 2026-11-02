"""Read-only, post-publication V7 quality reconciliation. Standard library only.

This recomputes aggregates from retained per-token NLL/prediction evidence and
the frozen targets. It does not reconstruct the 199 unavailable raw matrices.
No package from the experiment is imported and no file is written.
"""
from __future__ import annotations

import argparse
from collections import Counter
import gzip
import hashlib
import json
import math
from pathlib import Path
import platform
import re
import struct
import subprocess
import sys

PACKAGE = "research/mini_mythos/base_v01/moda_fresh_v1"
FREEZE = "6a87446f8a146f62cae30ae75f986d2b30d30f60"
INPUT_PIN = {"bytes": 32692, "sha256": "2b740275785c4920ff59bcf3b76b2a81cce24597e4f5de1f491b8ea3357890db"}
ARMS = (("fixed32", None), ("shared", 4101), ("depth", 4101), ("shared", 4202), ("depth", 4202))
SEEDS = (5101, 5202)
EXPECTED = {"model_loads": 1, "calls_started": 405, "calls_completed": 405,
            "bridge_calls": 5, "quality_rows": 200, "repeat_rows": 200,
            "train_steps": 0, "backward_calls": 0, "optimizer_steps": 0}
TOLERANCE = 1e-10
LIMIT = 64 * 1024**2


class ReviewFailure(Exception):
    pass


def require(ok, message):
    if not ok:
        raise ReviewFailure(message)


def pin(raw):
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, "Duplicate JSON key: " + key)
        result[key] = value
    return result


def reject_constant(value):
    raise ReviewFailure("Nonfinite JSON constant: " + value)


def decode(raw, compressed=False):
    if compressed:
        import io
        with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
            raw = stream.read(LIMIT + 1)
    require(len(raw) <= LIMIT, "JSON expansion bound exceeded")
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=reject_constant)


def read_bytes(path):
    path = Path(path)
    require(not path.is_symlink() and path.is_file(), "Required regular file unavailable: " + str(path))
    require(path.stat().st_size <= LIMIT, "Physical read bound exceeded: " + str(path))
    return path.read_bytes()


def git(repo, *arguments):
    return subprocess.check_output(["git", "-C", str(repo), *arguments], timeout=120)


def committed(repo, revision, relative):
    value = git(repo, "show", revision + ":" + PACKAGE + "/" + relative)
    require(len(value) <= LIMIT, "Committed evidence read bound exceeded")
    return value


def same(left, right, context):
    if isinstance(left, dict):
        require(isinstance(right, dict) and set(left) == set(right), context + ": keys")
        for key in left:
            same(left[key], right[key], context + "." + key)
    elif isinstance(left, list):
        require(isinstance(right, list) and len(left) == len(right), context + ": length")
        for number, (a, b) in enumerate(zip(left, right)):
            same(a, b, context + "[%d]" % number)
    elif type(left) is float:
        require(type(right) in (int, float) and math.isfinite(left) and math.isfinite(right)
                and abs(left - right) <= TOLERANCE, context + ": numeric mismatch")
    else:
        require(type(left) is type(right) and left == right, context + ": exact mismatch")


def model_name(arm, seed):
    return arm if seed is None else arm + "_" + str(seed)


def interpretation(nll, accuracy):
    if nll <= -0.01 and accuracy >= -0.01:
        return "IMPROVEMENT"
    if nll >= 0.01 or accuracy < -0.01:
        return "WORSE"
    return "NO_QUALIFIED_IMPROVEMENT"


def reconstruct(rows, data):
    require(len(rows) == 200, "Exactly 200 first-pass quality rows")
    samples = data["eval"]
    require(len(samples) == 20 and len({s["id"] for s in samples}) == 20, "Twenty unique frozen articles")
    require(Counter(s["label"] for s in samples) == Counter({0: 5, 1: 5, 2: 5, 3: 5}), "Five texts per source label")
    require(data["context_tokens"] == 128 and data["scored_positions"] == [64, 128]
            and data["eval_seeds"] == list(SEEDS), "Original scoring contract")
    for sample in samples:
        require(len(sample["tokens"]) == 129 and all(type(x) is int and 0 <= x < 32768 for x in sample["tokens"]), "129 valid IDs")
    reconstructed = {}
    for index, row in enumerate(rows):
        case, slot = divmod(index, 5)
        article_index, eval_offset = divmod(case, 2)
        arm_index = (case + slot) % 5
        arm, train_seed = ARMS[arm_index]
        expected = {"call_index": index, "pass_index": 0, "case": case, "slot": slot,
                    "article_index": article_index, "eval_seed": SEEDS[eval_offset],
                    "arm_index": arm_index, "arm": arm, "train_seed": train_seed}
        require(all(row.get(k) == value for k, value in expected.items()), "First-pass schedule row %d" % index)
        sample = samples[article_index]
        require(row["article_id"] == sample["id"], "Article identity row %d" % index)
        targets = sample["tokens"][65:129]
        require(row["targets_sha256"] == hashlib.sha256(struct.pack("<64q", *targets)).hexdigest(), "Targets binding row %d" % index)
        require(row["shape"] == [64, 32768] and row["dtype"] == "float32-le", "Matrix layout row %d" % index)
        require(re.fullmatch(r"[0-9a-f]{64}", row["logits_sha256"]) is not None, "Logits digest row %d" % index)
        nll = row["worker_per_token"]["nll"]
        predictions = row["worker_per_token"]["predictions"]
        require(len(nll) == len(predictions) == 64, "64 retained token observations")
        require(all(type(x) in (int, float) and math.isfinite(x) and x >= 0 for x in nll), "Finite nonnegative token NLL")
        require(all(type(x) is int and 0 <= x < 32768 for x in predictions), "Valid predicted IDs")
        total = math.fsum(nll)
        correct = sum(a == b for a, b in zip(predictions, targets))
        metrics = {"nll_sum": total, "nll_mean": total / 64, "correct": correct, "target_count": 64}
        for key, value in metrics.items():
            same(value, row[key], "Row%d.%s" % (index, key))
        key = (arm, train_seed, SEEDS[eval_offset], sample["id"])
        require(key not in reconstructed, "Duplicate quality row identity")
        reconstructed[key] = metrics
    require(len(reconstructed) == 200, "Full quality identity grid")
    article_ids = sorted(s["id"] for s in samples)
    means = {}
    for arm, seed in ARMS:
        group = [reconstructed[(arm, seed, h0, article)] for article in article_ids for h0 in SEEDS]
        total_correct = sum(r["correct"] for r in group)
        means[model_name(arm, seed)] = {"mean_nll": math.fsum(r["nll_sum"] for r in group) / 2560,
            "correct": total_correct, "scored_observations": 2560, "accuracy": total_correct / 2560}
    comparisons, screens, interpretations = {}, {}, {}
    for left, right in (("depth", "fixed32"), ("depth", "shared"), ("shared", "fixed32")):
        title = left + "_vs_" + right
        labels = {}
        for seed in (4101, 4202):
            reference_seed = None if right == "fixed32" else seed
            per_article = []
            for article in article_ids:
                left_rows = [reconstructed[left, seed, h0, article] for h0 in SEEDS]
                right_rows = [reconstructed[right, reference_seed, h0, article] for h0 in SEEDS]
                per_article.append({"article_id": article,
                    "delta_nll": math.fsum(a["nll_sum"] - b["nll_sum"] for a, b in zip(left_rows, right_rows)) / 128,
                    "delta_correct": sum(a["correct"] - b["correct"] for a, b in zip(left_rows, right_rows))})
            dn = math.fsum(r["delta_nll"] for r in per_article) / 20
            da = sum(r["delta_correct"] for r in per_article) / 2560
            labels[str(seed)] = interpretation(dn, da)
            comparisons[title + "_" + str(seed)] = {"delta_nll": dn, "delta_accuracy": da,
                "per_article": per_article, "articles_improved": sum(r["delta_nll"] < 0 for r in per_article),
                "worst_article_delta_nll": max(r["delta_nll"] for r in per_article),
                "screen": dn <= -0.01 and da >= -0.01, "interpretation": labels[str(seed)]}
        screens[title] = "PASS" if all(comparisons[title + "_" + str(s)]["screen"] for s in (4101, 4202)) else "FAIL"
        interpretations[title] = {"per_seed": labels, "combined": labels["4101"] if labels["4101"] == labels["4202"] else "MIXED"}
    return {"means": means, "comparisons": comparisons, "scientific_screens": screens,
            "result_interpretations": interpretations}


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--repo-root", required=True, type=Path)
    cli.add_argument("--run-dir", required=True, type=Path)
    cli.add_argument("--inputs", required=True, type=Path)
    cli.add_argument("--publication-sha", required=True)
    args = cli.parse_args()
    report = {"Purpose": "Independent post-publication reconciliation of retained V7 token-quality evidence",
        "Environment": {"python": platform.python_version(), "stdlib_only": True},
        "Input": {"publication_sha": args.publication_sha, "execution_freeze": FREEZE},
        "Expected": {"quality_rows": 200, "scored_observations_per_model": 2560, "new_model_calls": 0},
        "Actual": {}, "Status": "NOT TESTED", "checks": [],
        "limitations": ["Reconciles retained per-token NLL/predictions and frozen targets; does not recompute absent raw logits.",
            "Repeat-pass quality is never scored twice. Two h0 evaluations do not create independent source texts.",
            "Scientific screen FAIL is a valid result; it does not make reconciliation FAIL."]}
    try:
        require(bool(sys.flags.isolated) and sys.dont_write_bytecode, "Run with Python -I -B")
        require(all(p.is_absolute() for p in (args.repo_root, args.run_dir, args.inputs)), "Absolute paths required")
        require(re.fullmatch(r"[0-9a-f]{40}", args.publication_sha) is not None, "Full publication commit required")
        require(git(args.repo_root, "merge-base", FREEZE, args.publication_sha).decode().strip() == FREEZE, "Publication descends from frozen execution")
        manifest_raw = committed(args.repo_root, args.publication_sha, "MODEL_V7_EXTERNAL_EVIDENCE_MANIFEST.json")
        manifest = decode(manifest_raw)
        report["Input"]["committed_external_manifest"] = pin(manifest_raw)

        def evidence(relative):
            path = args.run_dir / relative
            raw = read_bytes(path)
            require(manifest.get(str(path)) == pin(raw), "Published external pin mismatch: " + relative)
            published = committed(args.repo_root, args.publication_sha, "evidence_v7/" + relative)
            require(published == raw, "Public/external bytes mismatch: " + relative)
            return decode(raw, relative.endswith(".gz"))

        summary = evidence("summary.json")
        completion = evidence("worker/public/completion.json")
        require(summary["Status"] == "PASS" and summary["Actual"]["custody"]["Status"] == "PASS"
                and summary["Actual"]["protection_complete"] is True, "Published operator and custody PASS")
        require(completion["Status"] == "PASS" and completion["preservation"] == "PASS"
                and completion["Actual"] == EXPECTED, "Complete 405-call zero-training worker PASS")
        require(completion["Input"]["freeze"] == FREEZE and completion["Input"]["data_sha256"] == INPUT_PIN["sha256"], "Execution/data bridge")
        report["checks"].append("Published PASS, exact execution, custody and frozen data binding")
        input_raw = read_bytes(args.inputs)
        require(pin(input_raw) == INPUT_PIN, "Original prepared input bytes")
        data = decode(input_raw)
        rows = evidence("worker/public/evaluation.json.gz")["rows"]
        saved = evidence("worker/public/results.json")
        audited = evidence("audit.json.gz")
        require(audited["Status"] == "PASS" and audited["check_counts"]["FAIL"] == 0, "Published independent final audit PASS")
        computed = reconstruct(rows, data)
        for key, value in computed.items():
            same(value, saved[key], "Worker summary." + key)
            same(value, audited["Actual"][key], "Independent audit summary." + key)
        report["checks"].append("All200 first-pass identities, target digests, 64-token metrics and 2560-denominator means")
        report["checks"].append("All6 paired seed contrasts and3 both-seed screens independently reconciled")
        report["Actual"] = {"quality_rows": len(rows), "unique_articles": 20, "token_observations_per_model": 2560,
            "repeat_rows_added_to_quality": 0, "new_model_calls": 0, "input_pin": pin(input_raw), **computed}
        report["Status"] = "PASS"
    except BaseException as exc:
        report["Status"] = "BLOCKED" if isinstance(exc, (OSError, subprocess.SubprocessError, KeyboardInterrupt, MemoryError)) else "FAIL"
        report["error"] = {"type": type(exc).__name__, "message": str(exc)}
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, allow_nan=False))
    return 0 if report["Status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
