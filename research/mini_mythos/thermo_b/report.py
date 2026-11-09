#!/usr/bin/env python3
"""Thermo-B decisions and summary. The rules are the frozen ones in README.md.

  python report.py choose RUN...                       # lowest mean dev NLL over the 4 domains (LR choice)
  python report.py gate --runs ROOT --full LR --expand LR   # dev gate; exit 0 pass, 1 fail, 2 incomplete
  python report.py summarize --runs ROOT --native NATIVE_DIR --stage1 PER_WINDOW_CSV --out OUT.json
                                [--price-per-hour P --hours H]

Run directories are named <arm>_lr<lr>_s<seed>, arm full (C), expand (E) or thermo (T). T uses the
learning rate chosen for E. The candidate for the test set is whichever of E and T has the lower
out-of-domain dev NLL averaged over seeds 0 and 1 (ties go to E).
"""
import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "stage2"))
import gpu_common as G  # noqa: E402

_spec = importlib.util.spec_from_file_location("stage3_report", HERE.parent / "stage3" / "report.py")
R3 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(R3)

DOMAINS, OOD = R3.DOMAINS, R3.OOD
NAME = re.compile(r"^(full|expand|thermo)_lr([0-9.e+-]+)_s(\d+)$")
LABEL = {"full": "C (rank 28 from the start)", "expand": "E (rank 1->28)", "thermo": "T (rank 1->28 + temperature)"}


def summary(run):
    return json.loads((Path(run) / "summary.json").read_text())


def mean_all(run):
    m = summary(run)["dev_domain_mean_nll"]
    return float(np.mean([m[d] for d in DOMAINS]))


def mean_ood(run):
    m = summary(run)["dev_domain_mean_nll"]
    return float(np.mean([m[d] for d in OOD]))


def finished(p):
    return p is not None and (Path(p) / "summary.json").exists()


def choose(runs):
    done = [r for r in runs if finished(r)]
    if not done:
        raise SystemExit("no finished runs to choose from")
    return min(done, key=mean_all)


def run_dir(root, arm, lr, seed):
    root = Path(root)
    if not root.is_dir():
        return None
    for p in root.iterdir():
        m = NAME.match(p.name)
        if m and m.group(1) == arm and float(m.group(2)) == float(lr) and int(m.group(3)) == seed:
            return p
    return None


def main_runs(root, full_lr, expand_lr):
    lrs = {"full": full_lr, "expand": expand_lr, "thermo": expand_lr}
    return {(a, s): run_dir(root, a, lrs[a], s) for a in lrs for s in (0, 1)}


def gate(root, full_lr, expand_lr):
    """Candidate X = E or T (lower OOD dev NLL averaged over both seeds). Gate: for both seeds,
    X's mean OOD dev NLL is below C's."""
    runs = main_runs(root, full_lr, expand_lr)
    out = {"rule": "candidate X = argmin over {expand, thermo} of the seed-averaged OOD dev NLL; "
                   "pass if for both seeds OOD dev NLL of X < C", "complete": all(finished(p) for p in runs.values()),
           "pass": False}
    if not out["complete"]:
        out["missing"] = ["%s_s%d" % k for k, p in runs.items() if not finished(p)]
        return out
    ood = {k: mean_ood(p) for k, p in runs.items()}
    avg = {a: 0.5 * (ood[(a, 0)] + ood[(a, 1)]) for a in ("full", "expand", "thermo")}
    cand = "thermo" if avg["thermo"] < avg["expand"] else "expand"
    out.update(candidate_arm=cand, candidate_run=runs[(cand, 0)].name, control_run=runs[("full", 0)].name,
               seed_avg_ood=avg, seeds={})
    for s in (0, 1):
        x, c = ood[(cand, s)], ood[("full", s)]
        out["seeds"][s] = {"candidate_ood": x, "full_ood": c, "candidate_minus_full": x - c, "pass": x < c}
    out["pass"] = all(v["pass"] for v in out["seeds"].values())
    out["noise_floor_ood_dev"] = max(abs(ood[(a, 1)] - ood[(a, 0)]) for a in ("full", "expand", "thermo"))
    out["hypotheses_dev_ood"] = {
        "H1_expand_minus_full": {s: ood[("expand", s)] - ood[("full", s)] for s in (0, 1)},
        "H2_thermo_minus_expand": {s: ood[("thermo", s)] - ood[("expand", s)] for s in (0, 1)},
        "thermo_minus_full": {s: ood[("thermo", s)] - ood[("full", s)] for s in (0, 1)}}
    return out


