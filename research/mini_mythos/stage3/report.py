#!/usr/bin/env python3
"""Stage 3a decisions and summary. The rules are the frozen ones in README.md.

  python report.py choose RUN...                  # dir with the lowest mean dev NLL over 4 domains (LR choice)
  python report.py gate --runs ROOT --lora LR --moda LR      # dev gate; exit 0 pass, 1 fail, 2 incomplete
  python report.py summarize --runs ROOT --native NATIVE_DIR --stage1 PER_WINDOW_CSV --out OUT.json
                                   [--price-per-hour P --hours H]

Run directories are named <mode>_lr<lr>_s<seed>, mode lora (C-LoRA-r28) or moda (MoDA-P).
"""
import argparse
import json
import math
import re
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "stage2"))
import gpu_common as G  # noqa: E402

DOMAINS = ("books", "c4", "fineweb", "wikitext")
OOD = ("books", "c4", "wikitext")
MARGIN = 0.003
BOOT, BOOT_SEED = 10000, 20261110
NAME = re.compile(r"^(lora|moda)_lr([0-9.e+-]+)_s(\d+)$")


def dev_means(run):
    return json.loads((Path(run) / "summary.json").read_text())["dev_domain_mean_nll"]


def mean_all(run):
    return float(np.mean([dev_means(run)[d] for d in DOMAINS]))


def mean_ood(run):
    return float(np.mean([dev_means(run)[d] for d in OOD]))


def choose(runs):
    done = [r for r in runs if (Path(r) / "summary.json").exists()]
    if not done:
        raise SystemExit("no finished runs to choose from")
    return min(done, key=mean_all)


def run_dir(root, mode, lr, seed):
    for p in Path(root).iterdir():
        m = NAME.match(p.name)
        if m and m.group(1) == mode and float(m.group(2)) == float(lr) and int(m.group(3)) == seed:
            return p
    return None


def finished(p):
    return p is not None and (p / "summary.json").exists()


def gate(root, lora_lr, moda_lr):
    """Dev gate: for both seeds, MoDA's mean dev NLL over the 3 out-of-domain sets is below C-LoRA's."""
    out = {"rule": "both seeds: mean OOD dev NLL (books, c4, wikitext) of MoDA < C-LoRA-r28", "seeds": {}}
    complete = True
    for s in (0, 1):
        m, c = run_dir(root, "moda", moda_lr, s), run_dir(root, "lora", lora_lr, s)
        if not (finished(m) and finished(c)):
            complete = False
            out["seeds"][s] = None
            continue
        om, oc = mean_ood(m), mean_ood(c)
        out["seeds"][s] = {"moda_ood": om, "lora_ood": oc, "moda_minus_lora": om - oc, "pass": om < oc}
    out["complete"] = complete
    out["pass"] = complete and all(v["pass"] for v in out["seeds"].values())
    return out


def window_domains(csv):
    out = {}
    with open(csv, encoding="utf-8") as f:
        f.readline()
        for line in f:
            dom, split, doc = line.split(",")[:3]
            out[doc] = (dom, split)
    return out


def paired(base, other, domains, rng):
    """Per domain: mean over windows of (other - base) replica-mean NLL, with a bootstrap 95% CI."""
    res = {}
    for dom in DOMAINS:
        keys = [k for k, d in domains.items() if d == dom]
        if not keys:
            continue
        d = np.array([np.mean(other[k]) - np.mean(base[k]) for k in keys])
        idx = rng.integers(0, len(d), size=(BOOT, len(d)))
        boots = np.sort(d[idx].mean(1))
        res[dom] = {"windows": len(d), "delta_nll": float(d.mean()),
                    "ci95": [float(boots[int(0.025 * BOOT)]), float(boots[int(0.975 * BOOT) - 1])],
                    "improved": int((d < 0).sum()), "worse": int((d > 0).sum()),
                    "ppl_change_pct": 100 * (math.exp(float(d.mean())) - 1)}
    return res


