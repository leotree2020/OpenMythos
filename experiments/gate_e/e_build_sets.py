#!/usr/bin/env python3
"""
Build and validate the Gate E sets (PREREGISTRATION 3, 9.3, 9.5). No model is
involved. Rows are bodies with their queries / answers in statement-slot order.

K=2 (held-out bodies only, mutually disjoint by unordered statement key):
    dev_heldout   Random(61000)  500 bodies   learning curves
    test_heldout  Random(62000)  1000 bodies  formal judgment at step 12,000; per
                                              question a root-swap counterfactual
                                              whose body is held-out as well
    diag_fit      Random(63000)  1000 bodies  probe fitting, grad J
    diag_eval     Random(64000)  1000 bodies  all diagnostic metrics
    minpair       Random(65000)  derived from diag_eval (local input perturbation,
                                              paired with diag_eval, not an
                                              independent set): per body and
                                              statement 3 absent letters, consistent
                                              renaming (statement and query)
K=2 (non-held-out, training distribution):
    pool_b_k2     Random(66000)  M5(b): 200 x O (64 bodies, 1 query), 200 x F
                                 (32 bodies x 2 queries)
    pool_c_k2     same stream    1000 bodies, M5(c)
    dev_seen      Random(67000)  500 bodies   descriptive (memorization check)
K=4 bridge (level A bodies):
    diag_fit_k4   Random(68000)  500 bodies
    diag_eval_k4  Random(69000)  500 bodies
    minpair_k4    Random(71000)  derived from diag_eval_k4 by the minpair rule
                                 (4 statements x 3 letters); not named in the
                                 preregistration, flagged for review
    pool_b_k4     Random(70000)  200 x O / P / F as in Gate D
    pool_c_k4     same stream    1000 bodies
Isolation (3.2): K=2 held-out sets vs the 5 seeds x 12,000 x 64 training
streams (0 by construction, checked); K=4 sets vs budget_a's streams (seeds
1-3 x 12,000 x 64), A_dev / A_test / A_test2 (with counterfactuals) and every
Gate D set; no body shared between any two sets. Writes sets/*.jsonl,
sets/manifest.json and validation/sets.json; exits non-zero on any failure.
"""

import hashlib
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from e_common import EXP, LETTERS, SETS, body_key, is_heldout, statements  # noqa: E402
from e_task import check, sample_k2, train_rng_k2, train_sample_k2  # noqa: E402
from levels import make_sample, solve  # noqa: E402
from splits import train_rng  # noqa: E402

N_BATCH = 200


def body_of(prompt):
    return prompt.split("|")[0]


def family(body):
    st = statements(body)
    return {"body": body, "queries": [v for v, _ in st], "answers": [d for _, d in st]}


def heldout_unit_tests():
    """Held-out rule: both statement orders share one key and one decision;
    the query plays no part; the share is about 10%."""
    out, rng = {}, random.Random(1)
    same = 0
    for _ in range(20000):
        b = body_of(sample_k2(rng)[0])
        swapped = b[4:] + b[:4]
        same += body_key(b) == body_key(swapped) and is_heldout(b) == is_heldout(swapped)
    out["both_orders_same_key_and_decision"] = same == 20000
    rng = random.Random(2)
    n = 200000
    share = sum(is_heldout(body_of(sample_k2(rng)[0])) for _ in range(n)) / n
    out["heldout_share"] = share
    out["heldout_share_ok"] = 0.09 <= share <= 0.11
    out["key_ignores_query"] = body_key("a=3;b=7;") == body_key("b=7;a=3;")
    out["pass"] = all(v for k, v in out.items() if k.endswith(("ok", "decision", "query")))
    return out


