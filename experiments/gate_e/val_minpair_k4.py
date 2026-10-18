#!/usr/bin/env python3
"""
Freeze record and isolation of minpair_k4 (review of the implementation
report: principle approved; RNG 71000 and 6000 pairs to be recorded, frozen and
checked for isolation before any formal result). Checks:
  - the file matches sets/manifest.json; 6000 rows = 500 bodies x 4 statements
    x 3 letters; rebuilding the rule from diag_eval_k4 with Random(71000)
    reproduces the file byte for byte
  - every perturbed prompt is a valid task (independent solver), the letter is
    absent from the original body, only statement j (and the query when it
    named that statement) changed
  - overlap of the perturbed bodies with budget_a's training streams (seeds
    1-3 x 12,000 x 64), A_dev / A_test / A_test2 (with counterfactuals), every
    Gate D set, and every other Gate E K=4 set: reported (expected 0); the
    perturbed bodies are paired with diag_eval_k4 by construction and are not
    an independent set
Writes validation/minpair_k4.json; exits non-zero on a hard failure (hash,
rebuild, validity); overlaps are reported, and a non-zero overlap with a
training stream or an archived test set is also a failure.
"""

import hashlib
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import e_common  # noqa: F401,E402
from e_common import EXP, LETTERS, SETS, load_set  # noqa: E402
from e_task import check  # noqa: E402
from levels import make_sample  # noqa: E402
from splits import train_rng  # noqa: E402


def main():
    fail, rep = [], {}
    text = open(os.path.join(SETS, "minpair_k4.jsonl")).read()
    man = json.load(open(os.path.join(SETS, "manifest.json")))["minpair_k4"]
    rep["sha256"] = hashlib.sha256(text.encode()).hexdigest()
    rep["manifest_match"] = rep["sha256"] == man["sha256"]
    mp = load_set("minpair_k4")
    ev = load_set("diag_eval_k4")
    rep["rows"] = len(mp)
    rng = random.Random(71_000)
    rebuilt = []
    for r in ev:
        for j in range(4):
            absent = [c for c in LETTERS if c not in r["queries"]]
            for alt in rng.sample(absent, 3):
                old = r["queries"][j]
                nb = r["body"][: 4 * j] + alt + r["body"][4 * j + 1:]
                rebuilt.append({"id": r["id"], "stmt": j, "alt": alt, "body": nb,
                                "queries": [alt if q == old else q for q in r["queries"]],
                                "answers": list(r["answers"]), "heldout": None})
    rep["rebuild_identical"] = "".join(json.dumps(x) + "\n" for x in rebuilt) == text
    by_id = {r["id"]: r for r in ev}
    bad = 0
    for m in mp:
        o = by_id[m["id"]]
        j = m["stmt"]
        same_elsewhere = all(m["body"][i] == o["body"][i] for i in range(16) if i != 4 * j)
        renamed = m["queries"] == [m["alt"] if q == o["queries"][j] else q for q in o["queries"]]
        valid = all(check(m["body"] + "|" + q + "?", a) for q, a in zip(m["queries"], m["answers"]))
        bad += not (m["alt"] not in o["queries"] and same_elsewhere and renamed and valid)
    rep["invalid_pairs"] = bad
    for k in ("manifest_match", "rebuild_identical"):
        if not rep[k]:
            fail.append(k)
    if len(mp) != 6000 or bad:
        fail.append("rows/validity")

    pert = {m["body"] for m in mp}
    rep["distinct_perturbed_bodies"] = len(pert)
    train = set()
    for s in (1, 2, 3):
        tr = train_rng("A", s)
        train |= {make_sample("A", tr, "train")[0].split("|")[0] for _ in range(12_000 * 64)}
    archived = set()
    for path in (os.path.join(EXP, "gen_gate_a", "sets", "A_dev.jsonl"),
                 os.path.join(EXP, "gen_gate_a", "sets", "A_test.jsonl"),
                 os.path.join(EXP, "budget_a", "sets", "A_test2.jsonl")):
        for line in open(path):
            r = json.loads(line)
            archived.add(r["prompt"].split("|")[0])
            archived.add(r["root_swap"][0].split("|")[0])
            if r["query_swap"]:
                archived.add(r["query_swap"][0].split("|")[0])
    gd = set()
    gd_dir = os.path.join(EXP, "gate_d", "sets")
    for fn in os.listdir(gd_dir):
        if fn.endswith(".jsonl"):
            gd |= {json.loads(line)["body"] for line in open(os.path.join(gd_dir, fn))}
    other = {}
    for n in ("diag_fit_k4", "diag_eval_k4", "pool_b_k4", "pool_c_k4"):
        other[n] = len(pert & {r["body"] for r in load_set(n)})
    rep["overlap"] = {"budget_a_train_streams_12000": len(pert & train), "A_dev_test_test2": len(pert & archived),
                      "gate_d_sets": len(pert & gd), **{f"gate_e_{k}": v for k, v in other.items()}}
    if rep["overlap"]["budget_a_train_streams_12000"] or rep["overlap"]["A_dev_test_test2"]:
        fail.append("overlap with a training stream or an archived test set")
    rep["note"] = "paired with diag_eval_k4 by construction (local input perturbation), not an independent set"
    rep["hard_failures"] = fail
    rep["pass"] = not fail
    with open(os.path.join(HERE, "validation", "minpair_k4.json"), "w") as f:
        json.dump(rep, f, indent=1, ensure_ascii=False)
    print(json.dumps(rep, indent=1, ensure_ascii=False))
    sys.exit(0 if rep["pass"] else 1)


if __name__ == "__main__":
    main()