def verdict(test_m_minus_c, dev_seeds, noise_floor):
    """Frozen criteria 1-4 of README.md. test_m_minus_c: paired() output on the test set (M - C);
    dev_seeds: {seed: moda_ood - lora_ood on dev}; noise_floor: max over arms of |seed1 - seed0| (OOD dev)."""
    ood = [test_m_minus_c[d] for d in OOD]
    c1_hits = [d for d in OOD if test_m_minus_c[d]["delta_nll"] <= -MARGIN and test_m_minus_c[d]["ci95"][1] < 0]
    c2_mean = float(np.mean([v["delta_nll"] for v in ood]))
    c3_worse = [d for d in DOMAINS if d in test_m_minus_c and test_m_minus_c[d]["ci95"][0] > 0
                and test_m_minus_c[d]["delta_nll"] > MARGIN]
    deltas = [dev_seeds[0], dev_seeds[1]]
    c4 = all(x < 0 for x in deltas) and all(abs(x) > noise_floor for x in deltas)
    crit = {"1_two_of_three_ood_improved": {"pass": len(c1_hits) >= 2, "domains": c1_hits},
            "2_mean_ood_delta": {"pass": c2_mean <= -MARGIN, "value": c2_mean},
            "3_no_domain_clearly_worse": {"pass": not c3_worse, "domains": c3_worse},
            "4_beyond_training_noise": {"pass": bool(c4), "dev_deltas": deltas, "noise_floor": noise_floor}}
    return crit, all(v["pass"] for v in crit.values())


def throughput(run):
    with open(Path(run) / "train_log.jsonl", encoding="utf-8") as f:
        rows = [json.loads(x) for x in f]
    tps = [r["tokens_per_s"] for r in rows[5:]] or [r["tokens_per_s"] for r in rows]
    return {"median_train_tokens_per_s": float(np.median(tps)), "first_loss": rows[0]["loss"],
            "final_loss": rows[-1]["loss"], "train_seconds": float(sum(r["seconds"] for r in rows))}