def read_curve(run):
    p = Path(run) / "curve.jsonl"
    if not p.exists():
        return []
    with open(p, encoding="utf-8") as f:
        rows = [json.loads(x) for x in f if x.strip()]
    return sorted({r["step"]: r for r in rows}.values(), key=lambda r: r["step"])


def curve_ood(rows):
    return [(r["tokens"], float(np.mean([r["dev_rep0_domain_mean_nll"][d] for d in OOD]))) for r in rows]


def tokens_to_reach(points, target):
    """First token count at which the (linearly interpolated) curve reaches `target`; None if never."""
    for (t0, v0), (t1, v1) in zip(points, points[1:]):
        if v0 <= target:
            return float(t0)
        if v1 <= target:
            return float(t0 + (t1 - t0) * (v0 - target) / (v0 - v1))
    if points and points[-1][1] <= target:
        return float(points[-1][0])
    return None


def geometry_rows(rows):
    out = []
    for r in rows:
        g = r.get("geometry", {})
        tok, win, ad = g.get("pooled", {}).get("tokens", {}), g.get("pooled", {}).get("windows", {}), g.get("adapter", {})
        out.append({"step": r["step"], "tokens": r["tokens"], "rank": r["rank"], "pr_dh_tokens": tok.get("pr_dh"),
                    "twonn_dh_tokens": tok.get("twonn_dh"), "pr_dh_windows": win.get("pr_dh"),
                    "twonn_dh_windows": win.get("twonn_dh"), "dh_rms": tok.get("dh_rms"),
                    "adapter_effective_rank_mean": ad.get("effective_rank_mean")})
    return out


