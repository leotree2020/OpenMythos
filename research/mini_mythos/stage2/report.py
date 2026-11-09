#!/usr/bin/env python3
"""Stage 2 aggregation (numpy + torch only for the resume comparison).

  python report.py choose RUN_DIR...          # prints the dir with the lowest mean dev NLL (LR choice)
  python report.py summarize --native NATIVE_DIR --runs RUNS_ROOT --out OUT [--price-per-hour P --hours H]

Run directories are named <mode>_lr<lr>_s<seed> (resume test: <...>_resume).
"""
import argparse
import json
import math
import re
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gpu_common as G  # noqa: E402

BOOT, BOOT_SEED = 10000, 20261109
NAME = re.compile(r"^(lora|full)_lr([0-9.e+-]+)_s(\d+)(_resume)?$")


def mean_dev(run):
    d = json.loads((Path(run) / "summary.json").read_text())["dev_domain_mean_nll"]
    return float(np.mean(list(d.values())))


def choose(runs):
    done = [r for r in runs if (Path(r) / "summary.json").exists()]
    if not done:
        raise SystemExit("no finished runs to choose from")
    return min(done, key=mean_dev)


def window_domains(csv):
    out = {}
    with open(csv, encoding="utf-8") as f:
        f.readline()
        for line in f:
            dom, _, doc = line.split(",")[:3]
            out[doc] = dom
    return out


def paired(native, run, domains, rng):
    """Per domain: mean over windows of (run - native) replica-mean NLL, bootstrap CI."""
    res = {}
    for dom in sorted(set(domains.values())):
        keys = [k for k, d in domains.items() if d == dom]
        d = np.array([np.mean(run[k]) - np.mean(native[k]) for k in keys])
        idx = rng.integers(0, len(d), size=(BOOT, len(d)))
        boots = np.sort(d[idx].mean(1))
        res[dom] = {"windows": len(d), "delta_nll": float(d.mean()),
                    "ci95": [float(boots[int(0.025 * BOOT)]), float(boots[int(0.975 * BOOT) - 1])],
                    "improved": int((d < 0).sum()), "worse": int((d > 0).sum()),
                    "ppl_change_pct": 100 * (math.exp(float(d.mean())) - 1)}
    return res


def throughput(run):
    with open(Path(run) / "train_log.jsonl", encoding="utf-8") as f:
        rows = [json.loads(x) for x in f]
    tps = [r["tokens_per_s"] for r in rows[5:]] or [r["tokens_per_s"] for r in rows]
    return {"median_train_tokens_per_s": float(np.median(tps)), "final_loss": rows[-1]["loss"],
            "first_loss": rows[0]["loss"], "train_seconds": float(sum(r["seconds"] for r in rows))}


def compare_params(a, b):
    import torch
    pa = torch.load(Path(a) / "final_params.pt", map_location="cpu", weights_only=True)
    pb = torch.load(Path(b) / "final_params.pt", map_location="cpu", weights_only=True)
    same = pa.keys() == pb.keys() and all(torch.equal(pa[k], pb[k]) for k in pa)
    diff = max(float((pa[k] - pb[k]).abs().max()) for k in pa) if pa.keys() == pb.keys() else None
    return {"bitwise_equal": bool(same), "max_abs_param_diff": diff}


