#!/usr/bin/env python3
"""Independent post-result arithmetic review; reads rows.jsonl only, never a model.

Usage: python -I -B independent_summary.py --rows RUN/rows.jsonl --output NEW.json
This file does not import the formal auditor, runner, NumPy, Torch or tokenizers.
"""

import argparse
import datetime
import hashlib
import json
import math
from pathlib import Path
import random
import sys


DEPTHS = (2, 4, 8)
ARTICLE_COUNT = 32
REPLICA_COUNT = 3
TOKEN_COUNT = 192
BOOTSTRAP_COUNT = 10000
BOOTSTRAP_SEED = 20261101
TOLERANCE = 1e-10


def strict_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key: " + str(key))
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError("non-finite JSON literal: " + value)


def finite_number(value):
    return type(value) in (int, float) and math.isfinite(value)


def digest(value):
    return (isinstance(value, str) and len(value) == 64
            and all(c in "0123456789abcdef" for c in value))


def inspect_rows(path):
    errors, blockers, rows = [], [], {}
    actual = {"scientific_results": None}
    raw = path.read_bytes()
    binding = {"path": str(path), "bytes": len(raw),
               "sha256": hashlib.sha256(raw).hexdigest()}
    lines = raw.splitlines()
    for line_number, line in enumerate(lines, 1):
        try:
            row = json.loads(line, object_pairs_hook=strict_object,
                             parse_constant=reject_constant)
        except (ValueError, UnicodeError) as exc:
            errors.append({"line": line_number, "issue": "invalid JSON", "detail": str(exc)})
            continue
        if not isinstance(row, dict):
            errors.append({"line": line_number, "issue": "row is not an object"})
            continue
        a, r, d = (row.get(k) for k in ("article_index", "replica", "depth"))
        if not (type(a) is int and 0 <= a < ARTICLE_COUNT
                and type(r) is int and 0 <= r < REPLICA_COUNT
                and type(d) is int and d in DEPTHS):
            errors.append({"line": line_number, "issue": "invalid row identity"})
            continue
        key = (a, r, d)
        if key in rows:
            errors.append({"line": line_number, "issue": "duplicate row", "key": list(key)})
            continue
        rows[key] = row
        for field in ("h0_sha256", "rng_before_sha256", "rng_after_sha256", "article_id"):
            if not digest(row.get(field)):
                errors.append({"line": line_number, "issue": "invalid digest", "field": field})
        valid_arrays = True
        for field in ("nll", "logsumexp", "target_logits"):
            values = row.get(field)
            if not (isinstance(values, list) and len(values) == TOKEN_COUNT
                    and all(finite_number(v) for v in values)):
                errors.append({"line": line_number, "issue": "invalid scored array", "field": field})
                valid_arrays = False
        if not valid_arrays:
            continue
        residual = max(abs(n - (s - t)) for n, s, t in
                       zip(row["nll"], row["logsumexp"], row["target_logits"]))
        mean = math.fsum(row["nll"]) / TOKEN_COUNT
        if residual > TOLERANCE:
            errors.append({"line": line_number, "issue": "saved NLL arithmetic mismatch",
                           "max_abs_residual": residual})
        if not finite_number(row.get("mean_nll")) or abs(row["mean_nll"] - mean) > TOLERANCE:
            errors.append({"line": line_number, "issue": "saved row mean mismatch"})
        row["independent_mean"] = mean
        row["independent_residual"] = residual

    expected = {(a, r, d) for a in range(ARTICLE_COUNT)
                for r in range(REPLICA_COUNT) for d in DEPTHS}
    missing = sorted(expected - set(rows))
    if missing:
        blockers.append({"issue": "incomplete formal row coverage", "missing": [list(k) for k in missing]})
    if len(lines) > len(expected):
        errors.append({"issue": "too many rows", "actual": len(lines), "expected": len(expected)})

    h0_groups, rng_groups, complete_groups, distinct_h0 = [], [], 0, set()
    for a in range(ARTICLE_COUNT):
        article_ids = {rows[(a, r, d)].get("article_id")
                       for r in range(REPLICA_COUNT) for d in DEPTHS if (a, r, d) in rows}
        if len(article_ids) > 1:
            errors.append({"issue": "article ID differs within index", "article_index": a})
        for r in range(REPLICA_COUNT):
            triple = [rows.get((a, r, d)) for d in DEPTHS]
            if any(row is None for row in triple):
                continue
            complete_groups += 1
            h0 = [row.get("h0_sha256") for row in triple]
            if all(digest(v) for v in h0) and len(set(h0)) == 1:
                h0_groups.append([a, r])
                distinct_h0.add(h0[0])
            else:
                errors.append({"issue": "h0 pairing mismatch", "article_index": a, "replica": r})
            rng_ok = all(len({row.get(field) for row in triple}) == 1
                         and all(digest(row.get(field)) for row in triple)
                         for field in ("rng_before_sha256", "rng_after_sha256"))
            if rng_ok:
                rng_groups.append([a, r])
            else:
                errors.append({"issue": "RNG pairing mismatch", "article_index": a, "replica": r})

    actual.update({"line_count": len(lines), "unique_rows": len(rows),
                   "complete_article_replica_triples": complete_groups,
                   "h0_matched_triples": len(h0_groups), "rng_matched_triples": len(rng_groups),
                   "distinct_h0_digests_across_matched_triples": len(distinct_h0),
                   "h0_distinct_count_is_descriptive_not_an_acceptance_threshold": True,
                   "max_saved_nll_identity_residual": max(
                       (r["independent_residual"] for r in rows.values() if "independent_residual" in r),
                       default=None)})
    if errors or blockers:
        return binding, actual, errors, blockers

    article_means = {d: [math.fsum(rows[(a, r, d)]["independent_mean"]
                                 for r in range(REPLICA_COUNT)) / REPLICA_COUNT
                         for a in range(ARTICLE_COUNT)] for d in DEPTHS}
    differences = {"primary_d4_minus_d8": [article_means[4][a] - article_means[8][a]
                                          for a in range(ARTICLE_COUNT)],
                   "secondary_d2_minus_d8": [article_means[2][a] - article_means[8][a]
                                            for a in range(ARTICLE_COUNT)]}
    distributions = {name: [] for name in differences}
    random_source = random.Random(BOOTSTRAP_SEED)
    for _ in range(BOOTSTRAP_COUNT):
        indices = [random_source.randrange(ARTICLE_COUNT) for _ in range(ARTICLE_COUNT)]
        for name, effects in differences.items():
            distributions[name].append(math.fsum(effects[i] for i in indices) / ARTICLE_COUNT)
    lower = math.ceil(0.025 * BOOTSTRAP_COUNT) - 1
    upper = math.ceil(0.975 * BOOTSTRAP_COUNT) - 1
    result = {"analysis_unit": "article; first average the three initial-state replicas",
              "nll_unit": "nats per scored next token", "per_depth": {}, "paired_contrasts": {},
              "article_means": [{"article_index": a,
                                 "article_id": rows[(a, 0, 2)]["article_id"],
                                 "mean_nll_by_depth": {str(d): article_means[d][a] for d in DEPTHS}}
                                for a in range(ARTICLE_COUNT)],
              "bootstrap": {"count": BOOTSTRAP_COUNT, "seed": BOOTSTRAP_SEED,
                            "same_article_indices_for_both_contrasts": True,
                            "nearest_rank_sorted_indices": [lower, upper]}}
    for d in DEPTHS:
        value = math.fsum(article_means[d]) / ARTICLE_COUNT
        overflow = value > math.log(sys.float_info.max)
        result["per_depth"][str(d)] = {"mean_nll": value,
                                       "ppl": None if overflow else math.exp(value),
                                       "ppl_overflow": overflow}
    for name, effects in differences.items():
        ordered = sorted(distributions[name])
        shallow = 4 if name.startswith("primary") else 2
        result["paired_contrasts"][name] = {
            "mean_delta_nll": math.fsum(effects) / ARTICLE_COUNT,
            "exploratory_bootstrap_percentile_interval": [ordered[lower], ordered[upper]],
            "article_sign_counts": {"negative": sum(x < 0 for x in effects),
                                    "zero": sum(x == 0 for x in effects),
                                    "positive": sum(x > 0 for x in effects)},
            "article_effects": effects,
            "per_replica_mean_delta_nll": {
                str(seed): math.fsum(rows[(a, r, shallow)]["independent_mean"]
                                     - rows[(a, r, 8)]["independent_mean"]
                                     for a in range(ARTICLE_COUNT)) / ARTICLE_COUNT
                for r, seed in enumerate((3101, 3202, 3303))}}
    actual["scientific_results"] = result
    return binding, actual, errors, blockers


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source, output = args.rows.resolve(), args.output.resolve()
    if output.exists() or output == source or output == Path(__file__).resolve():
        parser.error("output must be a new file distinct from input and script")
    binding = {"path": str(source)}
    actual = {"scientific_results": None}
    errors, blockers = [], []
    try:
        binding, actual, errors, blockers = inspect_rows(source)
    except Exception as exc:
        blockers.append({"issue": "independent review could not complete",
                         "exception_type": type(exc).__name__, "detail": str(exc)})
    status = "FAIL" if errors else "BLOCKED" if blockers else "PASS"
    report = {"Purpose": "Independently recompute paired article-level summaries from saved rows only",
              "Environment": {"python": sys.version, "dependencies": "standard library only",
                              "model_or_formal_auditor_imported": False},
              "Input": binding,
              "Expected": {"articles": ARTICLE_COUNT, "replicas": REPLICA_COUNT,
                           "depths": list(DEPTHS), "rows": 288, "scored_tokens_per_row": TOKEN_COUNT,
                           "arithmetic_atol": TOLERANCE, "arithmetic_rtol": 0},
              "Actual": actual, "Status": status,
              "Status_scope": "Saved-row integrity and descriptive arithmetic; no quality or scientific superiority verdict",
              "errors": errors, "blockers": blockers,
              "limitations": [
                  "This review reads rows.jsonl only; it does not independently establish input selection, tokenization, source pins, runtime, state preservation or control-forward validity.",
                  "No logits or model are loaded or regenerated; saved NLL values are checked against saved logsumexp and target logits.",
                  "h0 and RNG pairing compares recorded digests, not newly observed tensors or RNG states.",
                  "The intervals are exploratory and conditional on these 32 historical article windows and this fixed model.",
                  "No equivalence, fresh-test generalization, ACT benefit, reasoning improvement or hardware-efficiency claim is established."],
              "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "review_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"Status": status, "unique_rows": actual.get("unique_rows"),
                      "errors": len(errors), "blockers": len(blockers), "output": str(output)}))
    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
