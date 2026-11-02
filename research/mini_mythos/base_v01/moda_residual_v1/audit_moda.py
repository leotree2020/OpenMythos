"""Final compact-evidence audit; only retained36 full rows are re-auditable."""
from __future__ import annotations
import argparse
import datetime
import hashlib
import json
import math
from pathlib import Path
import platform
import struct
import sys
import traceback
sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_row as rowaudit
read, info, save, sha = rowaudit.read, rowaudit.info, rowaudit.save, rowaudit.sha

def comparison_label(delta_nll, delta_accuracy):
    if not math.isfinite(delta_nll) or not math.isfinite(delta_accuracy):
        raise ValueError("Finite comparison metrics required")
    if delta_nll <= -.01 and delta_accuracy >= -.01:
        return "IMPROVEMENT"
    if delta_nll >= .01 or delta_accuracy < -.01:
        return "WORSE"
    return "NO_QUALIFIED_IMPROVEMENT"


def summarize(records, ids):
    """Article-equal mean; seeds repeated observations, never independent articles."""
    by_key = {(r["arm"], r["train_seed"], r["eval_seed"], r["article_id"]): r for r in records}
    if len(by_key) != len(records):
        raise ValueError("Duplicate evaluation key")
    combinations = [("fixed32", None)] + [(arm, seed) for arm in ("shared", "depth") for seed in (4101, 4202)]
    required = {(arm, seed, es, article) for arm, seed in combinations for es in (5101, 5202) for article in ids}
    if set(by_key) != required or len(ids) != 16 or len(set(ids)) != 16:
        raise ValueError("Exact160-row evaluation coverage required")
    means, comparisons = {}, {}
    for arm, seed in combinations:
        rows = [by_key[(arm, seed, es, a)] for a in ids for es in (5101, 5202)]
        label = arm if seed is None else f"{arm}_{seed}"
        means[label] = {"mean_nll": math.fsum(r["nll_mean"] for r in rows) / 32,
                        "correct": sum(r["correct"] for r in rows), "scored_observations": 2048,
                        "accuracy": sum(r["correct"] for r in rows) / 2048}
    for seed in (4101, 4202):
        for arm, comparator, cseed in (("shared", "fixed32", None), ("depth", "fixed32", None), ("depth", "shared", seed)):
            article_rows = []
            for article in ids:
                left = [by_key[(arm, seed, es, article)] for es in (5101, 5202)]
                right = [by_key[(comparator, cseed, es, article)] for es in (5101, 5202)]
                article_rows.append({"article_id": article,
                                     "delta_nll": math.fsum(l["nll_mean"] - r["nll_mean"] for l,r in zip(left,right)) / 2,
                                     "delta_correct": sum(l["correct"] - r["correct"] for l,r in zip(left,right))})
            delta = math.fsum(r["delta_nll"] for r in article_rows) / 16
            delta_acc = sum(r["delta_correct"] for r in article_rows) / 2048
            comparisons[f"{arm}_vs_{comparator}_{seed}"] = {
                "delta_nll": delta, "delta_accuracy": delta_acc, "per_article": article_rows,
                "worst_article_delta_nll": max(r["delta_nll"] for r in article_rows),
                "articles_improved": sum(r["delta_nll"] < 0 for r in article_rows),
                "screen": delta <= -.01 and delta_acc >= -.01,
                "interpretation": comparison_label(delta, delta_acc)}
    screens = {}
    for arm in ("shared", "depth"):
        passed = all(comparisons[f"{arm}_vs_fixed32_{seed}"]["screen"] for seed in (4101, 4202))
        screens[arm + "_vs_fixed32"] = {"Status": "PASS" if passed else "FAIL",
            "Expected": "Both training seeds: mean NLL improvement >=0.01 nats/token AND accuracy loss <=1 percentage point; average two h0 seeds per article",
            "scope": "Exploratory fixed-budget adaptation screen; not statistical confirmation"}
    screens["depth_vs_shared"] = {"Status": "PASS" if all(comparisons[f"depth_vs_shared_{s}"]["screen"] for s in (4101,4202)) else "FAIL",
        "Expected": "Same descriptive margins as primary screen in both training seeds",
        "scope": "Secondary exploratory equal-12288-parameter output-projection comparison; joint depth memory versus current-sequence attention control; compute/optimization may differ"}
    interpretations = {}
    for comparison in ("shared_vs_fixed32", "depth_vs_fixed32", "depth_vs_shared"):
        per_seed = {str(seed): comparisons[f"{comparison}_{seed}"]["interpretation"] for seed in (4101, 4202)}
        labels = set(per_seed.values())
        interpretations[comparison] = {"per_seed": per_seed,
            "combined": next(iter(labels)) if len(labels) == 1 else "MIXED",
            "scope": "Descriptive frozen practical margins; not equivalence or population inference"}
    return {"means": means, "comparisons": comparisons, "scientific_screens": screens,
            "result_interpretations": interpretations}


