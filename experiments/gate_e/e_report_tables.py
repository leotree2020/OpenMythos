#!/usr/bin/env python3
"""
Descriptive tables for the E1 report, read from the finished formal results
(written after the run; no threshold or rule is set here). Per run:
    readability  A_lin (linear_std) and A_mlp: the maximum P2 accuracy over
                 the digit-position record points except emb (e_events.a_max),
                 at step 0, the t_P2lin / t_P2mlp threshold c0 + 0.5 (A(0) - c0),
                 and at the last checkpoint
    M3           at the t_P2lin checkpoint and at the last checkpoint: the
                 label and the letter-sensitivity share s (95% CI) of every
                 digit-position record point except emb (9.4 asks for s when
                 t_P2lin happens and t_M3 does not)
    M1           at the last checkpoint: P(roots), query insensitivity, J

    python experiments/gate_e/e_report_tables.py   -> report_tables.json
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import e_common  # noqa: F401,E402
from e_common import ARMS, BRIDGE_SEEDS, BRIDGE_STEPS, K2_SEEDS, K2_STEPS, atomic_write_json, state_name  # noqa: E402
from e_events import C0_P2, NOT_HAPPENED, a_max  # noqa: E402


def m3_points(r):
    out = {}
    for rp, v in r["M3"]["pooled"].items():
        if rp == "emb":
            continue
        d = v["digit"]
        out[rp] = {"label": d["label"], "s": d.get("s"), "s_ci95": d.get("s_ci95")}
    return out


def main():
    events = json.load(open(os.path.join(HERE, "events.json")))
    out = {}
    for K, seeds, steps in ((2, K2_SEEDS, K2_STEPS), (4, BRIDGE_SEEDS, BRIDGE_STEPS)):
        for arm in ARMS:
            group = {}
            for seed in seeds:
                load = lambda t: json.load(open(os.path.join(HERE, "results", f"{state_name(arm, K, seed, t)}.json")))  # noqa: E731
                first, last = load(steps[0]), load(steps[-1])
                ev = events[f"K{K}_{arm}"]["per_seed"][str(seed)]["events"]
                row = {"readability": {}, "m3": {}}
                for kind, e in (("linear_std", "t_P2lin"), ("mlp", "t_P2mlp")):
                    a0 = a_max(first["M2"], kind)
                    row["readability"][kind] = {"A_step0": a0, "threshold": C0_P2 + 0.5 * (a0 - C0_P2),
                                                f"A_step{steps[-1]}": a_max(last["M2"], kind), "event": ev[e]}
                if ev["t_P2lin"] != NOT_HAPPENED:
                    row["m3"][f"at_t_P2lin_step{ev['t_P2lin']}"] = m3_points(load(ev["t_P2lin"]))
                row["m3"][f"at_step{steps[-1]}"] = m3_points(last)
                m1 = last["M1"]
                row["m1_last"] = {"p_roots": m1["metrics"]["p_roots"]["mean"],
                                  "query_insensitivity": m1["query_insensitivity"]["mean"],
                                  "J": m1["metrics"]["J"]["mean"], "J_ci95": m1["metrics"]["J"]["ci95"]}
                group[seed] = row
            out[f"K{K}_{arm}"] = group
    atomic_write_json(os.path.join(HERE, "report_tables.json"), out, indent=1)


if __name__ == "__main__":
    main()
