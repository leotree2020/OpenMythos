#!/usr/bin/env python3
"""
Build and validate the Gate D diagnostic sets (no model involved).

Every row is a level-A body ("a=3;b=7;c=5;d=9;") with its 4 queries in
statement-slot order. Sets and RNGs (PREREGISTRATION.md 2 and 8.11):
    diag_fit   Random(47000)  500 bodies    D2 probe fitting, D5 grad J
    diag_eval  Random(48000)  500 bodies    all diagnostic metrics
    pool_b     Random(49000)  D5(b) batches: 200 x O (64 bodies, 1 query each),
                              200 x P (32 bodies, 2 distinct queries),
                              200 x F (16 bodies, all 4 queries)
    pool_c     Random(49500)  1000 bodies   D5(c) expected-gradient pool
    timing     Random(50000)  100 bodies    performance test only
Isolation: no body may occur in the training streams (seeds 1-3, 12,000 steps
x 64), in A_dev / A_test / A_test2 (prompts and both counterfactuals), or in
another diagnostic set. A drawn body that does would be skipped (rejection,
deterministic) and the count of skipped bodies is reported. Writes
sets/*.jsonl, sets/manifest.json and validation_sets.json; exits non-zero on
any failure.
"""

import hashlib
import json
import os
import random
import sys

from common import EXP, HERE, SETS

sys.path.insert(0, os.path.join(EXP, "gen_gate_a"))
from levels import make_sample, solve  # noqa: E402
from splits import train_rng  # noqa: E402

N_BATCH = 200


def body_of(prompt):
    return prompt.split("|")[0]


def family(body):
    assert len(body) == 16
    return {
        "body": body,
        "queries": [body[4 * k] for k in range(4)],
        "answers": [body[4 * k + 2] for k in range(4)],
    }


def main():
    excl = set()
    for s in (1, 2, 3):
        tr = train_rng("A", s)
        excl |= {body_of(make_sample("A", tr, "train")[0]) for _ in range(12_000 * 64)}
    n_train = len(excl)
    for path in (
        os.path.join(EXP, "gen_gate_a", "sets", "A_dev.jsonl"),
        os.path.join(EXP, "gen_gate_a", "sets", "A_test.jsonl"),
        os.path.join(EXP, "budget_a", "sets", "A_test2.jsonl"),
    ):
        for l in open(path):
            r = json.loads(l)
            excl.add(body_of(r["prompt"]))
            excl.add(body_of(r["root_swap"][0]))
            if r["query_swap"]:
                excl.add(body_of(r["query_swap"][0]))
    used, skipped = set(), {}

    def draw(rng, name):
        while True:
            b = body_of(make_sample("A", rng, "test")[0])
            if b in excl or b in used:
                skipped[name] = skipped.get(name, 0) + 1
                continue
            used.add(b)
            return b

    sets = {}
    for name, seed, n in (("diag_fit", 47_000, 500), ("diag_eval", 48_000, 500)):
        rng = random.Random(seed)
        sets[name] = [dict(family(draw(rng, name)), id=i) for i in range(n)]
    rng = random.Random(49_000)
    rows = []
    for scheme, n_bodies, n_q in (("O", 64, 1), ("P", 32, 2), ("F", 16, 4)):
        for b in range(N_BATCH):
            for _ in range(n_bodies):
                fam = family(draw(rng, "pool_b"))
                slots = (
                    [rng.randrange(4)] if n_q == 1 else sorted(rng.sample(range(4), n_q))
                )
                rows.append(dict(fam, scheme=scheme, batch=b, slots=slots))
    sets["pool_b"] = rows
    for name, seed, n in (("pool_c", 49_500, 1000), ("timing", 50_000, 100)):
        rng = random.Random(seed)
        sets[name] = [dict(family(draw(rng, name)), id=i) for i in range(n)]

    fail, manifest = [], {}
    os.makedirs(SETS, exist_ok=True)
    for name, rows in sets.items():
        for r in rows:
            for q, a in zip(r["queries"], r["answers"]):
                if solve(r["body"] + "|" + q + "?") != (a, 0):
                    fail.append(("solver", name, r["body"], q))
            if len(set(r["queries"])) != 4 or len(set(r["answers"])) != 4:
                fail.append(("family", name, r["body"]))
        text = "".join(json.dumps(r) + "\n" for r in rows)
        with open(os.path.join(SETS, f"{name}.jsonl"), "w") as f:
            f.write(text)
        manifest[name] = {
            "rows": len(rows),
            "bodies": len({r["body"] for r in rows}),
            "sha256": hashlib.sha256(text.encode()).hexdigest(),
        }
    with open(os.path.join(SETS, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=1)

    bodies = {n: {r["body"] for r in rows} for n, rows in sets.items()}
    overlap = {}
    names = list(bodies)
    for i, a in enumerate(names):
        overlap[f"{a}∩excluded"] = len(bodies[a] & excl)
        if len(bodies[a]) != len(sets[a]):
            fail.append(("duplicate bodies", a, len(sets[a]) - len(bodies[a])))
        for b in names[i + 1 :]:
            overlap[f"{a}∩{b}"] = len(bodies[a] & bodies[b])
    for k, v in overlap.items():
        if v:
            fail.append(("overlap", k, v))
    rep = {
        "manifest": manifest,
        "excluded_bodies": {"train_streams_12000": n_train, "total": len(excl)},
        "skipped_on_draw": skipped,
        "overlap": overlap,
        "hard_failures": len(fail),
        "examples": [str(x) for x in fail[:3]],
    }
    with open(os.path.join(HERE, "validation_sets.json"), "w") as f:
        json.dump(rep, f, indent=1, ensure_ascii=False)
    print(json.dumps(rep, indent=1, ensure_ascii=False))
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