def summarize(args):
    root = Path(args.runs)
    rng = np.random.default_rng(BOOT_SEED)
    native_dir = Path(args.native)
    native_dev = G.read_per_window(native_dir / "native_dev.csv")
    dev_domains = {k: v[0] for k, v in window_domains(native_dir / "native_dev.csv").items()}
    o = {"status": None, "runs": {}, "chosen_lr": {}, "gate": None, "test": None, "criteria": None,
         "depth16_dev": {}, "cost": {}}
    for p in sorted(root.iterdir()):
        m = NAME.match(p.name)
        if not (m and finished(p)):
            continue
        s = json.loads((p / "summary.json").read_text())
        cfg = json.loads((p / "config.json").read_text())
        o["runs"][p.name] = {"mode": m.group(1), "lr": float(m.group(2)), "seed": int(m.group(3)),
                             "trainable_params": cfg["trainable_params"], "tokens": cfg["config"]["tokens"],
                             "peak_memory_gib": s.get("peak_memory_gib"), "dev_domain_mean_nll": s["dev_domain_mean_nll"],
                             "dev_delta_vs_native": paired(native_dev, G.read_per_window(p / "eval_dev.csv"),
                                                           dev_domains, rng),
                             "moda_stats_dev": s.get("moda_stats_dev"), **throughput(p)}
    for mode in ("lora", "moda"):
        sweep = [root / n for n, e in o["runs"].items() if e["mode"] == mode and e["seed"] == 0]
        if sweep:
            best = choose(sweep)
            o["chosen_lr"][mode] = {"lr": o["runs"][best.name]["lr"], "run": best.name,
                                    "rule": "lowest mean dev NLL over the 4 domains, seed 0",
                                    "sweep": {o["runs"][q.name]["lr"]: mean_all(q) for q in sweep}}
    if len(o["chosen_lr"]) == 2:
        L, Mlr = o["chosen_lr"]["lora"]["lr"], o["chosen_lr"]["moda"]["lr"]
        o["gate"] = gate(root, L, Mlr)
        if o["gate"]["complete"]:
            floor = max(abs(mean_ood(run_dir(root, mode, lr, 1)) - mean_ood(run_dir(root, mode, lr, 0)))
                        for mode, lr in (("lora", L), ("moda", Mlr)))
            o["noise_floor_ood_dev"] = floor
        mrun, crun = run_dir(root, "moda", Mlr, 0), run_dir(root, "lora", L, 0)
        if o["gate"]["pass"] and (mrun / "eval_test.csv").exists() and (crun / "eval_test.csv").exists():
            mt, ct = G.read_per_window(mrun / "eval_test.csv"), G.read_per_window(crun / "eval_test.csv")
            s1 = G.read_per_window(args.stage1)
            test_domains = {k: v[0] for k, v in window_domains(mrun / "eval_test.csv").items()}
            o["test"] = {"candidates": {"moda": mrun.name, "lora": crun.name},
                         "moda_minus_lora": paired(ct, mt, test_domains, rng),
                         "moda_minus_native": paired(s1, mt, test_domains, rng),
                         "lora_minus_native": paired(s1, ct, test_domains, rng),
                         "native_reference": "Stage 1 r1 CPU per-window scores (GPU agrees to ~1e-6)"}
            dev_seeds = {s: o["gate"]["seeds"][s]["moda_minus_lora"] for s in (0, 1)}
            o["criteria"], ok = verdict(o["test"]["moda_minus_lora"], dev_seeds, o["noise_floor_ood_dev"])
            o["status"] = "PASS" if ok else "FAIL"
            stats = mrun / "eval_test.json"
            if stats.exists():
                o["test"]["moda_stats_test"] = json.loads(stats.read_text()).get("moda_stats")
        elif o["gate"]["complete"] and not o["gate"]["pass"]:
            o["status"] = "FAIL (dev gate; test set not used)"
        else:
            o["status"] = "NOT TESTED (runs or test evaluations incomplete)"
        for label, path in (("native", native_dir / "native_dev_d16.csv"), ("moda", mrun / "eval_dev_d16.csv"),
                            ("lora", crun / "eval_dev_d16.csv")):
            if path.exists():
                o["depth16_dev"][label] = json.loads(path.with_suffix(".json").read_text())["domain_mean_nll"]
    else:
        o["status"] = "NOT TESTED (runs incomplete)"
    if getattr(args, "short", None) and Path(args.short).is_dir():   # Stage 3b: LR search on short runs
        o["short_lr_search"] = {}
        for mode in ("lora", "moda"):
            sw = [q for q in Path(args.short).iterdir() if NAME.match(q.name) and NAME.match(q.name).group(1) == mode
                  and int(NAME.match(q.name).group(3)) == 0 and finished(q)]
            if sw:
                o["short_lr_search"][mode] = {"chosen": choose(sw).name,
                                              "sweep": {float(NAME.match(q.name).group(2)): mean_all(q) for q in sw}}
    o["title"] = getattr(args, "title", None) or "Stage 3a (MoDA-P) summary"
    if args.price_per_hour and args.hours:
        o["cost"] = {"price_per_hour": args.price_per_hour, "wall_hours": args.hours,
                     "usd": args.price_per_hour * args.hours}
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(o, indent=1) + "\n")
    Path(args.out).with_suffix(".md").write_text(render(o) + "\n", encoding="utf-8")
    print(render(o))
    return 0


def cell(v):
    return "%+.4f [%+.4f,%+.4f]" % (v["delta_nll"], v["ci95"][0], v["ci95"][1]) if v else "-"


