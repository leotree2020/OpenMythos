"""Describe fully completed CORE seeds without changing the full-run acceptance.

Read-only stdlib post-processing. No model, tokenizer, RNG or score-generation
execution. Full row counts come from the separately frozen task inventory.
"""
import argparse
import csv
import datetime
import hashlib
import io
import json
import math
from pathlib import Path
import sys
import traceback


SEEDS = (1234, 2345, 3456)
ROWS_PER_TASK = 12
TOLERANCE = 2e-7


def numeric(value):
    return type(value) in (int, float) and math.isfinite(value)


def tokens(value):
    return isinstance(value, list) and all(type(v) is int and 0 <= v < 32768 for v in value)


def loads(text):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON key: " + key)
            result[key] = value
        return result
    def invalid(value):
        raise ValueError("Nonfinite JSON value: " + value)
    return json.loads(text, object_pairs_hook=pairs, parse_constant=invalid)


def summarize(run, bundle, inventory_path):
    bindings = {}
    errors = []
    def read(path):
        raw = path.read_bytes()
        bindings[str(path)] = {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
        return raw.decode("utf-8")
    metadata = loads(read(inventory_path))
    if not isinstance(metadata, list) or len(metadata) != 22:
        raise ValueError("Expected frozen inventory of 22 tasks")
    inventory = {}
    for entry in metadata:
        label = entry.get("label")
        if not isinstance(label, str) or label in inventory or type(entry.get("rows")) is not int or entry["rows"] < ROWS_PER_TASK:
            raise ValueError("Invalid or duplicate frozen task inventory entry")
        if entry.get("icl_task_type") not in ("multiple_choice", "schema", "language_modeling"):
            raise ValueError("Unsupported task type in frozen inventory")
        inventory[label] = entry
    if sum(entry["rows"] for entry in inventory.values()) != 91037:
        raise ValueError("Frozen full row total differs from 91037")
    baseline = {}
    for row in csv.DictReader(io.StringIO(read(bundle / "eval_meta_data.csv"))):
        label = row["Eval Task"]
        if label in baseline:
            raise ValueError("Duplicate CSV task baseline")
        baseline[label] = float(row["Random baseline"]) / 100
    if any(label not in baseline or not numeric(baseline[label]) or not 0 <= baseline[label] < 1 for label in inventory):
        raise ValueError("Missing or invalid original chance baseline")
    observations = [loads(line) for line in read(run / "observations.jsonl").splitlines()]
    examples, task_rows = {}, {}
    invalid_seeds = {seed: [] for seed in SEEDS}
    interrupted_seeds = {seed: [] for seed in SEEDS}
    exceptions = []
    for position, row in enumerate(observations):
        if not isinstance(row, dict):
            raise ValueError("Observation is not an object")
        kind = row.get("kind")
        if kind in ("error", "forward_model_exception", "example_incomplete", "task_incomplete"):
            exceptions.append(row)
            if row.get("seed") in interrupted_seeds:
                interrupted_seeds[row["seed"]].append("exception/incomplete observation at row " + str(position))
        if kind not in ("example", "task"):
            continue
        label, seed = row.get("task"), row.get("seed")
        if label not in inventory or type(seed) is not int or seed not in SEEDS:
            errors.append({"reason": "Unexpected task or seed identity", "row": position})
            continue
        if kind == "example":
            idx = row.get("idx")
            if type(idx) is not int or not 0 <= idx < ROWS_PER_TASK:
                invalid_seeds[seed].append("unexpected example index: " + repr(idx))
                continue
            key = (seed, label, idx)
            if key in examples:
                invalid_seeds[seed].append("duplicate example: " + repr(key))
                continue
            valid = type(row.get("correct")) is bool
            decision = None
            if inventory[label]["icl_task_type"] in ("multiple_choice", "schema"):
                losses, gold = row.get("mean_losses"), row.get("gold")
                valid = valid and isinstance(losses, list) and bool(losses) and all(numeric(v) for v in losses)
                valid = valid and type(gold) is int and isinstance(losses, list) and 0 <= gold < len(losses)
                if valid:
                    decision = losses.index(min(losses)) == gold
            else:
                predicted, gold = row.get("predicted_answer_tokens"), row.get("gold_answer_tokens")
                valid = valid and tokens(predicted) and tokens(gold) and len(predicted) == len(gold)
                if valid:
                    decision = predicted == gold
            if not valid or decision != row.get("correct"):
                invalid_seeds[seed].append("invalid/non-recomputable recorded decision: " + repr(key))
            else:
                examples[key] = row
        else:
            key = (seed, label)
            if key in task_rows:
                invalid_seeds[seed].append("duplicate task result: " + repr(key))
                continue
            if (row.get("rows") != ROWS_PER_TASK or not numeric(row.get("accuracy"))
                    or not numeric(row.get("seconds")) or row["seconds"] < 0):
                invalid_seeds[seed].append("invalid task result: " + repr(key))
            else:
                task_rows[key] = row
    seed_reports = {}
    completed = []
    for seed in SEEDS:
        rows = []
        missing = []
        for label, meta in inventory.items():
            expected = [(seed, label, idx) for idx in range(ROWS_PER_TASK)]
            available = [examples[key] for key in expected if key in examples]
            task = task_rows.get((seed, label))
            if len(available) != ROWS_PER_TASK or task is None:
                missing.append({"task": label, "valid_examples": len(available), "task_return_present": task is not None})
                continue
            accuracy = sum(row["correct"] for row in available) / ROWS_PER_TASK
            if abs(accuracy - task["accuracy"]) > TOLERANCE:
                invalid_seeds[seed].append("task return differs from Boolean mean: " + label)
            centered = (accuracy - baseline[label]) / (1 - baseline[label])
            rows.append({"task": label, "correct": sum(row["correct"] for row in available),
                         "rows": ROWS_PER_TASK, "accuracy": accuracy,
                         "random_baseline": baseline[label], "centered_accuracy": centered,
                         "measured_task_seconds": task["seconds"], "full_rows": meta["rows"],
                         "estimated_full_task_seconds": task["seconds"] * meta["rows"] / ROWS_PER_TASK})
        complete = len(rows) == 22 and not missing and not invalid_seeds[seed] and not interrupted_seeds[seed]
        score = sum(row["centered_accuracy"] for row in rows) / 22 if complete else None
        estimate = sum(row["estimated_full_task_seconds"] for row in rows) if complete else None
        seed_reports[str(seed)] = {
            "complete_seed": complete, "expected_examples": 264,
            "valid_recorded_examples": sum(key[0] == seed for key in examples),
            "expected_tasks": 22, "complete_task_rows": len(rows),
            "descriptive_core_fraction": score,
            "descriptive_core_percentage_points": 100 * score if score is not None else None,
            "measured_complete_seed_task_seconds": sum(row["measured_task_seconds"] for row in rows) if complete else None,
            "estimated_full_one_seed_seconds": estimate,
            "estimated_full_three_seed_seconds_from_this_seed": 3 * estimate if estimate is not None else None,
            "tasks": rows, "missing": missing, "invalid_records": invalid_seeds[seed],
            "interrupted_records": interrupted_seeds[seed],
        }
        if complete:
            completed.append(seed)
    integrity_errors = errors + [{"seed": seed, "reasons": reasons} for seed, reasons in invalid_seeds.items() if reasons]
    status = "FAIL" if integrity_errors else "PASS" if len(completed) == 3 and not exceptions else "BLOCKED"
    process_completion = None
    if (run / "PROCESS_COMPLETION.json").exists():
        process_completion = loads(read(run / "PROCESS_COMPLETION.json"))
    return {
        "Purpose": "Describe only fully completed official CORE seeds in otherwise partial evidence",
        "Environment": "stdlib only; no model/tokenizer/RNG execution; source run remains read-only",
        "Input": {"run": str(run), "bundle": str(bundle), "inventory": str(inventory_path), "bindings": bindings},
        "Expected": "Each reported seed total requires all 22 tasks and 264 valid independently reconstructed Boolean decisions",
        "Actual": {"completed_seeds": completed, "planned_seeds": list(SEEDS),
                   "full_three_seed_coverage": len(completed) == 3,
                   "formal_acceptance_established_by_this_report": False,
                   "seed_reports": seed_reports, "observed_exceptions_or_incomplete": exceptions,
                   "recorded_process_completion": process_completion},
        "Status": status,
        "Status_scope": "Descriptive record coverage/integrity only; never replaces audit_official.py or the formal run status",
        "errors": integrity_errors,
        "limitations": [
            "Incomplete seeds have no CORE total; partial task scores are never averaged into a seed total.",
            "Decision reconstruction uses stored mean losses/gold or predicted/gold answer tokens; logits and tokenization are not rerun.",
            "Original item hashes, environment, complete terminal acceptance and source preservation remain the separate full auditor's responsibility.",
            "Task timing excludes model loading; estimates sum each completed seed's task_seconds * full_rows / 12.",
            "Three-seed estimates multiply that one seed's estimate by three; these are projections, not measured full runtimes or uncertainty intervals.",
            "Limited few-shot pools differ from full evaluation. These development-mode scores do not establish paper-score replication or full CORE acceptance.",
            "Incomplete/failed formal evidence remains incomplete/failed regardless of any completed seed's descriptive score.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--inventory", type=Path, default=Path(__file__).with_name("TASK_INVENTORY.json"))
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    run, bundle, inventory, output = args.run.resolve(), args.bundle.resolve(), args.inventory.resolve(), args.output.resolve()
    if output.exists() or output.is_relative_to(run) or output.is_relative_to(bundle):
        parser.error("Output must be new and outside the immutable run and benchmark bundle")
    try:
        result = summarize(run, bundle, inventory)
    except BaseException as exc:
        result = {"Purpose": "Describe fully completed seeds without changing formal acceptance", "Status": "BLOCKED",
                  "Input": {"run": str(run), "bundle": str(bundle), "inventory": str(inventory)},
                  "Expected": "Complete valid records for every reported seed", "Actual": {"error": repr(exc),
                  "type": type(exc).__name__, "traceback": traceback.format_exc(), "formal_acceptance_established_by_this_report": False}}
    result["utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    result["source_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"Status": result["Status"], "completed_seeds": result.get("Actual", {}).get("completed_seeds", []),
                      "formal_acceptance_established_by_this_report": False, "output": str(output)}))
    return 0 if result["Status"] == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