def summarize(args):
    native = G.read_per_window(Path(args.native) / "native_dev.csv")
    domains = window_domains(Path(args.native) / "native_dev.csv")
    rng = np.random.default_rng(BOOT_SEED)
    runs = sorted(p for p in Path(args.runs).iterdir() if p.is_dir() and NAME.match(p.name)
                  and (p / "summary.json").exists())
    out = {"native_dev_domain_mean_nll": None, "runs": {}, "chosen_lr": {}, "training_noise_floor": {},
           "resume": {}, "cost": {}}
    agreement = Path(args.native) / "agreement.json"
    if agreement.exists():
        a = json.loads(agreement.read_text())
        out["agreement"] = {"pass": a["pass"], "all": a["all"], "bf16_minus_fp32": a["bf16_minus_fp32"],
                            "eval_tokens_per_s_fp32": a["eval_tokens_per_s_fp32"], "device": a["device"]}
        out["native_dev_domain_mean_nll"] = a["native_dev_domain_mean_nll"]
    for r in runs:
        m = NAME.match(r.name)
        s = json.loads((r / "summary.json").read_text())
        cfg = json.loads((r / "config.json").read_text())
        entry = {"mode": m.group(1), "lr": float(m.group(2)), "seed": int(m.group(3)), "resume_test": bool(m.group(4)),
                 "trainable_params": cfg["trainable_params"], "peak_memory_gib": s.get("peak_memory_gib"),
                 "delta_vs_native": paired(native, G.read_per_window(r / "eval_dev.csv"), domains, rng),
                 **throughput(r)}
        out["runs"][r.name] = entry
    for mode in ("lora", "full"):
        sweep = [Path(args.runs) / n for n, e in out["runs"].items()
                 if e["mode"] == mode and e["seed"] == 0 and not e["resume_test"]]
        if not sweep:
            continue
        best = choose(sweep)
        lr = out["runs"][best.name]["lr"]
        out["chosen_lr"][mode] = {"lr": lr, "rule": "lowest mean dev NLL over the 4 domains, seed 0",
                                  "sweep": {out["runs"][p.name]["lr"]: mean_dev(p) for p in sweep}}
        s1 = [n for n, e in out["runs"].items() if e["mode"] == mode and e["lr"] == lr and e["seed"] == 1]
        if s1:
            a = G.read_per_window(best / "eval_dev.csv")
            b = G.read_per_window(Path(args.runs) / s1[0] / "eval_dev.csv")
            floor = {}
            for dom in sorted(set(domains.values())):
                keys = [k for k, d in domains.items() if d == dom]
                da = np.mean([np.mean(a[k]) for k in keys])
                db = np.mean([np.mean(b[k]) for k in keys])
                floor[dom] = abs(float(db - da))
            out["training_noise_floor"][mode] = {"seed1_minus_seed0_abs_domain_mean": floor,
                                                 "note": "two seeds give one difference per domain; a rough floor"}
        res = [n for n, e in out["runs"].items() if e["mode"] == mode and e["resume_test"]]
        for n in res:
            ref = Path(args.runs) / n.replace("_resume", "")
            if (ref / "final_params.pt").exists():
                c = compare_params(ref, Path(args.runs) / n)
                dev_a, dev_b = mean_dev(ref), mean_dev(Path(args.runs) / n)
                c["dev_mean_nll_diff"] = abs(dev_a - dev_b)
                out["resume"][n] = c
    if args.price_per_hour and args.hours:
        out["cost"] = {"price_per_hour": args.price_per_hour, "wall_hours": args.hours,
                       "usd": args.price_per_hour * args.hours}
        tps = [e["median_train_tokens_per_s"] for e in out["runs"].values() if e["mode"] == "lora"]
        if tps:
            out["cost"]["usd_per_10M_train_tokens_lora"] = args.price_per_hour * 1e7 / float(np.median(tps)) / 3600
        tps = [e["median_train_tokens_per_s"] for e in out["runs"].values() if e["mode"] == "full"]
        if tps:
            out["cost"]["usd_per_10M_train_tokens_full"] = args.price_per_hour * 1e7 / float(np.median(tps)) / 3600
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=1) + "\n")
    Path(args.out).with_suffix(".md").write_text(render(out) + "\n", encoding="utf-8")
    print(render(out))
    return 0


def render(o):
    L = ["# Stage 2 summary", ""]
    if "agreement" in o:
        a = o["agreement"]
        L += ["GPU/CPU agreement (%s): %s; mean |diff| %.2e, max |diff| %.2e. FP32 eval %.0f tokens/s." % (
            a["device"], "PASS" if a["pass"] else "FAIL", a["all"]["mean_abs"], a["all"]["max_abs"],
            a["eval_tokens_per_s_fp32"]), ""]
    for mode, c in o["chosen_lr"].items():
        L.append("- %s: chosen LR %g (sweep mean dev NLL: %s)" % (mode, c["lr"],
                 ", ".join("%g -> %.4f" % (k, v) for k, v in sorted(c["sweep"].items()))))
    L += ["", "| run | trainable | tok/s | loss first->last | " + " | ".join(
        "%s dNLL" % d for d in ("books", "c4", "fineweb", "wikitext")) + " |", "|---|---:|---:|---|---:|---:|---:|---:|"]
    for n, e in o["runs"].items():
        cells = []
        for d in ("books", "c4", "fineweb", "wikitext"):
            v = e["delta_vs_native"].get(d)
            cells.append("%+.4f [%+.4f,%+.4f]" % (v["delta_nll"], v["ci95"][0], v["ci95"][1]) if v else "-")
        L.append("| %s | %d | %.0f | %.3f->%.3f | %s |" % (n, e["trainable_params"], e["median_train_tokens_per_s"],
                                                           e["first_loss"], e["final_loss"], " | ".join(cells)))
    for mode, f in o["training_noise_floor"].items():
        L.append("")
        L.append("Training noise floor %s (|seed1-seed0| of domain mean): %s" % (mode, ", ".join(
            "%s %.4f" % (d, v) for d, v in f["seed1_minus_seed0_abs_domain_mean"].items())))
    for n, c in o["resume"].items():
        L.append("Resume %s: bitwise %s, max param diff %s, dev diff %.2e" % (
            n, c["bitwise_equal"], c["max_abs_param_diff"], c["dev_mean_nll_diff"]))
    if o["cost"]:
        L += ["", "Cost: %s" % json.dumps(o["cost"])]
    return "\n".join(L)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("choose")
    c.add_argument("runs", nargs="+")
    s = sub.add_parser("summarize")
    s.add_argument("--native", required=True)
    s.add_argument("--runs", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--price-per-hour", type=float, default=0)
    s.add_argument("--hours", type=float, default=0)
    args = p.parse_args()
    if args.cmd == "choose":
        print(choose(args.runs))
        return 0
    return summarize(args)


if __name__ == "__main__":
    sys.exit(main())
