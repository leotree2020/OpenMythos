#!/usr/bin/env python3
"""
Mechanical evidence grading of Gate D (ANALYSIS_PLAN.md) from results/*.json.
Writes analysis.json and analysis.md (tables; the narrative report is written
separately). Exits 1 if any of the 30 state files is missing.
"""

import json
import os
import sys

from common import ARMS, HERE, SEEDS, STEPS, state_name

DET, NODET = "检测到可线性解码的信息", "未检测到足够的可线性解码信息"
SUP, OPP, UNC, NA = "支持", "反对", "不确定", "不适用"


RESULTS = os.environ.get("GATE_D_RESULTS", os.path.join(HERE, "results"))
OUT = os.environ.get("GATE_D_OUT", HERE)


def load():
    res, missing = {}, []
    for a in ARMS:
        for s in SEEDS:
            for t in STEPS:
                p = os.path.join(RESULTS, f"{state_name(a, s, t)}.json")
                if os.path.exists(p):
                    res[(a, s, t)] = json.load(open(p))
                else:
                    missing.append(state_name(a, s, t))
    return res, missing


def read_points(arm):
    return ["out0", "out1", "out2"] if arm == "transformer" else \
        ["e", "h1", "h2", "h3", "h4", "h_out", "coda_out"]


def probe_status(r, probe, point):
    """检测到 / 未检测到 / 不确定 / None (skipped), with the MLP refinement."""
    p = r["D2"]["probes"].get(f"{probe}@{point}")
    if p is None or "skipped" in p:
        return None
    d = p["decision"]
    if d == NODET:
        m = r["D2"]["mlp"].get(f"{probe}@{point}")
        if m and not m.get("void") and m["decision"] == DET:
            return UNC
        return NODET
    return DET if d == DET else UNC


def all_none_detected(r, probe, points):
    st = [probe_status(r, probe, p) for p in points]
    st = [x for x in st if x is not None]
    if not st:
        return UNC
    if any(x == DET for x in st):
        return OPP
    if all(x == NODET for x in st):
        return SUP
    return UNC


def d2_controls(r):
    pr = r["D2"]["probes"]["P0@emb"]
    planted = r["D2"]["planted"]
    return pr["acc"] >= 0.95 and all(v["smallest_detected_alpha"] is not None for v in planted.values())


def negligible(i):
    return i["tv"]["mean"] < 0.02 or i["indistinguishable"]["tv"]


def i2_keys(r):
    return [k for k, v in r["D4"]["interfaces"].items() if k.startswith("I2") and "skipped" not in v]


def classes(r, arm, d0, synth, d3_calibrated=False):
    """Per hypothesis: {class: result} for one 12,000-step state."""
    out = {}
    rp = read_points(arm)
    ok2 = d2_controls(r)
    st = state_name(arm, r["_seed"], 12000)
    ok3 = d0["states"][st]["attention_reconstruction"]["pass"] and d0["states"][st]["attention_future_zero"]["pass"]
    d5 = r.get("D5", {})
    ok5 = synth and "a_per_question" in d5 and d5["a_tied_split"]["max_check_diff"] <= 1e-6
    # H1
    h1 = {"D2": all_none_detected(r, "P1", rp) if ok2 else UNC}
    I = r["D4"]["interfaces"]
    i0 = I["I0:emb@17"]
    if any(I[k]["tv"]["mean"] >= 0.02 for k in i2_keys(r)):
        h1["D4"] = OPP
    elif negligible(i0) and all(negligible(I[k]) for k in i2_keys(r)):
        h1["D4"] = SUP
    else:
        h1["D4"] = UNC
    out["H1"] = h1
    # H2
    out["H2"] = {"D2": all_none_detected(r, "P2", [p for p in rp if p != "e"] + (["e"] if arm == "openmythos" else [])) if ok2 else UNC}
    # H3
    d3 = r["D3"]["decision"]
    # revision 4: D3 enters the grading only if its randomization test passed
    # the calibration / negative-control validation (d3_calibration.json);
    # otherwise it is descriptive and does not count as a diagnostic class
    h3 = {"D2": all_none_detected(r, "P3", rp) if ok2 else UNC}
    if d3_calibrated:
        h3["D3"] = (SUP if d3 == "未检测到" else OPP) if ok3 else UNC
    out["H3"] = h3
    # H4
    det = [p for p in rp if DET in (probe_status(r, "P1", p), probe_status(r, "P3", p))]
    if not det or not ok2:
        out["H4"] = {"D2": NA if ok2 else UNC}
    else:
        h4 = {"D2": SUP}
        effects = []
        for p in det:
            k = next((k for k in i2_keys(r) if k.split(":")[1] == f"{p}@18"), None)
            if k:
                effects.append(negligible(I[k]))
        h4["D4"] = UNC if not effects else SUP if all(effects) else OPP if not any(effects) else UNC
        out["H4"] = h4
    # H5, H6
    if ok5:
        c = d5["c_local_direction"]["groups"]["total"]
        lo, hi = c["d_dot_gradJ_ci95"]
        snr = d5["b_batches"]["O"]["s_along_u"]["snr"]
        out["H5"] = {"D5c": OPP if lo > 0 else SUP, "D5b": SUP if abs(snr) < 1 else OPP}
        cons = all(d5["b_vs_a"][g][s]["cis_overlap"] for g in ("attn_all", "total") for s in ("O", "P", "F"))
        po = d5["b_vs_a"]["attn_all"]["P_minus_O_ci95"]
        s3 = d5["a_per_question"]["attn_all"]["S_minus_3V_ci95"]
        out["H6"] = {"D5b": (SUP if po[1] < 0 else OPP if po[0] > 0 else UNC) if cons else UNC,
                     "D5a": (SUP if s3[0] > 0 else OPP if s3[1] < 0 else UNC) if cons else UNC}
    else:
        out["H5"] = {"D5c": UNC, "D5b": UNC}
        out["H6"] = {"D5b": UNC, "D5a": UNC}
    return out


