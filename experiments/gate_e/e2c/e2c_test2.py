"""
The sealed test set test2_heldout of E2-c (E2C_PREREG_DRAFT 5.1, 7.4) and its
evaluation. Implemented in stage 1; executed only in stage 2 (key-space
counts and hashes) and stage 4 (generation and judgment) with their own
authorizations. In stage 1 nothing here is run on the real key space: the
enumeration refuses to run unless E2C_KEYSPACE_STAGE is "2" or "4", and the
fault-injection tests (V4) replace it by stubs or use synthetic pools.

    keyspace(sets_dir)        H, U, R*, M1* of 7.4 steps 2-3 (Appendix A rules)
    pool_hashes(R, M1)        sha256 of the sorted, one-key-per-line serializations
    generate(salt, R, M1)     7.4 step 8: 1000 main bodies, both queries, 1-2
                              root-swap counterfactuals per body (preferred / fallback)
    isolation(test2, ...)     7.4 step 9 checks
    evaluate(model, test2)    5.1 metrics of one run at step 12000
"""

import hashlib
import itertools
import json
import os
import random
import sys

import numpy as np
import torch

HERE = os.path.dirname(os.path.abspath(__file__))
GE = os.path.dirname(HERE)
if GE not in sys.path:
    sys.path.insert(0, GE)

import e_common  # noqa: E402,F401
from e_common import LETTERS, Geom, encode  # noqa: E402

DIG = "0123456789"
N_BODIES = 1000
SALT_PREFIX = "E2C-test2|"
E1_HELDOUT_SETS = ("dev_heldout", "test_heldout", "diag_fit", "diag_eval")
LEARNED = {"accuracy": 0.9, "root_swap_both": 0.8, "query_swap_both": 0.8}
BASELINE = 0.5


class NotAuthorized(Exception):
    pass


def key(st):
    return ";".join(sorted(f"{v}={d}" for v, d in st))


def held(k):
    return int(hashlib.sha256(k.encode()).hexdigest(), 16) % 10 == 0


def stmts(body):
    return [(body[i], body[i + 2]) for i in range(0, len(body), 4)]


def key_stmts(k):
    a, b = k.split(";")
    return [(a[0], a[2]), (b[0], b[2])]


def _guard():
    if os.environ.get("E2C_KEYSPACE_STAGE") not in ("2", "4"):
        raise NotAuthorized("the key space of test2 is enumerated only in stage 2 (hashing) or stage 4 "
                            "(judgment), each with its own authorization")


def keyspace(sets_dir):
    """7.4 steps 2-3, the rules of Appendix A: canonical enumeration of the K=2
    key space (letter pairs l1 < l2 in LETTERS order, digits d1 != d2 in
    character order), H = held-out keys, U = held-out keys used by E1's sets,
    R* = H - U, M1* = keys of R* with at least one statement re-rootable in R*."""
    _guard()
    H = set()
    for l1, l2 in itertools.combinations(LETTERS, 2):
        for d1 in DIG:
            for d2 in DIG:
                if d1 != d2:
                    k = key([(l1, d1), (l2, d2)])
                    if held(k):
                        H.add(k)
    U = set()

    def add(body):
        k = key(stmts(body))
        if k in H:
            U.add(k)
    for name in E1_HELDOUT_SETS:
        for line in open(os.path.join(sets_dir, name + ".jsonl")):
            r = json.loads(line)
            add(r["body"])
            for rs in r.get("root_swap", []):
                add(rs["body"])
    for line in open(os.path.join(sets_dir, "minpair.jsonl")):
        add(json.loads(line)["body"])
    R = H - U
    M1 = {k for k in R if any(swap_options(k, j, R) for j in (0, 1))}
    return {"H": H, "U": U, "R": R, "M1": M1}


