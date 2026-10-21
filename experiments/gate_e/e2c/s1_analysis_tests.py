#!/usr/bin/env python3
"""
Stage 1, check of the stage-4 analysis code e2c_analysis.py (with V7): no test2,
no judgment; synthetic tables and the measurement-set results of R3 only.

    1  p-bar of the Appendix F cells (N = 24) equal the registered values
    2  N = 20, 24, 30: for every cell, frozen-table membership <=> p-bar <= 0.025
    3  exact McNemar and Holm on known cases
    4  the decision table: every cell gives a conclusion; (0, 0) depends on
       the exclusion test; modifiers attach to the P2 columns
    5  t_P2lin from the D2c results of R3 (E1 seeds 1-5, both arms) equals
       E1's events.json for every run
    6  analyse_arm runs end to end on a synthetic cohort of 24 seeds
Writes stage1/analysis_tests.json; exit 0 only if all pass.
"""

import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GE = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, GE)

import e2c_analysis as A  # noqa: E402
from s1_budget import STAGE1, Ledger  # noqa: E402

REG = {(0, 0): "0.001565", (2, 0): "0.016419", (3, 0): "0.042398", (3, 1): "0.020521", (5, 5): "0.016419",
       (5, 4): "0.026150", (10, 13): "0.018947", (10, 12): "0.026150", (11, 13): "0.042254"}


def main():
    res = {}
    led = Ledger()
    with led.job("analysis_tests"):
        got = {f"{b},{c}": A.p_bar(b, c, 24) for (b, c) in REG}
        res["1_p_bar_appendix_F"] = {"values": got, "pass": all(got[f"{b},{c}"] == v for (b, c), v in REG.items())}
        bad = []
        for n in (20, 24, 30):
            for b in range(n + 1):
                for c in range(n + 1 - b):
                    if A.in_table(b, c, n) != (float(A.p_bar(b, c, n)) <= 0.025):
                        bad.append([n, b, c])
        res["2_table_equals_p_bar_rule"] = {"cells_checked": sum((n + 1) * (n + 2) // 2 for n in (20, 24, 30)), "mismatches": bad,
                                            "pass": not bad}
        mc = {"0,0": A.mcnemar(0, 0) == 1.0, "5,0": abs(A.mcnemar(5, 0) - 0.0625) < 1e-15,
              "10,0": abs(A.mcnemar(10, 0) - 2 / 1024) < 1e-15, "7,2": abs(A.mcnemar(7, 2) - 92 / 512) < 1e-15}
        hl = {"both": A.holm(0.01, 0.02, 0.025) == [True, True], "both_reversed": A.holm(0.013, 0.001, 0.025) == [True, True],
              "none": A.holm(0.02, 0.03, 0.025) == [False, False], "first_only": A.holm(0.001, 0.03, 0.025) == [True, False],
              "tf": A.holm(0.02, 0.04, 0.05) == [True, True]}
        res["3_mcnemar_holm"] = {"mcnemar": mc, "holm": hl, "pass": all(mc.values()) and all(hl.values())}
        cells = {}
        ex_rej = {"reject": True, "p_bar": "0.010000"}
        for s1 in "+0-":
            for s2 in "+0-":
                d = A.decide(s1, s2, None, 24, True, True, True)
                cells[s1 + s2] = bool(d["conclusion"])
        d00 = A.decide("0", "0", ex_rej, 24, True, True, True)["conclusion"].startswith("与较大提高不相容")
        d00n = A.decide("0", "0", {"reject": False, "p_bar": "0.3"}, 24, True, True, True)["conclusion"].startswith("不确定")
        dmod = A.decide("+", "+", ex_rej, 24, False, False, False)["modifiers"]
        res["4_decision_table"] = {"cells": cells, "00_exclusion": d00, "00_not": d00n, "modifiers_++": dmod,
                                   "pass": all(cells.values()) and d00 and d00n and len(dmod) == 4}
        ev = json.load(open(os.path.join(GE, "events.json")))
        g2 = os.path.join(STAGE1, "gate2", "r3")
        tp = {}
        for arm in ("openmythos", "transformer"):
            for s in range(1, 6):
                alin = {t: json.load(open(os.path.join(g2, f"K2_{arm}_s{s}_step{t}.json")))["A_lin"] for t in A.STEPS}
                mine = A.t_p2lin(alin)[0]
                e1 = ev[f"K2_{arm}"]["per_seed"][str(s)]["events"]["t_P2lin"]
                tp[f"{arm}_s{s}"] = {"d2c_grid": mine, "e1": e1, "equal": mine == e1}
        res["5_t_P2lin_vs_E1"] = {"runs": tp, "pass": all(v["equal"] for v in tp.values())}
        rng = random.Random(3)
        seeds = list(range(201, 225))
        learned = {"C0": {s: rng.random() < 0.4 for s in seeds}, "C1": {s: rng.random() < 0.9 for s in seeds},
                   "C2": {s: rng.random() < 0.4 for s in seeds}}
        alin = {c: {s: {t: (0.6 if t == 0 else (0.8 if c == "C1" else 0.1)) for t in A.STEPS} for s in seeds} for c in learned}
        pairing = {f"{c}_openmythos_s{s}": {"E_W": 1.0 + 0.1 * (c == "C2"), "clip_share_W": 0.5} for c in ("C1", "C2") for s in seeds}
        out = A.analyse_arm("openmythos", seeds, learned, alin, pairing, 0.025, True)
        res["6_synthetic_cohort"] = {"P1": out["P1"], "P2": out["P2"], "exclusion": out["exclusion_Delta10"],
                                     "manipulation": out["manipulation_check"]["pass"], "verdict": out["verdict"],
                                     "pass": out["verdict"]["status"] == "判定" and out["P1"]["sign"] in "+0-"}
    res["pass"] = all(v["pass"] for v in res.values())
    json.dump(res, open(os.path.join(STAGE1, "analysis_tests.json"), "w"), indent=1, ensure_ascii=False)
    print(json.dumps({k: v["pass"] for k, v in res.items() if isinstance(v, dict)}, indent=1))
    sys.exit(0 if res["pass"] else 3)


if __name__ == "__main__":
    main()