def summarize(args):
    root = Path(args.runs)
    rng = np.random.default_rng(R3.BOOT_SEED)
    native_dir = Path(args.native)
    native_dev = G.read_per_window(native_dir / "native_dev.csv")
    dev_domains = {k: v[0] for k, v in R3.window_domains(native_dir / "native_dev.csv").items()}
    o = {"title": "Thermo-B (rank expansion on Parcae-140M, LoRA r28, base frozen) summary", "status": None,
         "runs": {}, "chosen_lr": {}, "gate": None, "test": None, "criteria": None, "curves": {},
         "efficiency": None, "geometry": {}, "data_dimension": None, "cost": {}}
    for p in sorted(root.iterdir()) if root.is_dir() else []:
        m = NAME.match(p.name)
        if not (m and finished(p)):
            continue
        s, cfg = summary(p), json.loads((p / "config.json").read_text())
        run_dev = G.read_per_window(p / "eval_dev.csv")             # may be a subset (CPU runs)
        run_domains = {k: v for k, v in dev_domains.items() if k in run_dev}
        o["runs"][p.name] = {"arm": m.group(1), "lr": float(m.group(2)), "seed": int(m.group(3)),
                             "trainable_params": cfg["trainable_params"], "tokens": cfg["config"]["tokens"],
                             "peak_memory_gib": s.get("peak_memory_gib"), "dev_domain_mean_nll": s["dev_domain_mean_nll"],
                             "dev_windows": len(run_dev),
                             "dev_delta_vs_native": R3.paired(native_dev, run_dev, run_domains, rng), **R3.throughput(p)}
    for arm in ("full", "expand"):
        sweep = [root / n for n, e in o["runs"].items() if e["arm"] == arm and e["seed"] == 0]
        if sweep:
            best = choose(sweep)
            o["chosen_lr"][arm] = {"lr": o["runs"][best.name]["lr"], "run": best.name,
                                   "rule": "lowest mean dev NLL over the 4 domains, seed 0",
                                   "sweep": {o["runs"][q.name]["lr"]: mean_all(q) for q in sweep}}
    if len(o["chosen_lr"]) == 2:
        fl, el = o["chosen_lr"]["full"]["lr"], o["chosen_lr"]["expand"]["lr"]
        o["gate"] = gate(root, fl, el)
        runs = main_runs(root, fl, el)
        for (arm, seed), p in runs.items():
            if seed == 0 and p is not None:
                rows = read_curve(p)
                o["curves"][arm] = curve_ood(rows)
                o["geometry"][arm] = geometry_rows(rows)
                if o["data_dimension"] is None and rows and rows[0]["step"] == 0:
                    doms = rows[0]["geometry"]["domains"]
                    o["data_dimension"] = {d: {"twonn_windows": v["windows"]["twonn_h"],
                                               "pr_windows": v["windows"]["pr_h"],
                                               "twonn_tokens": v["tokens"]["twonn_h"], "pr_tokens": v["tokens"]["pr_h"]}
                                           for d, v in doms.items()}
        if o["gate"]["complete"]:
            cand = o["gate"]["candidate_arm"]
            if "full" in o["curves"] and cand in o["curves"] and o["curves"]["full"] and o["curves"][cand]:
                c_final, x_final = o["curves"]["full"][-1], o["curves"][cand][-1]
                tx = tokens_to_reach(o["curves"][cand], c_final[1])
                tc = tokens_to_reach(o["curves"]["full"], x_final[1])
                o["efficiency"] = {"rule": "report only; OOD dev mean, replica 0, linear interpolation",
                                   "candidate_tokens_to_reach_C_final": tx, "C_tokens_to_reach_candidate_final": tc,
                                   "candidate_over_C_tokens": (tx / c_final[0]) if tx is not None else None}
            xrun, crun = root / o["gate"]["candidate_run"], root / o["gate"]["control_run"]
            if o["gate"]["pass"] and (xrun / "eval_test.csv").exists() and (crun / "eval_test.csv").exists():
                xt, ct = G.read_per_window(xrun / "eval_test.csv"), G.read_per_window(crun / "eval_test.csv")
                s1 = G.read_per_window(args.stage1)
                test_domains = {k: v[0] for k, v in R3.window_domains(xrun / "eval_test.csv").items()}
                o["test"] = {"candidates": {"candidate": xrun.name, "full": crun.name},
                             "candidate_minus_full": R3.paired(ct, xt, test_domains, rng),
                             "candidate_minus_native": R3.paired(s1, xt, test_domains, rng),
                             "full_minus_native": R3.paired(s1, ct, test_domains, rng),
                             "native_reference": "Stage 1 r1 CPU per-window scores (GPU agrees to ~1e-6)"}
                dev_seeds = {s: o["gate"]["seeds"][s]["candidate_minus_full"] for s in (0, 1)}
                o["criteria"], ok = R3.verdict(o["test"]["candidate_minus_full"], dev_seeds,
                                               o["gate"]["noise_floor_ood_dev"])
                o["status"] = "PASS" if ok else "FAIL"
            elif not o["gate"]["pass"]:
                o["status"] = "FAIL (dev gate; test set not used)"
            else:
                o["status"] = "NOT TESTED (test evaluations missing)"
        else:
            o["status"] = "NOT TESTED (runs incomplete)"
    else:
        o["status"] = "NOT TESTED (runs incomplete)"
    if args.price_per_hour and args.hours:
        o["cost"] = {"price_per_hour": args.price_per_hour, "wall_hours": args.hours,
                     "usd": args.price_per_hour * args.hours}
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(o, indent=1) + "\n")
    Path(args.out).with_suffix(".md").write_text(render(o) + "\n", encoding="utf-8")
    print(render(o))
    return 0


def fmt(v, spec="%.3f"):
    return "-" if v is None else spec % v