def swap_options(k, j, pool):
    """Digits d (not in the body) for which re-rooting statement j gives a key in pool."""
    st = key_stmts(k)
    ds = {st[0][1], st[1][1]}
    out = []
    for d in DIG:
        if d in ds:
            continue
        nst = list(st)
        nst[j] = (st[j][0], d)
        if key(nst) in pool:
            out.append(d)
    return out


def serialize(keys):
    return "".join(k + "\n" for k in sorted(keys))


def pool_hashes(R, M1):
    return {"R_star_sha256": hashlib.sha256(serialize(R).encode()).hexdigest(),
            "M1_star_sha256": hashlib.sha256(serialize(M1).encode()).hexdigest(),
            "counts": {"R_star": len(R), "M1_star": len(M1)}}


def salt_matches(salt, commitment):
    return hashlib.sha256(salt.encode()).hexdigest() == commitment


def generate(salt, R, M1, n=N_BODIES):
    """7.4 step 8. Returns the test2 rows (E1 family format with root swaps per
    statement) and the fallback / duplicate counts."""
    seed = int(hashlib.sha256((SALT_PREFIX + salt).encode()).hexdigest(), 16) % (2 ** 63)
    rng = random.Random(seed)
    main = rng.sample(sorted(M1), n)
    main_set = set(main)
    chosen = set()
    rows, n_fallback = [], 0
    for k in main:
        st = key_stmts(k)
        if not rng.random() < 0.5:  # statement order: key order if r < 0.5, else reversed
            st = st[::-1]
        body = "".join(f"{v}={d};" for v, d in st)
        swaps = []
        for j in range(2):
            ds = {st[0][1], st[1][1]}
            cand = sorted(d for d in DIG if d not in ds)
            rng.shuffle(cand)
            pick, fb = None, False
            for d in cand:
                nst = list(st)
                nst[j] = (st[j][0], d)
                nk = key(nst)
                if nk in R and nk not in main_set and nk not in chosen:
                    pick = d
                    break
            if pick is None:
                for d in cand:
                    nst = list(st)
                    nst[j] = (st[j][0], d)
                    if key(nst) in R:
                        pick, fb = d, True
                        break
            if pick is not None:
                nst = list(st)
                nst[j] = (st[j][0], pick)
                nk = key(nst)
                chosen.add(nk)
                n_fallback += fb
                swaps.append({"slot": j, "body": "".join(f"{v}={d};" for v, d in nst), "answer": pick, "fallback": fb})
        if not swaps:
            raise RuntimeError(f"{k}: no root swap although it is in M1*")
        rows.append({"body": body, "queries": [st[0][0], st[1][0]], "answers": [st[0][1], st[1][1]], "root_swaps": swaps})
    cf = [key(stmts(s["body"])) for r in rows for s in r["root_swaps"]]
    stats = {"rng_seed": seed, "bodies": len(rows), "root_swap_pairs": len(cf), "fallback_pairs": n_fallback,
             "counterfactual_equal_to_a_main_body": sum(c in main_set for c in cf),
             "counterfactuals_repeated": len(cf) - len(set(cf))}
    return rows, stats


def serialize_test2(rows):
    return "".join(json.dumps(r, sort_keys=True) + "\n" for r in rows)


def isolation(rows, R, e1_keys, train_keys):
    """7.4 step 9: every key in R*; no key shared with E1's sets or with the
    training streams. Returns the counts (all must be 0)."""
    keys = [key(stmts(r["body"])) for r in rows] + [key(stmts(s["body"])) for r in rows for s in r["root_swaps"]]
    return {"keys_not_in_R_star": sum(k not in R for k in keys), "overlap_E1_sets": sum(k in e1_keys for k in keys),
            "overlap_training_streams": sum(k in train_keys for k in keys)}


def e1_set_keys(sets_dir):
    out = set()
    for f in sorted(os.listdir(sets_dir)):
        if not (f.endswith(".jsonl") and "k4" not in f):
            continue
        for line in open(os.path.join(sets_dir, f)):
            r = json.loads(line)
            for b in [r["body"]] + [x["body"] for x in r.get("root_swap", [])]:
                out.add(key(stmts(b)))
    return out