def seed_direction(cl):
    vals = [v for v in cl.values() if v != NA]
    if not vals:
        return NA, 0
    s, o = vals.count(SUP), vals.count(OPP)
    if s and not o:
        return SUP, s
    if o and not s:
        return OPP, o
    return UNC, 0


def grade(per_seed):
    dirs = [d for d, _ in per_seed]
    if all(d == NA for d in dirs):
        return {"grade": NA, "direction": NA}
    for direction in (SUP, OPP):
        idx = [i for i, (d, _) in enumerate(per_seed) if d == direction]
        n2 = [i for i in idx if per_seed[i][1] >= 2]
        if len(idx) == 3 and len(n2) == 3:
            return {"grade": "强", "direction": direction}
        if len(idx) == 3 or len(n2) >= 2:
            return {"grade": "中", "direction": direction}
    return {"grade": "弱或不确定", "direction": UNC}


def main():
    res, missing = load()
    if missing:
        print("missing states:", missing)
        sys.exit(1)
    d0 = json.load(open(os.path.join(HERE, "validation", "d0_rev3.json")))
    synth = not json.load(open(os.path.join(HERE, "validation", "synthetic_d5.json")))["failures"]
    cal_path = os.path.join(HERE, "validation", "d3_calibration.json")
    d3_cal = os.path.exists(cal_path) and not json.load(open(cal_path))["failures"]
    out = {"per_seed": {}, "per_arm": {}, "cross_arm": {}, "d3_counts_as_class": None}
    for a in ARMS:
        seeds = []
        for s in SEEDS:
            r = res[(a, s, 12000)]
            r["_seed"] = s
            cl = classes(r, a, d0, synth, d3_cal)
            out["per_seed"][f"{a}_s{s}"] = {h: {"classes": c, "direction": seed_direction(c)[0],
                                                "n_classes": seed_direction(c)[1]} for h, c in cl.items()}
            seeds.append(cl)
        out["per_arm"][a] = {h: grade([seed_direction(cl[h]) for cl in seeds]) for h in seeds[0]}
    out["d3_counts_as_class"] = d3_cal
    for h in out["per_arm"]["openmythos"]:
        g1, g2 = out["per_arm"]["openmythos"][h], out["per_arm"]["transformer"][h]
        if g1["grade"] == g2["grade"] == "强" and g1["direction"] == g2["direction"]:
            c = f"两种架构共同（{g1['direction']}）"
        elif "强" in (g1["grade"], g2["grade"]) and not (g1["grade"] == g2["grade"] and g1["direction"] == g2["direction"]):
            c = "架构差异线索"
        else:
            c = "分别报告"
        out["cross_arm"][h] = c
    # exploratory curves (all steps)
    curves = {}
    for (a, s, t), r in sorted(res.items()):
        d1 = r["D1"]["metrics"]
        row = {"acc": d1["acc"]["mean"], "dp_root": d1["dp_root"]["mean"], "tv": d1["tv"]["mean"],
               "p_roots": d1["p_roots"]["mean"], "d3_max_share": r["D3"]["primary_max_share"],
               "d4_I0_tv": r["D4"]["interfaces"]["I0:emb@17"]["tv"]["mean"]}
        for probe in ("P1", "P2", "P3"):
            row[probe] = {p: probe_status(r, probe, p) for p in read_points(a)}
        if "a_per_question" in r.get("D5", {}):
            d5 = r["D5"]
            row["S_minus_3V_attn"] = d5["a_per_question"]["attn_all"]["S_minus_3V"]
            row["snr_u_O"] = d5["b_batches"]["O"]["s_along_u"]["snr"]
            row["d_dot_gradJ"] = d5["c_local_direction"]["groups"]["total"]["d_dot_gradJ"]
        curves[state_name(a, s, t)] = row
    out["curves_exploratory"] = curves
    with open(os.path.join(OUT, "analysis.json"), "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    lines = ["| 假设 | OpenMythos | Transformer | 跨架构 |", "|---|---|---|---|"]
    for h in out["per_arm"]["openmythos"]:
        g1, g2 = out["per_arm"]["openmythos"][h], out["per_arm"]["transformer"][h]
        lines.append(f"| {h} | {g1['grade']}（{g1['direction']}） | {g2['grade']}（{g2['direction']}） | {out['cross_arm'][h]} |")
    lines += ["", "| 种子 | " + " | ".join(out["per_arm"]["openmythos"]) + " |",
              "|---|" + "---|" * len(out["per_arm"]["openmythos"])]
    for k, v in out["per_seed"].items():
        lines.append(f"| {k} | " + " | ".join(
            f"{v[h]['direction']} ({', '.join(f'{c}:{x}' for c, x in v[h]['classes'].items())})" for h in v) + " |")
    with open(os.path.join(OUT, "analysis.md"), "w") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
