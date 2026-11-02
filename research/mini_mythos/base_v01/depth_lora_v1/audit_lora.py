"""Independent NumPy FP64 audit of final held-out logits; never imports Torch."""
from __future__ import annotations
import argparse
import datetime
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
import traceback


def sha(x):
    return hashlib.sha256(x).hexdigest()


def info(path):
    b = Path(path).read_bytes()
    return {"bytes": len(b), "sha256": sha(b)}


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save(path, obj):
    with Path(path).open("x", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False)
        f.write("\n")


def score_logits(np, logits, targets):
    if logits.shape != (64, 32768) or len(targets) != 64 or not np.isfinite(logits).all():
        raise ValueError("Saved logits shape/finiteness mismatch")
    if not all(type(t) is int and 0 <= t < 32768 for t in targets):
        raise ValueError("Scored target IDs mismatch")
    x = logits.astype(np.float64)
    maximum = np.max(x, axis=1)
    # Stable subtract-first ordering; no FP32 reduction or softmax in the audit.
    nll = maximum - x[np.arange(64), np.array(targets)] + np.log(np.exp(x - maximum[:, None]).sum(axis=1))
    predictions = np.argmax(logits, axis=1)
    return {"nll_mean": float(nll.mean()), "nll": nll.tolist(),
            "correct": int((predictions == targets).sum()), "predictions": predictions.tolist()}


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
                "screen": delta <= -.01 and delta_acc >= -.01}
    screens = {}
    for arm in ("shared", "depth"):
        passed = all(comparisons[f"{arm}_vs_fixed32_{seed}"]["screen"] for seed in (4101, 4202))
        screens[arm + "_vs_fixed32"] = {"Status": "PASS" if passed else "FAIL",
            "Expected": "Both training seeds: mean NLL improvement >=0.01 nats/token AND accuracy loss <=1 percentage point; average two h0 seeds per article",
            "scope": "Exploratory fixed-budget adaptation screen; not statistical confirmation"}
    screens["depth_vs_shared"] = {"Status": "PASS" if all(comparisons[f"depth_vs_shared_{s}"]["screen"] for s in (4101,4202)) else "FAIL",
        "Expected": "Same descriptive margins as primary screen in both training seeds",
        "scope": "Secondary exploratory comparison; trainable parameter counts differ32fold, so not isolated causal depth-specialization proof"}
    return {"means": means, "comparisons": comparisons, "scientific_screens": screens}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--run", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    run = args.run.resolve()
    worker = run / "worker"
    report = {"Purpose": "Independently recompute all final evaluation metrics from saved FP32 logits",
              "Environment": {"python": sys.version, "executable": sys.executable, "torch_imported": False},
              "Input": {"run": str(run)}, "Expected": "160 exact rows; finite hashed logits; paired h0; independent metrics and frozen screens",
              "Actual": {}, "Status": "NOT TESTED", "checks": [],
              "utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    def check(name, okay, actual=None):
        row = {"Purpose": name, "Environment": "Independent NumPy audit", "Input": str(run),
               "Expected": True, "Actual": actual, "Status": "PASS" if okay else "FAIL"}
        report["checks"].append(row)
        if not okay:
            raise ValueError(name)
    try:
        import numpy as np
        check("No model/Torch import", not any(n.split(".")[0] in ("torch", "parcae_lm", "receval") for n in sys.modules))
        spec = read(run / "spec.json")
        data_path = Path(spec["data_path"])
        data = read(data_path)
        check("Frozen payload hash", info(data_path)["sha256"] == spec["inputs_sha256"])
        completion = read(worker / "public" / "completion.json")
        check("Worker engineering complete", completion.get("Status") == "PASS" and completion.get("preservation") == "PASS")
        check("Worker exact main budget", completion["Actual"] == {
            "calls_started":293,"calls_completed":293,"train_steps":128,"eval_rows":160,
            "zero_control_calls":5,"model_loads":1,"adapters_saved":4,"reload_calls":0})
        check("Base state hashes unchanged", read(worker / "public" / "base_state_before.json") == read(worker / "public" / "base_state_after.json"))
        reload = read(run / "reload" / "public" / "completion.json")
        check("Fresh-process reload complete", reload.get("Status") == "PASS" and reload.get("preservation") == "PASS"
              and reload["Actual"]["reload_calls"] == 4 and reload["Actual"]["model_loads"] == 1)
        training = [json.loads(line) for line in (worker / "public" / "training.jsonl").read_text().splitlines()]
        train_by = {(r["arm"],r["train_seed"],r["step"]):r for r in training}
        required_train = {(arm,seed,step) for arm in ("shared","depth") for seed in (4101,4202) for step in range(32)}
        check("Exact128 training steps", len(training) == len(train_by) == 128 and set(train_by) == required_train)
        for arm,seed,step in sorted(required_train):
            record = train_by[arm,seed,step]
            check(f"Training budget/data/finite {arm} {seed} {step}", record["article_id"] == data["train"][step%16]["id"]
                  and record["targets"] == 128 and record["optimizer_step"] == step+1 and record["epoch"] == step//16
                  and record["h0_seed"] == 1000000+100*seed+step
                  and math.isfinite(record["loss"]) and math.isfinite(record["gradient_norm_before_clip"])
                  and record["observer"]["c_proj_calls"] == [32,32])
            if arm == "depth":
                check(f"Matched training h0/RNG {seed} {step}", record["observer"] == train_by["shared",seed,step]["observer"])
        samples = {s["id"]: s for s in data["eval"]}
        check("Frozen128 context /64 scored targets", data["context_tokens"] == 128 and data["scored_positions"] == [64,128])
        check("16 distinct held-out sources", len(samples) == 16)
        check("Train/eval article IDs disjoint", not set(samples) & {s["id"] for s in data["train"]})
        evaluation = read(worker / "public" / "evaluation.json")
        check("Worker evaluation complete", evaluation.get("Status") == "PASS")
        rows = evaluation["rows"]
        check("Exact160 planned rows", len(rows) == 160, len(rows))
        records, hashes, paired_h0 = [], {}, {}
        for index, row in enumerate(rows):
            label = f"row{index}"
            path = (worker / row["logits_file"]).resolve()
            check(label + " confined raw path", path.is_relative_to(worker.resolve()) and not Path(row["logits_file"]).is_absolute())
            check(label + " rawshape/dtype", row["shape"] == [64,32768] and row["dtype"] == "float32-le")
            stat = info(path)
            check(label + " exactsavedbytes", stat == {"bytes": 64*32768*4, "sha256": row["logits_sha256"]}, stat)
            hashes[str(path)] = stat
            targets = samples[row["article_id"]]["tokens"][65:129]
            check(label + " targetsha", sha(struct.pack("<64q", *targets)) == row["targets_sha256"])
            logits = np.fromfile(path, dtype="<f4").reshape(64,32768)
            metrics = score_logits(np, logits, targets)
            check(label + " independentNLL", abs(metrics["nll_mean"] - row["nll_mean"]) <= 1e-10,
                  {"computed": metrics["nll_mean"], "worker": row["nll_mean"]})
            check(label + " independentTop1", metrics["correct"] == row["correct"], metrics["correct"])
            key = (row["article_id"], row["eval_seed"])
            h = row["h0_sha256"]
            check(label + " h0hashformat", isinstance(h,str) and len(h)==64 and all(c in "0123456789abcdef" for c in h))
            if key in paired_h0:
                check(label + " matchedinitialstate", paired_h0[key] == h)
            else:
                paired_h0[key] = h
            records.append({k: row[k] for k in ("arm","train_seed","eval_seed","article_id")} | metrics)
        result = summarize(records, list(samples))
        check("32 paired initial states", len(paired_h0) == 32)
        check("All saved logits finite", True, {"components": 160*64*32768})
        report["Actual"] = result | {"rows":160,"finite_components":160*64*32768,"saved_metrics":records,"raw_manifest":hashes,
                                     "data_input": info(data_path), "evaluation_manifest":info(worker / "public" / "evaluation.json")}
        report["Status"] = "PASS"
    except BaseException as e:
        report["Status"] = "FAIL"
        report["error"] = {"type":type(e).__name__,"message":str(e),"traceback":traceback.format_exc()}
    report["check_counts"] = {s:sum(r["Status"] == s for r in report["checks"]) for s in ("PASS","FAIL")}
    save(args.output, report)
    print(json.dumps({"Status":report["Status"],"checks":report["check_counts"],"scientific_screens":report["Actual"].get("scientific_screens"),"error":report.get("error")},allow_nan=False))
    return 0 if report["Status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