def main():
    fail, rep = [], {"heldout_rule": heldout_unit_tests()}
    if not rep["heldout_rule"]["pass"]:
        fail.append(("heldout_rule", rep["heldout_rule"]))

    # ---------------- K=2 training streams (for the isolation check)
    train_keys_k2 = set()
    for s in range(1, 6):
        rng = train_rng_k2(s)
        for _ in range(12_000 * 64):
            train_keys_k2.add(body_key(body_of(train_sample_k2(rng)[0])))
    rep["k2_train_stream_distinct_keys"] = len(train_keys_k2)

    sets, used, skipped = {}, set(), {}

    def draw_k2(rng, name, heldout):
        while True:
            b = body_of(sample_k2(rng)[0])
            k = body_key(b)
            if is_heldout(b) != heldout or k in used:
                skipped[name] = skipped.get(name, 0) + 1
                continue
            used.add(k)
            return b

    for name, seed, n in (("dev_heldout", 61_000, 500), ("test_heldout", 62_000, 1000),
                          ("diag_fit", 63_000, 1000), ("diag_eval", 64_000, 1000)):
        rng = random.Random(seed)
        rows = []
        for i in range(n):
            while True:
                fam = dict(family(draw_k2(rng, name, True)), id=i)
                if name != "test_heldout":
                    break
                # root swap per question: an absent digit keeping the body held-out
                rs, ok = [], True
                for k in range(2):
                    cands = [d for d in "0123456789" if d not in fam["answers"]]
                    rng.shuffle(cands)
                    pick = None
                    for d in cands:
                        nb = fam["body"].replace(f"{fam['queries'][k]}={fam['answers'][k]};",
                                                 f"{fam['queries'][k]}={d};")
                        if is_heldout(nb):
                            pick = (nb, d)
                            break
                    if pick is None:
                        ok = False
                        break
                    rs.append({"body": pick[0], "answer": pick[1]})
                if ok:
                    fam["root_swap"] = rs
                    break
                skipped["test_heldout_no_heldout_root_swap"] = skipped.get("test_heldout_no_heldout_root_swap", 0) + 1
            rows.append(fam)
        sets[name] = rows

    # minimal pairs from diag_eval (9.3): 3 absent letters per statement, consistent renaming
    rng = random.Random(65_000)
    mp = []
    for r in sets["diag_eval"]:
        for j in range(2):
            absent = [c for c in LETTERS if c not in r["queries"]]
            for alt in rng.sample(absent, 3):
                old = r["queries"][j]
                nb = r["body"][: 4 * j] + alt + r["body"][4 * j + 1:]
                qs = [alt if q == old else q for q in r["queries"]]
                mp.append({"id": r["id"], "stmt": j, "alt": alt, "body": nb, "queries": qs,
                           "answers": list(r["answers"]), "heldout": is_heldout(nb)})
    sets["minpair"] = mp

    rng = random.Random(66_000)
    rows = []
    for scheme, n_bodies, n_q in (("O", 64, 1), ("F", 32, 2)):
        for b in range(N_BATCH):
            for _ in range(n_bodies):
                fam = family(draw_k2(rng, "pool_b_k2", False))
                slots = [rng.randrange(2)] if n_q == 1 else [0, 1]
                rows.append(dict(fam, scheme=scheme, batch=b, slots=slots))
    sets["pool_b_k2"] = rows
    sets["pool_c_k2"] = [dict(family(draw_k2(rng, "pool_c_k2", False)), id=i) for i in range(1000)]
    rng = random.Random(67_000)
    sets["dev_seen"] = [dict(family(draw_k2(rng, "dev_seen", False)), id=i) for i in range(500)]

    # ---------------- K=4 bridge sets
    excl = set()
    for s in (1, 2, 3):
        tr = train_rng("A", s)
        excl |= {body_of(make_sample("A", tr, "train")[0]) for _ in range(12_000 * 64)}
    rep["k4_excluded_train_stream_bodies"] = len(excl)
    for path in (os.path.join(EXP, "gen_gate_a", "sets", "A_dev.jsonl"),
                 os.path.join(EXP, "gen_gate_a", "sets", "A_test.jsonl"),
                 os.path.join(EXP, "budget_a", "sets", "A_test2.jsonl")):
        for line in open(path):
            r = json.loads(line)
            excl.add(body_of(r["prompt"]))
            excl.add(body_of(r["root_swap"][0]))
            if r["query_swap"]:
                excl.add(body_of(r["query_swap"][0]))
    gd_sets = os.path.join(EXP, "gate_d", "sets")
    for fn in sorted(os.listdir(gd_sets)):
        if fn.endswith(".jsonl"):
            excl |= {json.loads(line)["body"] for line in open(os.path.join(gd_sets, fn))}
    rep["k4_excluded_total"] = len(excl)
    used4 = set()

    def draw_k4(rng, name):
        while True:
            b = body_of(make_sample("A", rng, "test")[0])
            if b in excl or b in used4:
                skipped[name] = skipped.get(name, 0) + 1
                continue
            used4.add(b)
            return b

    for name, seed in (("diag_fit_k4", 68_000), ("diag_eval_k4", 69_000)):
        rng = random.Random(seed)
        sets[name] = [dict(family(draw_k4(rng, name)), id=i) for i in range(500)]
    rng = random.Random(70_000)
    rows = []
    for scheme, n_bodies, n_q in (("O", 64, 1), ("P", 32, 2), ("F", 16, 4)):
        for b in range(N_BATCH):
            for _ in range(n_bodies):
                fam = family(draw_k4(rng, "pool_b_k4"))
                slots = [rng.randrange(4)] if n_q == 1 else sorted(rng.sample(range(4), n_q))
                rows.append(dict(fam, scheme=scheme, batch=b, slots=slots))
    sets["pool_b_k4"] = rows
    sets["pool_c_k4"] = [dict(family(draw_k4(rng, "pool_c_k4")), id=i) for i in range(1000)]
    # K=4 counterpart of minpair (same rule; RNG 71000; flagged for review: the
    # preregistration names only the K=2 set, M3 runs at every checkpoint)
    rng = random.Random(71_000)
    mp4 = []
    for r in sets["diag_eval_k4"]:
        for j in range(4):
            absent = [c for c in LETTERS if c not in r["queries"]]
            for alt in rng.sample(absent, 3):
                old = r["queries"][j]
                nb = r["body"][: 4 * j] + alt + r["body"][4 * j + 1:]
                qs = [alt if q == old else q for q in r["queries"]]
                mp4.append({"id": r["id"], "stmt": j, "alt": alt, "body": nb, "queries": qs,
                            "answers": list(r["answers"]), "heldout": None})
    sets["minpair_k4"] = mp4

    # ---------------- checks and files
    manifest = {}
    os.makedirs(SETS, exist_ok=True)
    for name, rows in sets.items():
        K = len(rows[0]["queries"])
        for r in rows:
            for q, a in zip(r["queries"], r["answers"]):
                if not check(r["body"] + "|" + q + "?", a):
                    fail.append(("solver", name, r["body"], q))
            if len(set(r["queries"])) != K or len(set(r["answers"])) != K:
                fail.append(("family", name, r["body"]))
            for k, rs in enumerate(r.get("root_swap", [])):
                if solve(rs["body"] + "|" + r["queries"][k] + "?") != (rs["answer"], 0) \
                        or not is_heldout(rs["body"]) or rs["answer"] in r["answers"]:
                    fail.append(("root_swap", name, r["body"], k))
        text = "".join(json.dumps(r) + "\n" for r in rows)
        with open(os.path.join(SETS, f"{name}.jsonl"), "w") as f:
            f.write(text)
        manifest[name] = {"rows": len(rows), "bodies": len({r["body"] for r in rows}),
                          "sha256": hashlib.sha256(text.encode()).hexdigest()}
    with open(os.path.join(SETS, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=1)

    k2_held = ("dev_heldout", "test_heldout", "diag_fit", "diag_eval")
    k2_seen = ("pool_b_k2", "pool_c_k2", "dev_seen")
    k4 = ("diag_fit_k4", "diag_eval_k4", "pool_b_k4", "pool_c_k4")
    keys = {n: {body_key(r["body"]) for r in sets[n]} for n in k2_held + k2_seen}
    keys.update({n: {r["body"] for r in sets[n]} for n in k4})
    overlap = {}
    names = k2_held + k2_seen + k4
    for i, a in enumerate(names):
        if len(keys[a]) != len(sets[a]):
            fail.append(("duplicate bodies", a, len(sets[a]) - len(keys[a])))
        for b in names[i + 1:]:
            overlap[f"{a}∩{b}"] = len(keys[a] & keys[b])
    for n in k2_held:
        overlap[f"{n}∩k2_train_streams"] = len(keys[n] & train_keys_k2)
        if not all(is_heldout(r["body"]) for r in sets[n]):
            fail.append(("not held-out", n))
    for n in k2_seen:
        if any(is_heldout(r["body"]) for r in sets[n]):
            fail.append(("held-out body in a training-distribution set", n))
    for n in k4:
        overlap[f"{n}∩k4_excluded"] = len(keys[n] & excl)
    for k, v in overlap.items():
        if v:
            fail.append(("overlap", k, v))
    mp = sets["minpair"]
    rep["minpair"] = {
        "pairs": len(mp),
        "share_perturbed_body_heldout": sum(r["heldout"] for r in mp) / len(mp),
        "all_valid_tasks": all(check(r["body"] + "|" + q + "?", a) for r in mp
                               for q, a in zip(r["queries"], r["answers"])),
        "paired_with": "diag_eval (local input perturbation, not an independent set)",
    }
    rep["dev_seen_bodies_in_k2_train_streams"] = len(keys["dev_seen"] & train_keys_k2) / len(sets["dev_seen"])
    rep.update({"manifest": manifest, "skipped_on_draw": skipped, "overlap": overlap,
                "hard_failures": len(fail), "examples": [str(x) for x in fail[:5]]})
    os.makedirs(os.path.join(HERE, "validation"), exist_ok=True)
    with open(os.path.join(HERE, "validation", "sets.json"), "w") as f:
        json.dump(rep, f, indent=1, ensure_ascii=False)
    print(json.dumps({k: v for k, v in rep.items() if k != "manifest"}, indent=1, ensure_ascii=False))
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