def confined(root, relative):
    candidate = Path(relative)
    path = (root / candidate).resolve()
    rowaudit.require(not candidate.is_absolute() and path.is_relative_to(root.resolve()), "Confined evidence path")
    return path


def validate_training(adapter, rows):
    rowaudit.require(adapter["steps"] == 32 and adapter["trainable_parameters"] == 12288 and len(rows) == 32,
                     "Equal12288 parameter/32step budget")
    rowaudit.require({r["step"] for r in rows} == set(range(32)), "Unique32 optimizer steps")
    union = [False] * 32
    history_active = {"key": False, "value": False}
    for record in rows:
        rowaudit.require((record["arm"], record["train_seed"]) == (adapter["arm"], adapter["train_seed"]), "Training adapter identity")
        rowaudit.require(record["nonzero_o_proj_gradient"] is True, "Active output-projection gradient")
        for key in ("gradient_norm_before_clip", "output_update_norm"):
            rowaudit.require(type(record[key]) in (float, int) and math.isfinite(record[key]) and record[key] > 0,
                             "Finite positive training gradient/update")
        depth = record["depth_gradient_coverage"]
        norms = record["depth_o_proj_gradient_norms"]
        rowaudit.require(len(depth) == len(norms) == 32 and all(type(x) is bool for x in depth)
                         and all(type(x) in (float, int) and math.isfinite(x) and x >= 0 for x in norms)
                         and depth == [x > 0 for x in norms], "Depth contribution norm/coverage")
        union = [a or b for a, b in zip(union, depth)]
        trace = record["branch_trace"]
        rowaudit.require(trace["writer_calls"] == 32 and trace["arm"] == adapter["arm"]
                         and trace["read_lengths"] == (list(range(32)) if adapter["arm"] == "depth" else [0] * 32),
                         "Exact current-sequence/depth-history control")
        for component in ("key", "value"):
            history = record["history_gradients"][component]
            expected = [True] * 31 + [False] if adapter["arm"] == "depth" else [False] * 32
            rowaudit.require(history["present"] == expected and len(history["norms"]) == 32,
                             "Actual memory read/unused writer gradient coverage")
            for present, norm in zip(expected, history["norms"]):
                rowaudit.require((type(norm) in (float,int) and math.isfinite(norm) and norm >= 0) if present else norm is None,
                                 "Finite used history gradients and absent unused gradients")
                if present:
                    history_active[component] |= norm > 0
                    if record["step"] == 0:
                        rowaudit.require(norm == 0, "Initial zero output projection blocks history gradient")
    rowaudit.require(adapter["gradient_coverage"] is True and adapter["depth_gradient_coverage"] == union and all(union),
                     "All32 output-projection depth paths active")
    rowaudit.require(adapter["parameter_changes"] == {"o_proj": True}, "Output projection changed")
    rowaudit.require(adapter["features_before"] == adapter["features_after"] and bool(adapter["features_before"]), "Frozen feature state unchanged")
    rowaudit.require(adapter["history_gradient_active"] == history_active and
                     history_active == {"key":adapter["arm"]=="depth", "value":adapter["arm"]=="depth"},
                     "History key/value active only in memory arm after learning")
    return {"steps": 32, "trainable_parameters": 12288, "active_depths": sum(union), "history_gradient_active":history_active}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run, checks = args.run.resolve(), []
    worker = run / "worker"
    report = {"Purpose": "Audit compact receipts and recompute36 retained complete logits;124 full trained rows unavailable after live audit",
              "Environment": {"python": sys.version, "executable": sys.executable, "torch_imported": False},
              "Input": {"run": str(run)}, "Expected": "160 exact live audits;32 historical full rows;4 sentinels;124 explicitly non-retained rows",
              "Actual": {}, "Status": "NOT TESTED", "checks": checks,
              "utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}

    def check(name, okay, actual=None):
        checks.append({"Purpose": name, "Environment": "Independent NumPy final audit", "Input": str(run),
                       "Expected": True, "Actual": actual, "Status": "PASS" if okay else "FAIL"})
        if not okay:
            raise ValueError(name)

    try:
        import numpy as np
        if not (platform.system()=="Linux" and platform.python_version()=="3.12.3" and sys.executable==rowaudit.DATA_PYTHON
                and np.__version__=="1.26.4" and sys.flags.isolated and sys.dont_write_bytecode):
            raise OSError("Frozen independent final NumPy environment unavailable")
        check("No model/Torch import", not any(n.split(".")[0] in ("torch", "parcae_lm", "receval") for n in sys.modules))
        spec = read(run / "spec.json")
        data = read(spec["data_path"])
        check("Frozen input payload", info(spec["data_path"])["sha256"] == spec["inputs_sha256"])
        completion = read(worker / "public/completion.json")
        check("Main engineering complete", completion.get("Status") == "PASS" and completion.get("preservation") == "PASS")
        budget = {"calls_started":293,"calls_completed":293,"train_steps":128,"eval_rows":160,
                  "zero_control_calls":5,"model_loads":1,"adapters_saved":4,"reload_calls":0}
        check("Main exact budget", all(completion["Actual"].get(k) == v for k, v in budget.items()))
        before = read(worker / "public/base_state_before.json")
        check("Base63 state hashes unchanged", len(before) == 63 and before == read(worker / "public/base_state_after.json"))
        reload = read(run / "reload/public/completion.json")
        check("Fresh-process reload complete", reload.get("Status") == "PASS" and reload.get("preservation") == "PASS"
              and reload["Actual"]["reload_calls"] == 4 and reload["Actual"]["model_loads"] == 1)
        training = [json.loads(line) for line in (worker / "public/training.jsonl").read_text().splitlines()]
        train_by = {(r["arm"], r["train_seed"], r["step"]): r for r in training}
        required = {(a,s,t) for a in ("shared","depth") for s in (4101,4202) for t in range(32)}
        check("Exact128 training rows", len(training) == len(train_by) == 128 and set(train_by) == required)
        for arm, seed, step in sorted(required):
            row = train_by[arm,seed,step]
            check(f"Frozen train input/step {arm} {seed} {step}", row["article_id"] == data["train"][step%16]["id"]
                  and row["h0_seed"] == 1000000+100*seed+step and row["optimizer_step"] == step+1
                  and row["targets"] == 128 and row["epoch"] == step//16 and math.isfinite(row["loss"])
                  and row["observer"]["adapter_calls"] == 32 and row["observer"]["core_block_calls"] == [32,32])
            if arm == "depth":
                check(f"Paired train h0/RNG {seed} {step}", row["observer"] == train_by["shared",seed,step]["observer"])
        adapters = read(worker / "public/adapters.json")
        check("Four complete trained adapters", adapters.get("Status") == "PASS" and len(adapters["rows"]) == 4
              and {(r["arm"], r["train_seed"]) for r in adapters["rows"]} == {(a,s) for a in ("shared","depth") for s in (4101,4202)})
        training_coverage = {}
        by_adapter = {(r["arm"],r["train_seed"]):r for r in adapters["rows"]}
        for seed in (4101,4202):
            check(f"Paired initial frozen features {seed}", by_adapter["shared",seed]["features_before"] == by_adapter["depth",seed]["features_before"])
        for adapter in adapters["rows"]:
            arm, seed = adapter["arm"], adapter["train_seed"]
            coverage = validate_training(adapter, [train_by[arm,seed,t] for t in range(32)])
            training_coverage[f"{arm}_{seed}"] = coverage
            check(f"Training gradient/preservation {arm} {seed}", True, coverage)
            check(f"Checkpoint bytes {arm} {seed}", info(confined(worker, adapter["path"])) == {"bytes": adapter["bytes"], "sha256": adapter["sha256"]})
        samples = {s["id"]: s for s in data["eval"]}
        check("16 development validation articles", len(samples) == 16 and not set(samples) & {s["id"] for s in data["train"]})
        evaluation = read(worker / "public/evaluation.json")
        check("160 complete evaluation rows", evaluation.get("Status") == "PASS" and len(evaluation["rows"]) == 160)
        ledger = [json.loads(line) for line in (worker / "public/retention.jsonl").read_text().splitlines()]
        ledger_by = {tuple(r["identity"][k] for k in ("arm","train_seed","eval_seed","article_id")): r for r in ledger}
        check("160 unique retention receipts", len(ledger) == len(ledger_by) == 160)
        records, retained, row_receipts, paired_h0 = [], {}, {}, {}
        retention_counts = {"historical_bridge":0, "sentinel":0, "audited_then_discarded":0}
        for index, row in enumerate(evaluation["rows"]):
            label = "row" + str(index)
            input_path, receipt_path = confined(worker, row["row_input_file"]), confined(worker, row["row_audit_file"])
            check(label+" immutable row metadata", read(input_path) == row)
            receipt = read(receipt_path)
            check(label+" complete live audit receipt", receipt.get("Status") == "PASS" and
                  receipt.get("Environment",{}).get("development_only") is False and
                  receipt["Input"]["row_input"] == info(input_path) and receipt["Input"]["identity"] == rowaudit.identity(row)
                  and receipt["Input"]["spec_sha256"] == info(run / "spec.json")["sha256"])
            actual = receipt["Actual"]
            check(label+" complete raw identity", actual["raw"] == {"bytes": rowaudit.RAW_BYTES, "sha256": row["logits_sha256"]}
                  and actual["finite_components"] == 64*32768)
            targets = samples[row["article_id"]]["tokens"][65:129]
            check(label+" targets unchanged", sha(struct.pack("<64q",*targets)) == row["targets_sha256"])
            metric = rowaudit.validate_columns(actual["columns"], targets)
            rowaudit.compare_worker(row, actual)
            check(label+" compact aggregate recomputed", abs(metric["nll_mean"]-actual["metrics"]["nll_mean"]) <= 1e-10
                  and abs(metric["nll_sum"]-actual["metrics"]["nll_sum"]) <= 1e-10
                  and metric["correct"] == actual["metrics"]["correct"])
            chunks = actual["chunks"]
            check(label+" eight complete chunk summaries", len(chunks)==8 and all(c["index"]==j and c["offset"]==j*1048576
                  and c["bytes"]==1048576 and len(c["sha256"])==64
                  and all(math.isfinite(c[k]) for k in ("sum64","sum_squares64","min64","max64")) for j,c in enumerate(chunks)))
            kind = rowaudit.expected_retention(row, data)
            check(label+" predeclared retention", row["retention"] == kind)
            retention_counts[kind] += 1
            item = ledger_by[tuple(row[k] for k in ("arm","train_seed","eval_seed","article_id"))]
            check(label+" retention ledger bound", item["action"] == kind and item["raw_path"] == row["raw_path"]
                  and item["raw_sha256"] == row["logits_sha256"] and item["row_input_file"] == row["row_input_file"]
                  and item["row_audit_file"] == row["row_audit_file"] and item["audit_sha256"] == info(receipt_path)["sha256"]
                  and item["raw_after_audit"] == actual["raw"])
            raw_path = Path(row["raw_path"]).resolve()
            check(label+" new path confined", raw_path.parent == (worker / "private").resolve())
            if kind == "sentinel":
                check(label+" sentinel retained", item["raw_exists_after"] is True and item["retained_path"] == str(raw_path)
                      and confined(worker,row["logits_file"]) == raw_path and info(raw_path) == actual["raw"])
                retained_path = raw_path
            elif kind == "historical_bridge":
                reference = rowaudit.historical_bridge(spec,row,actual)
                check(label+" immutable historical bridge", actual["baseline_reference"] == reference and
                      item["retained_path"] == reference["path"] and item["raw_exists_after"] is False and not raw_path.exists())
                retained_path = Path(reference["path"])
            else:
                check(label+" audited temporary disposal", not raw_path.exists() and item["retained_path"] is None
                      and item["raw_exists_after"] is False and row["logits_file"] is None and actual["baseline_reference"] is None)
                retained_path = None
            if retained_path is not None:
                recomputed = rowaudit.compute(np, retained_path.read_bytes(), targets)
                check(label+" retained full tensor independently recomputed", all(recomputed[k] == actual[k]
                      for k in ("raw","metrics","columns","chunks","finite_components")))
                retained[str(retained_path)] = actual["raw"]
            pair = (row["article_id"],row["eval_seed"])
            state = {k:row["observer"][k] for k in rowaudit.STABLE_OBSERVER}
            if pair in paired_h0:
                check(label+" matched eval h0/RNG", state == paired_h0[pair])
            else:
                paired_h0[pair] = state
            row_receipts[str(receipt_path)] = info(receipt_path)
            records.append(rowaudit.identity(row) | {"nll_mean":metric["nll_mean"],"correct":metric["correct"]})
        check("Declared retention exact counts", retention_counts == {"historical_bridge":32,"sentinel":4,"audited_then_discarded":124})
        check("No pending raw tensors remain", not list((worker/"private").glob("pending_row_*.bin")))
        result = summarize(records,list(samples))
        report["Actual"] = result | {"rows":160,"live_audited_components":160*64*32768,
            "retention_counts":retention_counts,"retained_full_rows_recomputed":36,
            "retrospective_full_logits_unavailable_rows":124,"retained_raw_manifest":retained,
            "live_receipt_manifest":row_receipts,"training_coverage":training_coverage,
            "evidence_limit":"124 nonsentinel candidate logits received full live audit but were not retained; hashes/statistics cannot restore them"}
        report["Status"] = "PASS"
    except BaseException as exc:
        report["Status"] = "BLOCKED" if isinstance(exc,(OSError,MemoryError)) else "FAIL"
        report["error"] = {"type":type(exc).__name__,"reason":str(exc),"traceback":traceback.format_exc()}
    report["check_counts"] = {s:sum(r["Status"]==s for r in checks) for s in ("PASS","FAIL")}
    save(args.output,report)
    print(json.dumps({"Status":report["Status"],"checks":report["check_counts"],"scientific_screens":report["Actual"].get("scientific_screens")},allow_nan=False))
    return 0 if report["Status"] == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())