def render(o):
    cell = R3.cell
    L = ["# " + o["title"], "", "**Status: %s**" % o["status"], ""]
    for arm, c in o["chosen_lr"].items():
        L.append("- %s: chosen LR %g (sweep mean dev NLL: %s)" % (LABEL[arm], c["lr"], ", ".join(
            "%g -> %.4f" % (k, v) for k, v in sorted(c["sweep"].items()))))
    L += ["", "Dev, change vs native (nats/token, mean [95% CI]):", "",
          "| run | trainable | tok/s | loss first->last | " + " | ".join(DOMAINS) + " |",
          "|---|---:|---:|---|" + "---:|" * len(DOMAINS)]
    for n, e in o["runs"].items():
        L.append("| %s | %d | %.0f | %.3f->%.3f | %s |" % (n, e["trainable_params"], e["median_train_tokens_per_s"],
                 e["first_loss"], e["final_loss"], " | ".join(cell(e["dev_delta_vs_native"].get(d)) for d in DOMAINS)))
    g = o["gate"]
    if g:
        L += ["", "Dev gate (%s): %s" % (g["rule"], "PASS" if g["pass"] else ("not passed" if g["complete"] else "incomplete"))]
        if g["complete"]:
            L.append("- candidate: %s (seed-averaged OOD dev NLL: %s)" % (
                LABEL[g["candidate_arm"]], ", ".join("%s %.4f" % kv for kv in g["seed_avg_ood"].items())))
            for s, v in g["seeds"].items():
                L.append("- seed %s: candidate %.4f vs C %.4f (diff %+.4f)" % (
                    s, v["candidate_ood"], v["full_ood"], v["candidate_minus_full"]))
            L.append("- training noise floor (max over arms of |seed1-seed0|, OOD dev mean): %.4f" % g["noise_floor_ood_dev"])
            L += ["", "Hypotheses on dev (OOD mean, report only):"]
            for k, v in g["hypotheses_dev_ood"].items():
                L.append("- %s: seed 0 %+.4f, seed 1 %+.4f" % (k, v[0], v[1]))
        else:
            L.append("- missing: %s" % ", ".join(g.get("missing", [])))
    if o["test"]:
        L += ["", "Test set (%s vs %s), mean [95%% CI]:" % (o["test"]["candidates"]["candidate"],
                                                           o["test"]["candidates"]["full"]),
              "", "| comparison | " + " | ".join(DOMAINS) + " |", "|---|" + "---:|" * len(DOMAINS)]
        for k in ("candidate_minus_full", "candidate_minus_native", "full_minus_native"):
            L.append("| %s | %s |" % (k, " | ".join(cell(o["test"][k].get(d)) for d in DOMAINS)))
    if o["criteria"]:
        L += ["", "Criteria:"] + ["- %s: %s %s" % (k, "PASS" if v["pass"] else "FAIL",
                                                   json.dumps({a: b for a, b in v.items() if a != "pass"}))
                                  for k, v in o["criteria"].items()]
    if o["curves"]:
        L += ["", "Learning curves (OOD dev mean NLL, replica 0; seed 0 of the chosen LR):", "",
              "| arm | " + " | ".join("%.1fM" % (t / 1e6) for t, _ in next(iter(o["curves"].values()))) + " |",
              "|---|" + "---:|" * len(next(iter(o["curves"].values())))]
        for arm, pts in o["curves"].items():
            L.append("| %s | %s |" % (arm, " | ".join("%.4f" % v for _, v in pts)))
    if o["efficiency"]:
        L += ["", "Efficiency (report only): %s" % json.dumps(o["efficiency"])]
    if o["geometry"]:
        L += ["", "Geometry of the change dh = h - h_native (report only; seed 0). Columns: tokens, active rank, "
              "PR(dh) token level, TwoNN(dh) token level, PR(dh) window means, TwoNN(dh) window means, rms(dh), "
              "mean effective rank of the adapter updates", ""]
        for arm, rows in o["geometry"].items():
            L += ["%s:" % LABEL[arm], "", "| tokens | rank | PR tok | TwoNN tok | PR win | TwoNN win | rms | adapter erank |",
                  "|---:|---:|---:|---:|---:|---:|---:|---:|"]
            for r in rows:
                L.append("| %.1fM | %d | %s | %s | %s | %s | %s | %s |" % (
                    r["tokens"] / 1e6, r["rank"], fmt(r["pr_dh_tokens"], "%.2f"), fmt(r["twonn_dh_tokens"], "%.2f"),
                    fmt(r["pr_dh_windows"], "%.2f"), fmt(r["twonn_dh_windows"], "%.2f"), fmt(r["dh_rms"], "%.4f"),
                    fmt(r["adapter_effective_rank_mean"], "%.2f")))
            L.append("")
    if o["data_dimension"]:
        L += ["", "Data dimension per domain, as Parcae sees it (native final hidden states; report only): " + ", ".join(
            "%s TwoNN %s / PR %s (window means), TwoNN %s / PR %s (tokens)" % (
                d, fmt(v["twonn_windows"], "%.1f"), fmt(v["pr_windows"], "%.1f"), fmt(v["twonn_tokens"], "%.1f"),
                fmt(v["pr_tokens"], "%.1f")) for d, v in o["data_dimension"].items())]
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
    g.add_argument("--full", required=True)
    g.add_argument("--expand", required=True)
    s = sub.add_parser("summarize")
    s.add_argument("--runs", required=True)
    s.add_argument("--native", required=True)
    s.add_argument("--stage1", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--price-per-hour", type=float, default=0)
    s.add_argument("--hours", type=float, default=0)
    args = p.parse_args()
    if args.cmd == "choose":
        print(choose(args.runs))
        return 0
    if args.cmd == "gate":
        r = gate(args.runs, args.full, args.expand)
        print(json.dumps(r, indent=1))
        return 0 if r["pass"] else (1 if r["complete"] else 2)
    return summarize(args)


if __name__ == "__main__":
    sys.exit(main())
