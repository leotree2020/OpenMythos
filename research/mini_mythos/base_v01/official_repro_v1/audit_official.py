"""Read-only CORE evidence audit. No Torch, tokenizer, model or RNG-state replay.

PyYAML only parses the original task configuration. Python random reconstructs
the official dataset shuffle; it never samples tokens or touches model RNG.
"""
import argparse
from collections import Counter
import csv
import datetime
import hashlib
import io
import json
import math
from pathlib import Path
import random
import sys
import traceback

import yaml


SEEDS = (1234, 2345, 3456)
TOLERANCE = 2e-7


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def near(actual, expected):
    return number(actual) and number(expected) and abs(actual - expected) <= TOLERANCE


def token_list(value):
    return isinstance(value, list) and all(type(x) is int and 0 <= x < 32768 for x in value)


def population_sd(values):
    mean = sum(values) / len(values)
    return (sum((value - mean) ** 2 for value in values) / len(values)) ** 0.5


def strict_json(raw):
    def pairs(items):
        value = {}
        for key, entry in items:
            if key in value:
                raise ValueError("Duplicate JSON key: " + key)
            value[key] = entry
        return value

    def invalid(value):
        raise ValueError("Nonfinite JSON value: " + value)

    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)


class Audit:
    def __init__(self, run, bundle, maximum):
        self.run, self.bundle, self.maximum = run, bundle, maximum
        self.failures, self.blockers, self.checks = [], [], []
        self.bindings, self.statistics = {}, {}

    def issue(self, reason, actual=None, blocked=False):
        (self.blockers if blocked else self.failures).append({"reason": reason, "actual": actual})

    def check(self, purpose, expected, actual, okay, blocked=False):
        status = "PASS" if okay else "BLOCKED" if blocked else "FAIL"
        self.checks.append({"Purpose": purpose, "Environment": "saved evidence; stdlib and PyYAML only",
                            "Input": str(self.run), "Expected": expected, "Actual": actual, "Status": status})
        if not okay:
            self.issue(purpose, actual, blocked)

    def read(self, path):
        raw = path.read_bytes()
        self.bindings[str(path)] = {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
        return raw.decode("utf-8")

    def load(self, path):
        return strict_json(self.read(path))

    def inventory(self):
        config = yaml.safe_load(self.read(self.bundle / "core.yaml"))
        tasks = config["icl_tasks"]
        if not isinstance(tasks, list) or len(tasks) != 22:
            raise ValueError("Frozen CORE requires exactly 22 task entries")
        inventory = {}
        for meta in tasks:
            label = meta["label"]
            if not isinstance(label, str) or label in inventory:
                raise ValueError("Invalid or duplicate CORE task label")
            kind = meta["icl_task_type"]
            if kind not in ("multiple_choice", "schema", "language_modeling"):
                raise ValueError("Unsupported official task type: " + str(kind))
            data_root = (self.bundle / "eval_data").resolve()
            path = (data_root / meta["dataset_uri"]).resolve()
            if not path.is_relative_to(data_root):
                raise ValueError("Dataset path is outside the original bundle")
            rows = [strict_json(line) for line in self.read(path).splitlines()]
            random.Random(1337).shuffle(rows)
            count = len(rows) if self.maximum == -1 else min(self.maximum, len(rows))
            if not count or count <= meta["num_fewshot"][0]:
                raise ValueError("Insufficient rows for official few-shot pool: " + label)
            retained = rows[:count]
            inventory[label] = {
                "kind": kind, "full_rows": len(rows), "scored_rows": count,
                "num_fewshot": meta["num_fewshot"][0], "dataset_uri": meta["dataset_uri"],
                "items": [{"sha256": hashlib.sha256(json.dumps(item, sort_keys=True).encode()).hexdigest(),
                           "gold": item.get("gold"),
                           "options": len(item["choices"]) if kind == "multiple_choice"
                           else len(item["context_options"]) if kind == "schema" else 1}
                          for item in retained],
            }
        baselines = {}
        for row in csv.DictReader(io.StringIO(self.read(self.bundle / "eval_meta_data.csv"))):
            label = row["Eval Task"]
            if label in baselines:
                raise ValueError("Duplicate task in baseline CSV: " + label)
            baselines[label] = float(row["Random baseline"])
        for label in inventory:
            baseline = baselines.get(label)
            if not number(baseline) or not 0 <= baseline < 100:
                raise ValueError("Missing or invalid chance baseline: " + label)
            inventory[label]["random_baseline_percent"] = baseline
        full = sum(meta["full_rows"] for meta in inventory.values())
        self.check("Original CORE task inventory", {"tasks": 22, "full_rows_per_seed": 91037},
                   {"tasks": len(inventory), "full_rows_per_seed": full}, len(inventory) == 22 and full == 91037)
        return inventory

    def audit(self):
        inventory = self.inventory()
        events = [strict_json(line) for line in self.read(self.run / "observations.jsonl").splitlines()]
        by_kind = {}
        for row in events:
            if not isinstance(row, dict):
                raise ValueError("Observation row is not an object")
            by_kind.setdefault(row.get("kind"), []).append(row)
        allowed = {"environment", "command", "loaded", "example", "task", "completion",
                   "error", "forward_model_exception", "example_incomplete", "task_incomplete"}
        self.check("Known observation schemas", sorted(allowed), sorted(str(k) for k in by_kind),
                   set(by_kind).issubset(allowed))
        for kind in ("environment", "command", "loaded", "completion"):
            self.check("Exactly one " + kind + " observation", 1, len(by_kind.get(kind, [])),
                       len(by_kind.get(kind, [])) == 1, blocked=not by_kind.get(kind))
        self.check("No observed official fallback or runtime exception", 0,
                   by_kind.get("forward_model_exception", []) + by_kind.get("error", []),
                   not by_kind.get("forward_model_exception") and not by_kind.get("error"), blocked=True)
        self.check("No incomplete example or task observations", 0,
                   by_kind.get("example_incomplete", []) + by_kind.get("task_incomplete", []),
                   not by_kind.get("example_incomplete") and not by_kind.get("task_incomplete"), blocked=True)
        for row in events:
            if not number(row.get("elapsed_s")) or row["elapsed_s"] < 0:
                self.issue("Invalid observation elapsed time", row)
            if type(row.get("maxrss_kib")) is not int or row["maxrss_kib"] < 0:
                self.issue("Invalid Linux maximum RSS observation", row)
        loaded = by_kind.get("loaded", [{}])[0]
        self.check("Official loaded model recurrence and precision", "ModelingParcae, depth 8, FP32 parameters",
                   loaded, loaded.get("model_class") == "ModelingParcae"
                   and loaded.get("mean_recurrence") == 8 and loaded.get("dtypes") == ["torch.float32"],
                   blocked=not by_kind.get("loaded"))
        command = by_kind.get("command", [{}])[0]
        argv = command.get("argv", [])
        def argument(name):
            return argv[argv.index(name) + 1] if name in argv and argv.index(name) + 1 < len(argv) else None
        self.check("Recorded official CPU command and sample limit", {"device": "cpu", "max_per_task": self.maximum},
                   {"argv": argv, "spec_max_per_task": command.get("spec", {}).get("max_per_task")},
                   argument("--device_type") == "cpu" and argument("--tasks.core.max_per_task") == str(self.maximum)
                   and command.get("spec", {}).get("max_per_task") == self.maximum)
        expected = {(label, seed, idx) for label, meta in inventory.items()
                    for seed in SEEDS for idx in range(meta["scored_rows"])}
        expected_tasks = {(label, seed) for label in inventory for seed in SEEDS}
        examples, tasks, computed = {}, {}, {}
        bad_examples = []
        empty_answers = []
        for row in by_kind.get("example", []):
            key = (row.get("task"), row.get("seed"), row.get("idx"))
            if key not in expected or type(row.get("seed")) is not int or type(row.get("idx")) is not int:
                self.issue("Unexpected example identity", key)
                continue
            if key in examples:
                self.issue("Duplicate example identity", key)
                continue
            examples[key] = row
            label, seed, idx = key
            meta = inventory[label]
            original = meta["items"][idx]
            reasons = []
            if row.get("item_sha256") != original["sha256"]:
                reasons.append("shuffled original item hash differs")
            if type(row.get("correct")) is not bool:
                reasons.append("correct is not Boolean")
            if not number(row.get("seconds")) or row["seconds"] < 0:
                reasons.append("invalid example duration")
            shape = row.get("input_shape")
            if (not isinstance(shape, list) or len(shape) != 2 or any(type(x) is not int for x in shape)
                    or shape[0] != original["options"] or not 1 <= shape[1] <= 2048):
                reasons.append("unexpected observed input shape")
            decision = None
            if meta["kind"] in ("multiple_choice", "schema"):
                losses, gold = row.get("mean_losses"), row.get("gold")
                if (not isinstance(losses, list) or len(losses) != original["options"]
                        or not all(number(x) for x in losses) or type(gold) is not int
                        or gold != original["gold"] or not 0 <= gold < original["options"]):
                    reasons.append("invalid mean losses or gold option")
                else:
                    # list.index reproduces the official first-index tie rule.
                    decision = losses.index(min(losses)) == gold
            else:
                predicted, gold = row.get("predicted_answer_tokens"), row.get("gold_answer_tokens")
                if not token_list(predicted) or not token_list(gold) or len(predicted) != len(gold):
                    reasons.append("invalid recorded LM answer token arrays")
                else:
                    decision = predicted == gold
                    if not gold:
                        empty_answers.append(key)  # Original all(empty) behavior; never repair the score.
            if decision is not None and decision != row.get("correct"):
                reasons.append("recomputed decision differs from recorded correct")
            if reasons:
                bad_examples.append({"identity": key, "reasons": reasons})
            else:
                computed[key] = decision
        for row in by_kind.get("task", []):
            key = (row.get("task"), row.get("seed"))
            if key not in expected_tasks or type(row.get("seed")) is not int:
                self.issue("Unexpected task identity", key)
            elif key in tasks:
                self.issue("Duplicate task summary", key)
            else:
                tasks[key] = row
                if (row.get("rows") != inventory[key[0]]["scored_rows"] or not number(row.get("seconds"))
                        or row["seconds"] < 0 or not number(row.get("accuracy"))):
                    self.issue("Invalid task summary values", row)
        missing_examples = sorted(expected - set(examples))
        missing_tasks = sorted(expected_tasks - set(tasks))
        self.check("Complete unique example coverage", len(expected),
                   {"records": len(by_kind.get("example", [])), "unique": len(examples),
                    "missing_count": len(missing_examples), "missing_first_30": missing_examples[:30]},
                   set(examples) == expected and len(by_kind.get("example", [])) == len(expected),
                   blocked=bool(missing_examples))
        self.check("Complete unique task coverage", len(expected_tasks),
                   {"records": len(by_kind.get("task", [])), "unique": len(tasks), "missing": missing_tasks},
                   set(tasks) == expected_tasks and len(by_kind.get("task", [])) == len(expected_tasks),
                   blocked=bool(missing_tasks))
        self.check("Every recorded decision recomputes from saved scores/tokens", "all recorded examples valid",
                   {"valid": len(computed), "invalid": bad_examples}, not bad_examples)
        try:
            process_end = self.load(self.run / "PROCESS_COMPLETION.json")
        except FileNotFoundError:
            process_end = {}
        completion = by_kind.get("completion", [{}])[0]
        expected_counts = {"examples": len(expected), "forward_model_exceptions": 0}
        self.check("Successful terminal evidence and complete counts", {"exit_code": 0, "counts": expected_counts},
                   {"process": process_end, "observation": completion},
                   process_end.get("exit_code") == 0 and process_end.get("counts") == expected_counts
                   and process_end.get("failures") == [] and completion.get("exit_code") == 0
                   and completion.get("counts") == expected_counts
                   and bool(events) and events[-1].get("kind") == "completion", blocked=True)
        per_seed = {seed: {"results": {}, "centered_results": {}} for seed in SEEDS}
        timing = {}
        for label, meta in inventory.items():
            seed_times = {}
            for seed in SEEDS:
                identities = [(label, seed, idx) for idx in range(meta["scored_rows"])]
                if all(key in computed for key in identities):
                    accuracy = sum(computed[key] for key in identities) / len(identities)
                    baseline = meta["random_baseline_percent"] / 100
                    per_seed[seed]["results"][label] = accuracy
                    per_seed[seed]["centered_results"][label] = (accuracy - baseline) / (1 - baseline)
                    if (label, seed) in tasks and not near(tasks[(label, seed)]["accuracy"], accuracy):
                        self.issue("Task return differs from independent Boolean mean",
                                   {"task": label, "seed": seed, "expected": accuracy,
                                    "actual": tasks[(label, seed)]["accuracy"]})
                task = tasks.get((label, seed))
                if task and number(task.get("seconds")) and task["seconds"] >= 0:
                    seed_times[str(seed)] = task["seconds"]
            total = sum(seed_times.values()) if len(seed_times) == len(SEEDS) else None
            timing[label] = {"full_rows_per_seed": meta["full_rows"], "scored_rows_per_seed": meta["scored_rows"],
                             "observed_task_seconds_by_seed": seed_times, "observed_three_seed_seconds": total,
                             "estimated_full_three_seed_seconds": total * meta["full_rows"] / meta["scored_rows"]
                             if total is not None else None}
        metrics_complete = all(set(per_seed[seed]["results"]) == set(inventory) for seed in SEEDS)
        official = None
        try:
            official_document = self.load(self.run / "eval/core.json")
            official = official_document["core"]
        except FileNotFoundError:
            self.issue("Official eval/core.json is unavailable", blocked=True)
        if metrics_complete:
            for seed in SEEDS:
                per_seed[seed]["core_metric"] = sum(per_seed[seed]["centered_results"].values()) / len(inventory)
            aggregated = {"results": {}, "results_std": {}, "centered_results": {}, "centered_results_std": {}}
            for label in inventory:
                for name in ("results", "centered_results"):
                    values = [per_seed[seed][name][label] for seed in SEEDS]
                    aggregated[name][label] = sum(values) / len(values)
                    aggregated[name + "_std"][label] = population_sd(values)
            core_values = [per_seed[seed]["core_metric"] for seed in SEEDS]
            aggregated["core_metric"] = sum(core_values) / len(core_values)
            aggregated["core_metric_std"] = population_sd(core_values)
            expected_core = {"per_seed": {str(seed): per_seed[seed] for seed in SEEDS}, "aggregated": aggregated,
                             "seeds": list(SEEDS), "results": aggregated["results"],
                             "centered_results": aggregated["centered_results"], "core_metric": aggregated["core_metric"]}
            mismatches = []
            def compare(actual, expected_value, path):
                if isinstance(expected_value, dict):
                    if not isinstance(actual, dict) or set(actual) != set(expected_value):
                        mismatches.append({"path": path, "expected_keys": list(expected_value),
                                           "actual_keys": list(actual) if isinstance(actual, dict) else None})
                        return
                    for key, value in expected_value.items():
                        compare(actual[key], value, path + "/" + str(key))
                elif isinstance(expected_value, list):
                    if actual != expected_value or not isinstance(actual, list) or any(type(x) is not int for x in actual):
                        mismatches.append({"path": path, "expected": expected_value, "actual": actual})
                elif not near(actual, expected_value):
                    mismatches.append({"path": path, "expected": expected_value, "actual": actual})
            if official is not None:
                compare(official, expected_core, "core")
                self.check("All official task/centered/macro/population-SD scores recompute", {"absolute_tolerance": TOLERANCE},
                           mismatches, not mismatches)
            self.statistics["recomputed_core"] = expected_core
        else:
            self.issue("Incomplete decisions prevent full CORE metric recomputation", blocked=True)
        estimated = [row["estimated_full_three_seed_seconds"] for row in timing.values()]
        peak = max((row["maxrss_kib"] for row in events if type(row.get("maxrss_kib")) is int), default=None)
        self.statistics.update({
            "expected_examples": len(expected), "observed_examples": len(by_kind.get("example", [])),
            "expected_tasks": len(expected_tasks), "observed_tasks": len(by_kind.get("task", [])),
            "observed_examples_by_seed": dict(Counter(str(row.get("seed")) for row in by_kind.get("example", []))),
            "full_examples_three_seeds": len(SEEDS) * sum(meta["full_rows"] for meta in inventory.values()),
            "elapsed_at_loaded_seconds": loaded.get("elapsed_s"),
            "process_elapsed_seconds": process_end.get("elapsed_s"),
            "peak_rss_kib": peak, "peak_rss_gib": peak / (1024 * 1024) if peak is not None else None,
            "task_timings_exclude_model_load": True, "task_timings": timing,
            "observed_all_task_seconds": sum(row["seconds"] for row in tasks.values() if number(row.get("seconds"))),
            "estimated_full_three_seed_seconds": sum(estimated) if all(value is not None for value in estimated) else None,
            "empty_lm_answer_slices": empty_answers,
            "metrics_complete": metrics_complete,
        })


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--max-per-task", type=int, choices=(12, -1), default=12)
    args = parser.parse_args()
    run, bundle, output = args.run.resolve(), args.bundle.resolve(), args.output.resolve()
    if output.exists() or output.is_relative_to(run) or output.is_relative_to(bundle):
        parser.error("Output must be new and outside the immutable run and benchmark bundle")
    audit = Audit(run, bundle, args.max_per_task)
    try:
        audit.audit()
    except BaseException as exc:
        audit.issue("Audit could not complete", {"type": type(exc).__name__, "error": repr(exc),
                                                "traceback": traceback.format_exc()}, blocked=True)
    status = "FAIL" if audit.failures else "BLOCKED" if audit.blockers else "PASS"
    result = {
        "Purpose": "Independently recompute official CORE decisions, aggregates and measured resource estimates",
        "Environment": {"python": sys.version, "yaml": yaml.__version__, "model_execution": False},
        "Input": {"run": str(run), "bundle": str(bundle), "max_per_task": args.max_per_task,
                  "seeds": list(SEEDS), "file_bindings": audit.bindings,
                  "audit_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
        "Expected": "Complete official coverage; depth8/FP32; no exceptions; exit0; all metrics within 2e-7",
        "Actual": audit.statistics, "Status": status, "checks": audit.checks,
        "failures": audit.failures, "blockers": audit.blockers,
        "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "limitations": [
            "Model logits, tokenization, attention and RNG are not rerun; decisions are independently reconstructed from saved outputs.",
            "Input item identities are checked against original JSONL after official shuffle1337; few-shot rendering is not reconstructed here.",
            "Task timings measure evaluate_task only, excluding model loading and outer dataset preparation; profiler overhead remains included.",
            "Full-duration estimates linearly scale each task's measured time by full_rows/scored_rows and are not confidence bounds.",
            "Limited few-shot pools, sequence lengths, machine load and long-run behavior can change full-run timing and scores.",
            "Peak RSS is the Linux observer's process high-water mark, not total machine or process-tree memory.",
            "Pipeline PASS does not establish paper-score replication, positive language quality, fresh-test generalization or training/resume.",
            "Protected source/environment/input preservation requires the separate pre/post integrity record; this audit binds bytes it read.",
        ],
    }
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"Status": status, "examples": audit.statistics.get("observed_examples"),
                      "tasks": audit.statistics.get("observed_tasks"), "failures": len(audit.failures),
                      "blockers": len(audit.blockers), "output": str(output)}))
    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