def training_stream_keys(seeds, updates=12000, batch=64):
    from e_task import train_rng_k2, train_sample_k2
    out = set()
    for s in seeds:
        rng = train_rng_k2(s)
        for _ in range(updates * batch):
            p, _ = train_sample_k2(rng)
            out.add(key(stmts(p.split("|")[0])))
    return out


@torch.no_grad()
def evaluate(model, rows, n_loops=None):
    """5.1 metrics on test2 of one run (eval mode, readout position)."""
    from common import grouped_bootstrap  # gate_d
    g = Geom(2)
    run = (lambda x: model(x, n_loops=n_loops)) if n_loops else model
    N = len(rows)
    x = encode([r["body"] + "|" + r["queries"][k] + "?" for r in rows for k in range(2)], g)
    y = torch.tensor([ord(r["answers"][k]) for r in rows for k in range(2)])
    pred = run(x)[:, g.READ_POS].argmax(-1)
    ok = (pred == y).view(N, 2)
    pairs = [(i, s["slot"], s) for i, r in enumerate(rows) for s in r["root_swaps"]]
    xr = encode([s["body"] + "|" + rows[i]["queries"][j] + "?" for i, j, s in pairs], g)
    yr = torch.tensor([ord(s["answer"]) for _, _, s in pairs])
    okr = (run(xr)[:, g.READ_POS].argmax(-1) == yr)
    both = [bool(ok[i, j]) and bool(okr[n]) for n, (i, j, _) in enumerate(pairs)]
    per_body, per_body_nofb = np.zeros(N), []
    for i in range(N):
        v = [b for b, (bi, _, _) in zip(both, pairs) if bi == i]
        per_body[i] = sum(v) / len(v)
        w = [b for b, (bi, _, s) in zip(both, pairs) if bi == i and not s["fallback"]]
        per_body_nofb.append(sum(w) / len(w) if w else None)
    acc_q = ok.reshape(-1).double().numpy()
    gq = np.repeat(np.arange(N), 2)
    qs = ok.all(1).double().numpy()
    insens = (pred.view(N, 2)[:, 0] == pred.view(N, 2)[:, 1]).double().numpy()
    gb = np.arange(N)
    out = {"accuracy": {"mean": float(acc_q.mean()), "ci95": grouped_bootstrap(acc_q, gq)},
           "query_swap_both": {"mean": float(qs.mean()), "ci95": grouped_bootstrap(qs, gb)},
           "root_swap_both": {"mean": float(per_body.mean()), "ci95": grouped_bootstrap(per_body, gb),
                              "weighting": "per main body (each body weight 1; its 1-2 pairs averaged)"},
           "root_swap_both_pair_weighted": float(np.mean(both)),
           "root_swap_pairs": len(pairs),
           "query_insensitivity": {"mean": float(insens.mean()), "ci95": grouped_bootstrap(insens, gb)}}
    nofb = [v for v in per_body_nofb if v is not None]
    out["sensitivity_without_fallback"] = {"bodies": len(nofb), "root_swap_both": float(np.mean(nofb)) if nofb else None}
    m = out
    out["learned"] = (m["accuracy"]["mean"] >= LEARNED["accuracy"] and m["root_swap_both"]["mean"] >= LEARNED["root_swap_both"]
                      and m["query_swap_both"]["mean"] >= LEARNED["query_swap_both"])
    if out["learned"]:
        out["level"] = "学会"
    elif m["accuracy"]["ci95"][0] > BASELINE and m["query_insensitivity"]["mean"] < 0.9:
        out["level"] = "出现学习迹象"
    else:
        out["level"] = "未满足综合学习迹象标准"
    if nofb:
        out["sensitivity_without_fallback"]["learned"] = (m["accuracy"]["mean"] >= 0.9 and float(np.mean(nofb)) >= 0.8
                                                          and m["query_swap_both"]["mean"] >= 0.8)
    return out
