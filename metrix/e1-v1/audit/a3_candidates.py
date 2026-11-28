# data-auditor, E1-V1 round 1, item 3: candidate feasibility under the four constraints
# (same relation, same stratum, same exposure class, same answer token count), plus a check that
# every candidate list of candidates.json satisfies them and that the scored candidate ids are the
# same in the QA context and in the TRAIN closed-book context (equal-length scoring).
import json
import sys

sys.path.insert(0, "/home/user/OpenMythos/metrix/e1-v1/audit")
import audit_lib as A  # noqa: E402

D = A.TMP + "/v1data"


def main():
    dm = A.load_json(A.V1 + "/DATA_MANIFEST.json")
    sm = A.load_json(A.V1 + "/SPLIT_MANIFEST.json")
    tok = A.load_qwen_tokenizer(dm["model"]["tokenizer"]["files_sha256"])
    facts = A.read_jsonl(D + "/facts.jsonl")
    with open(D + "/candidates.json", encoding="utf-8") as f:
        C = json.load(f)
    Q = A.read_jsonl(D + "/dev_qa.jsonl")
    F = A.read_jsonl(D + "/train_F.jsonl")
    enc = lambda s: tok.encode(s, add_special_tokens=False)  # noqa: E731
    kst = {f["fact_id"]: len(enc(" " + f["answer"])) for f in facts}
    kqa = {f["fact_id"]: len(enc(f["answer"])) for f in facts}
    by_answer = {f["answer"]: f for f in facts}

    # pool sizes under the four constraints
    print("cell (relation/stratum/exposure): facts | distinct K_st | pool (other answers, 4 constraints, K_st) min/max | candidates available incl. own answer min | (K_st, K_qa) pool min")
    overall_min, short = 10 ** 9, []
    for rel in A.RELATIONS:
        for st in A.STRATA:
            for ex in ("learned", "unread"):
                cell = [f for f in facts if f["relation"] == rel and f["stratum"] == st and f["exposure"] == ex]
                pools = []
                pools2 = []
                for f in cell:
                    p = [g for g in cell if g["fact_id"] != f["fact_id"] and kst[g["fact_id"]] == kst[f["fact_id"]]]
                    p2 = [g for g in p if kqa[g["fact_id"]] == kqa[f["fact_id"]]]
                    pools.append(len(p))
                    pools2.append(len(p2))
                ks = sorted({kst[f["fact_id"]] for f in cell})
                mn = min(pools)
                overall_min = min(overall_min, mn)
                if mn < 4:  # protocol rule: pool of other answers < 4 -> IMPLEMENTATION_FAIL (also covers < 4 candidates)
                    short.append((rel, st, ex, mn))
                print(f"  {rel}/{st}/{ex}: {len(cell)} | K_st {ks} | pool {min(pools)}/{max(pools)} | candidates {mn + 1} | {min(pools2)}")
    print("minimum pool (other answers) over all 320 facts:", overall_min, "| minimum candidates incl. own answer:", overall_min + 1)
    print("cells with a pool of other answers < 4 (protocol IMPLEMENTATION_FAIL rule; includes any cell with < 4 candidates):", short)
    print("note: protocol 2.5 / Pilot 2.5 rule 'pool < 4 -> IMPLEMENTATION_FAIL' counts the other answers; pool sizes per manifest", sm["candidates"]["pool_sizes"])

    # candidates.json obeys the constraints
    bad, nfacts = 0, 0
    for f in facts:
        nfacts += 1
        c = C[f["fact_id"]]
        ok = len(c) == 4 and len(set(c)) == 4 and f["answer"] in c
        for x in c:
            g = by_answer.get(x)
            ok &= g is not None and g["relation"] == f["relation"] and g["stratum"] == f["stratum"] and g["exposure"] == f["exposure"]
            ok &= len(enc(" " + x)) == kst[f["fact_id"]]
        bad += not ok
    print(f"candidates.json: facts {nfacts} keys {len(C)} | lists violating (4 distinct, own answer included, same relation/stratum/exposure, same K_st): {bad}")
    pos = {}
    for f in facts:
        i = C[f["fact_id"]].index(f["answer"])
        pos[i] = pos.get(i, 0) + 1
    print("position of the true answer among the 4 candidates (report only):", dict(sorted(pos.items())))

    # in-context ids: QA context and TRAIN closed-book context
    fact_by_id = {f["fact_id"]: f for f in facts}
    n, total, mism, lens_differ = 0, 0, 0, 0
    for q in Q:
        f = fact_by_id[q["fact_id"]]
        ctx = tok.apply_chat_template([{"role": "user", "content": q["question"]}], tokenize=False,
                                      add_generation_prompt=True, enable_thinking=False) + "The answer is"
        cids = enc(ctx)
        L = set()
        for c in C[f["fact_id"]]:
            full = enc(ctx + " " + c)
            n += 1
            total += len(full)
            tail = enc(" " + c)
            if full[:len(cids)] != cids or full[len(cids):] != tail:
                mism += 1
            L.add(len(full) - len(cids))
        lens_differ += len(L) != 1
    print(f"DEV-QA scored sequences n {n} total ids {total} mean {total / n:.3f} | context+candidate ids != context ids + encode(' '+c): {mism} | questions whose 4 scored lengths differ: {lens_differ}")
    tb = A.templates_by(sm["templates"])
    n2, total2, mism2, statement_mism = 0, 0, 0, 0
    for r in F:
        f = fact_by_id[r["fact_id"]]
        t = tb[(f["relation"], "TRAIN")][0]["text"]
        prefix = t.split("{A}")[0].rstrip(" ").replace("{E}", f["entity"])
        pids = enc(prefix)
        for c in C[f["fact_id"]]:
            full = enc(prefix + " " + c)
            n2 += 1
            total2 += len(full)
            if full[:len(pids)] != pids or full[len(pids):] != enc(" " + c):
                mism2 += 1
        # the answer ids inside the actual TRAIN statement equal encode(' ' + answer)
        sids = enc(r["text"])
        a_ids = enc(" " + f["answer"])
        if sids[len(pids):len(pids) + len(a_ids)] != a_ids or sids[:len(pids)] != pids:
            statement_mism += 1
    print(f"TRAIN closed-book sequences n {n2} total ids {total2} mean {total2 / n2:.3f} | prefix+candidate ids != prefix ids + encode(' '+c): {mism2}")
    print(f"TRAIN statements whose answer ids differ from encode(' ' + answer) after prefix(f): {statement_mism} of {len(F)}")
    print("Executor (v1_data_check.txt): DEV-QA n 2560 sum 78032 mean 30.481; TRAIN closed-book n 960 sum 13288 mean 13.842")
    print("ITEM3:", "OK" if (overall_min >= 4 and not short and bad == 0 and mism == 0 and mism2 == 0 and statement_mism == 0
                             and n == 2560 and total == 78032 and n2 == 960 and total2 == 13288) else "CHECK OUTPUT")


if __name__ == "__main__":
    main()
