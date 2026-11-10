#!/usr/bin/env python3
"""Parcae closing experiment (README.md): does the growing knowledge space add anything?

  python -B closing.py --set A RUNS_A --set B RUNS_B [--out OUT.md]

Each RUNS dir holds the five runs of one book set: U_none, U_auto, F_auto, F_static, F_sched.
Prints the table and the verdict by the criteria fixed in README.md before the runs.
"""
import argparse
import json
import math
import sys
from pathlib import Path

ARMS = ("U_none", "U_auto", "F_auto", "F_static", "F_sched")
LABEL = {"U_none": "unfrozen, no knowledge space", "U_auto": "unfrozen, grows by surprise",
         "F_auto": "frozen, grows by surprise", "F_static": "frozen, all directions from the start (random)",
         "F_sched": "frozen, grows on a schedule"}
MARGIN = 0.010          # nats: what counts as better (README.md)
FORGET_TOL = 0.005      # nats: how much more general forgetting is tolerated


def load(run):
    run = Path(run)
    if not (run / "summary.json").exists():
        return None
    s = json.loads((run / "summary.json").read_text())
    ev = [json.loads(x) for x in open(run / "evals.jsonl", encoding="utf-8") if x.strip()]

    def forget(e):
        return sum(e["domains"][d] for d in ("c4", "wikitext", "fineweb")) / 3
    by = {e["books_read"]: forget(e) for e in ev}
    first = min(b for b in by if b > 0)
    last = max(by)
    return {"k": s["k_final"], "heldout_gain": -s["final_check"]["heldout_books"],
            "specific_immediate": s.get("specific_gain_immediate"), "specific_retained": s.get("specific_gain_retained"),
            "specific_retention": s.get("specific_retention"), "forgetting": s["forgetting_nats"],
            "forgetting_slope_per_10_books": 10 * (by[last] - by[first]) / (last - first) if last > first else None,
            "prequential": s["prequential_gain_all"],
            "model_only_diverged_chunks": s.get("read_chunks_model_only_diverged"),
            "final_diverged_windows": len(s.get("final_diverged_windows") or []),
            "native_diverged_windows": len(s.get("native_diverged_windows") or [])}


def better(a, b):
    """a beats b: more specific retained OR more gain on never-read books by MARGIN, without forgetting
    more than FORGET_TOL beyond b."""
    ds = a["specific_retained"] - b["specific_retained"]
    dh = a["heldout_gain"] - b["heldout_gain"]
    df = a["forgetting"] - b["forgetting"]
    return {"specific_retained_diff": ds, "heldout_gain_diff": dh, "forgetting_diff": df,
            "pass": bool((ds >= MARGIN or dh >= MARGIN) and df <= FORGET_TOL)}


def f(v, spec="%+.4f"):
    return "-" if v is None else spec % v


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--set", nargs=2, action="append", metavar=("NAME", "DIR"), required=True)
    p.add_argument("--out")
    args = p.parse_args()
    sets = {name: {a: load(Path(d) / a) for a in ARMS} for name, d in args.set}
    L = ["# Parcae closing experiment: does the growing knowledge space add anything?", "",
         "All runs: anchor 3, stability guard 1.5, 20 books x 16k tokens, one pass, CPU. Gains are native minus",
         "model (nats/token, positive = better); forgetting is the mean NLL increase on c4 / wikitext / fineweb.", ""]
    for name, runs in sets.items():
        L += ["## Book set %s" % name, "",
              "| arm | k | never-read books gain | specific: immediate | specific: retained | retention | "
              "forgetting (ppl) | forgetting slope / 10 books | prequential | model-only diverged chunks | "
              "diverged windows at end (native) |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for a in ARMS:
            r = runs[a]
            if r is None:
                L.append("| %s | not run | | | | | | | | | |" % LABEL[a])
                continue
            L.append("| %s | %d | %s | %s | %s | %s | %s (%+.1f%%) | %s | %s | %s | %d (%d) |" % (
                LABEL[a], r["k"], f(r["heldout_gain"]), f(r["specific_immediate"]), f(r["specific_retained"]),
                "-" if r["specific_retention"] is None else "%.0f%%" % (100 * r["specific_retention"]),
                f(r["forgetting"]), 100 * (math.exp(r["forgetting"]) - 1), f(r["forgetting_slope_per_10_books"]),
                f(r["prequential"]), r["model_only_diverged_chunks"], r["final_diverged_windows"],
                r["native_diverged_windows"]))
        L.append("")
    verdict = {}
    for key, (a, b) in (("1 unfrozen: growth vs no knowledge space", ("U_auto", "U_none")),
                        ("2 frozen: growth vs static random space", ("F_auto", "F_static"))):
        res = {}
        for name, runs in sets.items():
            res[name] = better(runs[a], runs[b]) if runs[a] and runs[b] else None
        verdict[key] = {"sets": res, "pass": all(v is not None and v["pass"] for v in res.values())}
    complete = all(v is not None for c in verdict.values() for v in c["sets"].values())
    L += ["## Verdict (criteria fixed before the runs)", "",
          "Better = specific retained OR never-read books gain higher by >= %.3f, with forgetting at most %.3f worse; "
          "in every book set." % (MARGIN, FORGET_TOL), ""]
    for key, c in verdict.items():
        L.append("- %s: **%s**" % (key, "PASS" if c["pass"] else ("FAIL" if complete else "INCOMPLETE")))
        for name, v in c["sets"].items():
            L.append("  - set %s: %s" % (name, "not run" if v is None else
                                         "specific %+.4f, never-read books %+.4f, forgetting %+.4f -> %s" % (
                                             v["specific_retained_diff"], v["heldout_gain_diff"], v["forgetting_diff"],
                                             "better" if v["pass"] else "not better")))
    c1, c2 = (verdict[k]["pass"] for k in verdict)
    if not complete:
        decision = "INCOMPLETE: not all runs finished."
    elif c1:
        decision = "Port the growth mechanism together with anchor and guard."
    elif c2:
        decision = ("Growth helps only when the base is frozen. Port anchor and guard; growth is not part of the "
                    "default recipe.")
    else:
        decision = "Do not port the growth mechanism. Port anchor and guard only."
    L += ["", "**Decision: %s**" % decision, "",
          "Report only: schedule vs surprise (timing) = F_sched vs F_auto: " + "; ".join(
              "set %s: specific %s, never-read books %s" % (
                  name, f(runs["F_auto"]["specific_retained"] - runs["F_sched"]["specific_retained"])
                  if runs["F_auto"] and runs["F_sched"] else "-",
                  f(runs["F_auto"]["heldout_gain"] - runs["F_sched"]["heldout_gain"])
                  if runs["F_auto"] and runs["F_sched"] else "-") for name, runs in sets.items())]
    text = "\n".join(L)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
        Path(args.out).with_suffix(".json").write_text(json.dumps({"sets": sets, "verdict": verdict,
                                                                   "decision": decision}, indent=1) + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
