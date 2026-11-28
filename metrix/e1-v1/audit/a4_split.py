# data-auditor, E1-V1 round 1, item 4: split checks (fact_id exclusivity, per-cell learned / unread
# counts, per-split counts against protocol 2.1, 2.3, 2.6, 7.2 and the manifests).
import re
import sys

sys.path.insert(0, "/home/user/OpenMythos/metrix/e1-v1/audit")
import audit_lib as A  # noqa: E402

D = A.TMP + "/v1data"


def chk(label, got, exp):
    ok = got == exp
    print(f"{'OK  ' if ok else 'DIFF'} {label}: got {got} | expected {exp}")
    return ok


def main():
    dm = A.load_json(A.V1 + "/DATA_MANIFEST.json")
    sm = A.load_json(A.V1 + "/SPLIT_MANIFEST.json")
    gm = A.load_json(A.V1 + "/DAMAGE_MANIFEST.json")
    facts = A.read_jsonl(D + "/facts.jsonl")
    F = A.read_jsonl(D + "/train_F.jsonl")
    Sx = A.read_jsonl(D + "/train_S.jsonl")
    Y = A.read_jsonl(D + "/train_Y.jsonl")
    Q = A.read_jsonl(D + "/dev_qa.jsonl")
    gdev = A.read_jsonl(D + "/general_dev.jsonl")
    d2m = A.read_jsonl(D + "/d2_dev.jsonl")
    d2a = A.read_jsonl(D + "/d2_dev_arc.jsonl")
    ok = True
    fm = dm["facts"]
    ids = [f["fact_id"] for f in facts]
    ok &= chk("fact_ids unique", len(set(ids)), len(ids))
    pat = re.compile(r"^E1V1-(L|U)-(capital|currency|founder|river)-(nat|rnd)-(\d\d)$")
    badfmt = [i for i in ids if not pat.match(i)]
    ok &= chk("fact_ids not matching E1V1-<L|U>-<relation>-<nat|rnd>-<NN>", len(badfmt), 0)
    cons = sum(1 for f in facts if (pat.match(f["fact_id"]).group(1) == "L") != (f["exposure"] == "learned")
               or pat.match(f["fact_id"]).group(2) != f["relation"]
               or pat.match(f["fact_id"]).group(3) != A.STRAT_SHORT[f["stratum"]])
    ok &= chk("fact_id prefix inconsistent with exposure / relation / stratum fields", cons, 0)
    L = {f["fact_id"] for f in facts if f["exposure"] == "learned"}
    U = {f["fact_id"] for f in facts if f["exposure"] == "unread"}
    ok &= chk("learned ∩ unread", len(L & U), 0)
    ok &= chk("total facts", len(facts), fm["total"])
    ok &= chk("learned", len(L), fm["learned"])
    ok &= chk("unread", len(U), fm["unread"])
    for rel in A.RELATIONS:
        for st in A.STRATA:
            cell = [f for f in facts if f["relation"] == rel and f["stratum"] == st]
            nl = [f for f in cell if f["exposure"] == "learned"]
            nu = [f for f in cell if f["exposure"] == "unread"]
            seq_l = [int(f["fact_id"][-2:]) for f in nl]
            seq_u = [int(f["fact_id"][-2:]) for f in nu]
            good = len(nl) == fm["per_cell"]["learned"] and len(nu) == fm["per_cell"]["unread"] and seq_l == list(range(1, 31)) and seq_u == list(range(1, 11))
            # generation order: learned 01-30 first, then unread 01-10
            order_ok = [f["exposure"] for f in cell] == ["learned"] * 30 + ["unread"] * 10
            print(f"  cell {rel}/{st}: learned {len(nl)} (01..30 {seq_l == list(range(1, 31))}) unread {len(nu)} (01..10 {seq_u == list(range(1, 11))}) order learned-then-unread {order_ok}")
            ok &= good and order_ok
    for st in A.STRATA:
        print(f"  stratum {st}: facts {sum(1 for f in facts if f['stratum'] == st)} learned {sum(1 for f in facts if f['stratum'] == st and f['exposure'] == 'learned')} unread {sum(1 for f in facts if f['stratum'] == st and f['exposure'] == 'unread')}")
    ok &= all(sum(1 for f in facts if f["stratum"] == st and f["exposure"] == "learned") == 120 for st in A.STRATA)
    ok &= all(sum(1 for f in facts if f["stratum"] == st and f["exposure"] == "unread") == 40 for st in A.STRATA)

    tset = {t["template_id"]: t["set"] for t in sm["templates"]}
    # TRAIN
    fF = [r["fact_id"] for r in F]
    ok &= chk("train_F rows", len(F), 240)
    ok &= chk("train_F: every learned fact exactly once", sorted(fF) == sorted(L), True)
    ok &= chk("train_F rows of unread facts", sum(1 for x in fF if x in U), 0)
    ok &= chk("train_F rows not using a TRAIN template", sum(1 for r in F if tset[r["template_id"]] != "TRAIN"), 0)
    ok &= chk("train_S rows", len(Sx), 240)
    ok &= chk("train_S fact_id / answer_fact_id of unread facts", sum(1 for r in Sx if r["fact_id"] in U or r["answer_fact_id"] in U), 0)
    ok &= chk("train_S fixed points (fact_id == answer_fact_id)", sum(1 for r in Sx if r["fact_id"] == r["answer_fact_id"]), 0)
    ok &= chk("train_S answer_fact_id outside the fact's cell", sum(1 for r in Sx if r["fact_id"][:-3] != r["answer_fact_id"][:-3]), 0)
    ok &= chk("train_S: fact_id and answer_fact_id each a permutation of the learned set",
              sorted(r["fact_id"] for r in Sx) == sorted(L) and sorted(r["answer_fact_id"] for r in Sx) == sorted(L), True)
    ok &= chk("train_Y rows", len(Y), 480)
    yk = {}
    for r in Y:
        yk[(r["fact_id"], r["kind"])] = yk.get((r["fact_id"], r["kind"]), 0) + 1
    ok &= chk("train_Y: every learned fact one Y_ENTITY and one Y_ANSWER", all(yk.get((f, k)) == 1 for f in L for k in ("Y_ENTITY", "Y_ANSWER")) and len(yk) == 480, True)
    ok &= chk("train_Y rows not using a Y template", sum(1 for r in Y if tset[r["template_id"]] != "Y"), 0)
    # DEV
    ok &= chk("dev_qa rows (320 x 2)", len(Q), 640)
    qc = {}
    for r in Q:
        qc[r["fact_id"]] = qc.get(r["fact_id"], 0) + 1
    ok &= chk("dev_qa: every fact (learned and unread) exactly 2 questions", all(qc.get(i) == 2 for i in ids) and len(qc) == 320, True)
    ok &= chk("dev_qa rows not using a DEV template", sum(1 for r in Q if tset[r["template_id"]] != "DEV"), 0)
    ok &= chk("dev_qa distinct (fact_id, template_id)", len({(r["fact_id"], r["template_id"]) for r in Q}), 640)
    ntest = sum(1 for t in sm["templates"] if t["set"] == "TEST")
    print(f"TEST templates {ntest} (3 per relation) -> TEST-QA would be 320 x 3 = {320 * 3} questions (protocol 5: 960); not generated")
    ok &= chk("TEST templates per relation", {rel: sum(1 for t in sm["templates"] if t["set"] == "TEST" and t["relation"] == rel) for rel in A.RELATIONS}, {r: 3 for r in A.RELATIONS})
    import os
    tfiles = [n for n in ("test_qa.jsonl", "general_test.jsonl", "d2_test.jsonl") if os.path.exists(D + "/" + n)]
    ok &= chk("TEST files generated by the auditor", tfiles, [])
    # damage DEV sets
    per = {}
    for w in gdev:
        per[w["domain"]] = per.get(w["domain"], 0) + 1
    ok &= chk("D1 DEV windows per domain", per, {d: 100 for d in gm["d1"]["domains"]})
    ok &= chk("D1 DEV doc_ids unique", len({w["doc_id"] for w in gdev}), 400)
    ok &= chk("D1 DEV doc_ids not of the form <domain>-dev-NNN", sum(1 for w in gdev if not re.match(r"^" + w["domain"] + r"-dev-\d{3}$", w["doc_id"])), 0)
    ok &= chk("D1 DEV windows with > 256 ids", sum(1 for w in gdev if len(w["ids"]) > 256), 0)
    ok &= chk("D2 DEV MMLU items", len(d2m), 800)
    ok &= chk("D2 DEV MMLU distinct source_row", len({x["source_row"] for x in d2m}), 800)
    ok &= chk("D2 DEV MMLU item numbering 0..799", [x["item"] for x in d2m] == list(range(800)), True)
    ok &= chk("D2 DEV MMLU distinct prompts", len({x["prompt"] for x in d2m}), 800)
    ok &= chk("D2 DEV ARC items", len(d2a), 800)
    ok &= chk("D2 DEV ARC distinct source_row", len({x["source_row"] for x in d2a}), 800)
    ok &= chk("D2 DEV ARC distinct prompts", len({x["prompt"] for x in d2a}), 800)
    ok &= chk("D2 DEV answer letters all in A-D", all(x["answer"] in "ABCD" and len(x["answer"]) == 1 for x in d2m + d2a), True)
    # duplicate prompts in DEV for MMLU (relevant for the TEST rule 'exclude items whose prompt equals a DEV prompt')
    print("ITEM4:", "ALL MATCH" if ok else "MISMATCH PRESENT")


if __name__ == "__main__":
    main()
