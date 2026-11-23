"""IA-8 (audit item 3): candidate feasibility under the four constraints (same relation, same stratum, same exposure
class, same answer token count).  Answer token count = K_st = len(encode(" " + answer)) (the scored span, protocol
2.2 / section 5); K_qa = len(encode(answer)) is reported too.
  cell = (relation, stratum, exposure): 16 cells (8 learned cells of 15 facts, 8 unread cells of 5 facts).
  per fact: available = answers of the facts of its cell with the same K_st, its own answer included;
            distractor pool = available - 1 (protocol 2.5: a pool with fewer than 4 answers is IMPLEMENTATION_FAIL;
            the protocol pool is defined without the token-count constraint, the token count is equal inside a
            relation x stratum by the answer rule of 2.2 - checked here).
  reports per cell: min available, min pool; lists cells with available < 4 and cells with pool < 4.
Also every candidate list (the auditor's candidates.json and the Executor's) is checked: 4 distinct strings, the true
answer once, all from the fact's cell, all with the same K_st and K_qa.
Data Auditor's own script; no Executor code imported, called or copied.
usage: python -I ia_08_feasibility.py <qwen_tok_dir> <my_out_dir> <executor_dir>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json
from collections import Counter
from ia_common import RELS, STRATA, load_qwen, enc, read_jsonl, run


def main():
    qdir, mine, exdir = sys.argv[1:4]
    ok = True
    tok = load_qwen(qdir)
    facts = json.load(open(os.path.join(mine, "facts.json"), encoding="utf-8"))
    K = {f["answer"]: (len(enc(tok, " " + f["answer"])), len(enc(tok, f["answer"]))) for f in facts}
    kfile = json.load(open(os.path.join(mine, "facts_k.json"), encoding="utf-8"))
    ok &= all(tuple(kfile[f["fact_id"]]) == K[f["answer"]] for f in facts)
    print(f"{'cell':<34} {'n':>3} {'K_st/K_qa values':<22} {'min available':>13} {'min pool':>9}")
    low_avail, low_pool, all_min_avail, all_min_pool = [], [], 99, 99
    for rel in RELS:
        for st in STRATA:
            ks = Counter(K[f["answer"]] for f in facts if (f["relation"], f["stratum"]) == (rel, st))
            for ex in ("learned", "unread"):
                cell = [f for f in facts if (f["relation"], f["stratum"], f["exposure"]) == (rel, st, ex)]
                avail = [sum(1 for g in cell if K[g["answer"]][0] == K[f["answer"]][0]) for f in cell]
                pool_proto = [len(cell) - 1 for _ in cell]
                ma, mp = min(avail), min(avail) - 1
                all_min_avail, all_min_pool = min(all_min_avail, ma), min(all_min_pool, mp)
                name = f"{rel}/{st}/{ex}"
                print(f"{name:<34} {len(cell):>3} {str(dict(Counter(K[f['answer']] for f in cell))):<22} {ma:>13} {mp:>9}"
                      f"   (protocol pool without the token constraint: {min(pool_proto)})")
                if ma < 4:
                    low_avail.append(name)
                if mp < 4:
                    low_pool.append(name)
            print(f"  relation x stratum {rel}/{st}: (K_st, K_qa) over all 20 answers {dict(ks)}")
            ok &= len(ks) == 1
    print("minimum available candidates per fact (incl. the true answer):", all_min_avail, "| cells with available < 4:", low_avail)
    print("minimum distractor pool per fact:", all_min_pool, "| cells with pool < 4:", low_pool)
    ok &= not low_avail and not low_pool
    print(f"AUDIT_VALUE feasibility:min_available {all_min_avail}")
    print(f"AUDIT_VALUE feasibility:min_pool {all_min_pool}")
    by_id = {f["fact_id"]: f for f in facts}
    for label, cands in (("auditor candidates.json", json.load(open(os.path.join(mine, "candidates.json"), encoding="utf-8"))),
                         ("Executor candidates.json", json.load(open(os.path.join(exdir, "candidates.json"), encoding="utf-8")))):
        bad = []
        for fid, c in cands.items():
            f = by_id.get(fid)
            if f is None:
                bad.append((fid, "unknown fact_id"))
                continue
            cellans = {g["answer"] for g in facts if (g["relation"], g["stratum"], g["exposure"]) == (f["relation"], f["stratum"], f["exposure"])}
            kc = {(len(enc(tok, " " + x)), len(enc(tok, x))) for x in c}
            if not (len(c) == 4 and len(set(c)) == 4 and c.count(f["answer"]) == 1 and set(c) <= cellans and len(kc) == 1):
                bad.append((fid, c))
        pos = Counter(c.index(by_id[fid]["answer"]) for fid, c in cands.items() if fid in by_id)
        print(f"{label}: keys {len(cands)} | lists violating the four constraints {bad[:5]} (count {len(bad)}) | "
              f"position of the true answer {dict(sorted(pos.items()))}")
        ok &= len(cands) == 160 and set(cands) == set(by_id) and not bad
    return bool(ok)


run(main)