def render(o):
    L = ["# " + o.get("title", "Stage 3a (MoDA-P) summary"), "", "**Status: %s**" % o["status"], ""]
    for mode, c in o.get("short_lr_search", {}).items():
        L.append("- %s short-run LR search (base-weight LR -> mean dev NLL): %s; chosen %s" % (
            mode, ", ".join("%g -> %.4f" % (k, v) for k, v in sorted(c["sweep"].items())), c["chosen"]))
    for mode, c in o["chosen_lr"].items():
        L.append("- %s: chosen LR %g (sweep mean dev NLL: %s)" % (mode, c["lr"], ", ".join(
            "%g -> %.4f" % (k, v) for k, v in sorted(c["sweep"].items()))))
    L += ["", "Dev, change vs native (nats/token, mean [95% CI]):", "",
          "| run | trainable | tok/s | loss first->last | " + " | ".join(DOMAINS) + " |",
          "|---|---:|---:|---|" + "---:|" * len(DOMAINS)]
    for n, e in o["runs"].items():
        L.append("| %s | %d | %.0f | %.3f->%.3f | %s |" % (n, e["trainable_params"], e["median_train_tokens_per_s"],
                 e["first_loss"], e["final_loss"], " | ".join(cell(e["dev_delta_vs_native"].get(d)) for d in DOMAINS)))
    if o["gate"]:
        L += ["", "Dev gate (%s): %s" % (o["gate"]["rule"], "PASS" if o["gate"]["pass"] else "not passed")]
        for s, v in o["gate"]["seeds"].items():
            L.append("- seed %s: %s" % (s, "incomplete" if v is None else "MoDA %.4f vs C-LoRA %.4f (diff %+.4f)" % (
                v["moda_ood"], v["lora_ood"], v["moda_minus_lora"])))
        if "noise_floor_ood_dev" in o:
            L.append("- training noise floor (max over arms of |seed1-seed0|, OOD dev mean): %.4f" % o["noise_floor_ood_dev"])
    if o["test"]:
        L += ["", "Test set (%s vs %s), mean [95%% CI]:" % (o["test"]["candidates"]["moda"], o["test"]["candidates"]["lora"]),
              "", "| comparison | " + " | ".join(DOMAINS) + " |", "|---|" + "---:|" * len(DOMAINS)]
        for k in ("moda_minus_lora", "moda_minus_native", "lora_minus_native"):
            L.append("| %s | %s |" % (k, " | ".join(cell(o["test"][k].get(d)) for d in DOMAINS)))
    if o["criteria"]:
        L += ["", "Criteria:"] + ["- %s: %s %s" % (k, "PASS" if v["pass"] else "FAIL",
                                                   json.dumps({a: b for a, b in v.items() if a != "pass"}))
                                  for k, v in o["criteria"].items()]
    if o["depth16_dev"]:
        L += ["", "Depth 16, dev domain mean NLL (report only): " + json.dumps(o["depth16_dev"])]
    if o["cost"]:
        L += ["", "Cost: %s" % json.dumps(o["cost"])]
    return "\n".join(L)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("choose")
    c.add_argument("runs", nargs="+")
    g = sub.add_parser("gate")
    g.add_argument("--runs", required=True)
    g.add_argument("--lora", required=True)
    g.add_argument("--moda", required=True)
    s = sub.add_parser("summarize")
    s.add_argument("--runs", required=True)
    s.add_argument("--native", required=True)
    s.add_argument("--stage1", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--price-per-hour", type=float, default=0)
    s.add_argument("--hours", type=float, default=0)
    s.add_argument("--title", default=None)
    s.add_argument("--short", default=None, help="directory of short LR-search runs (Stage 3b)")
    args = p.parse_args()
    if args.cmd == "choose":
        print(choose(args.runs))
        return 0
    if args.cmd == "gate":
        r = gate(args.runs, args.lora, args.moda)
        print(json.dumps(r, indent=1))
        return 0 if r["pass"] else (1 if r["complete"] else 2)
    return summarize(args)


if __name__ == "__main__":
    sys.exit(main())
