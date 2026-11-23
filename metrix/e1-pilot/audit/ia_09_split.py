"""IA-9 (audit item 4): split.  Run on the auditor's own data and on the Executor's files (data only).
  fact_ids: 160 distinct; format E1P-<L|U>-<relation>-<nat|rnd>-<NN>; learned 120 / unread 40, per cell 15 + 5
            (L 01..15, U 01..05); exposure field consistent with the L/U letter; learned and unread disjoint.
  TRAIN (train_F 120, train_S 120, train_Y 240): only learned fact_ids; train_F and train_S each learned fact exactly
            once; train_S answer_fact_id a learned fact of the same cell, never itself, each once; train_Y each learned
            fact exactly twice (Y_ENTITY + Y_ANSWER).
  DEV (dev_qa 320): every one of the 160 facts exactly twice, once per DEV template of its relation.
  candidates: 160 keys == fact_ids.  general DEV: 100 windows, 25 per domain.  anchor: 512 documents.
  TEST: no test_qa.jsonl / general_test.jsonl exists in the Executor's directory (only the directory listing is read)
        and SPLIT_MANIFEST split_sha256 (working tree) is still null for test_qa.jsonl.
Counts are compared with the protocol (2.1, 2.3, 2.6, 2.7) and the freeze-commit manifests.
Data Auditor's own script; no Executor code imported, called or copied.
usage: python -I ia_09_split.py <repo_root> <my_out_dir> <executor_dir>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json, re
from collections import Counter
from ia_common import RELS, STRATA, DOMAINS, frozen_json, read_jsonl, run

ID_RE = re.compile(r"E1P-(L|U)-(capital|currency|founder|river)-(nat|rnd)-(\d\d)")


def check(label, facts, F_ids, S_rows, Y_rows, D_rows, cand_keys, gen_domains, n_anchor, dev_t):
    ok = True
    ids = [f["fact_id"] for f in facts]
    fmt = all(ID_RE.fullmatch(i) for i in ids)
    lu = all((ID_RE.fullmatch(f["fact_id"]).group(1) == "L") == (f["exposure"] == "learned") and
             ID_RE.fullmatch(f["fact_id"]).group(2) == f["relation"] and
             ID_RE.fullmatch(f["fact_id"]).group(3) == {"natural": "nat", "random": "rnd"}[f["stratum"]] for f in facts)
    L = {f["fact_id"] for f in facts if f["exposure"] == "learned"}
    U = {f["fact_id"] for f in facts if f["exposure"] == "unread"}
    cells = Counter((f["relation"], f["stratum"], f["exposure"]) for f in facts)
    cell_ok = all(cells[(r, s, "learned")] == 15 and cells[(r, s, "unread")] == 5 for r in RELS for s in STRATA)
    seq_ok = all(sorted(int(i[-2:]) for i in ids if i.startswith(f"E1P-{x}-{r}-{s}-")) == list(range(1, n + 1))
                 for x, n in (("L", 15), ("U", 5)) for r in RELS for s in ("nat", "rnd"))
    print(f"[{label}] facts {len(ids)} distinct {len(set(ids))} | learned {len(L)} unread {len(U)} | learned & unread {len(L & U)} "
          f"| id format {fmt} | L/U letter, relation, stratum consistent {lu} | 8 cells x (15 + 5) {cell_ok} | indices L01-15, U01-05 {seq_ok}")
    ok &= len(ids) == 160 == len(set(ids)) and len(L) == 120 and len(U) == 40 and not (L & U) and fmt and lu and cell_ok and seq_ok
    cell_of = {f["fact_id"]: (f["relation"], f["stratum"]) for f in facts}
    fF, fS, fY = Counter(F_ids), Counter(r["fact_id"] for r in S_rows), Counter(r["fact_id"] for r in Y_rows)
    aS = Counter(r["answer_fact_id"] for r in S_rows)
    tr_ok = (len(F_ids) == 120 and set(fF) == L and set(fF.values()) == {1} and len(S_rows) == 120 and set(fS) == L
             and set(fS.values()) == {1} and set(aS) == L and set(aS.values()) == {1}
             and all(r["fact_id"] != r["answer_fact_id"] and cell_of[r["fact_id"]] == cell_of[r["answer_fact_id"]] for r in S_rows)
             and len(Y_rows) == 240 and set(fY) == L and set(fY.values()) == {2}
             and all(sorted(r["kind"] for r in Y_rows if r["fact_id"] == i) == ["Y_ANSWER", "Y_ENTITY"] for i in L))
    unread_in_train = sorted((set(fF) | set(fS) | set(aS) | set(fY)) & U)
    print(f"[{label}] TRAIN: train_F {len(F_ids)} | train_S {len(S_rows)} | train_Y {len(Y_rows)} | unread fact_ids in TRAIN files "
          f"{unread_in_train} | each learned fact once in F and S, once as S answer (same cell, not itself), twice in Y "
          f"(Y_ENTITY + Y_ANSWER): {tr_ok}")
    ok &= tr_ok and not unread_in_train
    fD = Counter(r["fact_id"] for r in D_rows)
    dev_ok = (len(D_rows) == 320 and set(fD) == set(ids) and set(fD.values()) == {2}
              and all(sorted(r["template_id"] for r in D_rows if r["fact_id"] == f["fact_id"]) == dev_t[f["relation"]] for f in facts))
    print(f"[{label}] DEV: dev_qa {len(D_rows)} | every fact twice, once per DEV template of its relation: {dev_ok} | "
          f"learned {sum(fD[i] for i in L)} unread {sum(fD[i] for i in U)}")
    ok &= dev_ok
    gd = Counter(gen_domains)
    print(f"[{label}] candidates keys {len(cand_keys)} == fact_ids {set(cand_keys) == set(ids)} | general DEV windows {len(gen_domains)} "
          f"per domain {dict(gd)} | anchor documents {n_anchor}")
    ok &= set(cand_keys) == set(ids) and len(cand_keys) == 160 and len(gen_domains) == 100 and all(gd[d] == 25 for d in DOMAINS) and n_anchor == 512
    return ok


def main():
    repo, mine, exdir = sys.argv[1:4]
    ok = True
    dm, sm = frozen_json(repo, "DATA_MANIFEST.json"), frozen_json(repo, "SPLIT_MANIFEST.json")
    print("freeze-commit facts:", {k: dm["facts"][k] for k in ("total", "learned", "unread", "per_cell")})
    print("freeze-commit SPLIT_MANIFEST fact_ids:", sm["fact_ids"])
    print("freeze-commit DATA_MANIFEST files contents:", {k: v["content"] for k, v in dm["files"].items()})
    ok &= (dm["facts"]["total"], dm["facts"]["learned"], dm["facts"]["unread"]) == (160, 120, 40)
    dev_t = {r: sorted(t["template_id"] for t in sm["templates"] if t["relation"] == r and t["kind"] == "DEV") for r in RELS}

    facts = json.load(open(os.path.join(mine, "facts.json"), encoding="utf-8"))
    ok &= check("auditor", facts, [r["fact_id"] for r in json.load(open(os.path.join(mine, "train_F.json"), encoding="utf-8"))],
                read_jsonl(os.path.join(mine, "train_S.jsonl")), json.load(open(os.path.join(mine, "train_Y.json"), encoding="utf-8")),
                json.load(open(os.path.join(mine, "dev_qa.json"), encoding="utf-8")),
                list(json.load(open(os.path.join(mine, "candidates.json"), encoding="utf-8"))),
                [g["domain"] for g in json.load(open(os.path.join(mine, "general.json"), encoding="utf-8"))],
                len(json.load(open(os.path.join(mine, "anchor.json"), encoding="utf-8"))), dev_t)
    ok &= check("Executor", read_jsonl(os.path.join(exdir, "facts.jsonl")),
                [r["fact_id"] for r in read_jsonl(os.path.join(exdir, "train_F.jsonl"))],
                read_jsonl(os.path.join(exdir, "train_S.jsonl")), read_jsonl(os.path.join(exdir, "train_Y.jsonl")),
                read_jsonl(os.path.join(exdir, "dev_qa.jsonl")),
                list(json.load(open(os.path.join(exdir, "candidates.json"), encoding="utf-8"))),
                [g["domain"] for g in read_jsonl(os.path.join(exdir, "general_dev.jsonl"))],
                len(read_jsonl(os.path.join(exdir, "anchor_text.jsonl"))), dev_t)
    listing = sorted(os.listdir(exdir))
    test_files = [x for x in listing if "test" in x.lower()]
    print("Executor directory listing:", listing, "| files with 'test' in the name:", test_files)
    ok &= not test_files
    wt_sm = json.load(open(os.path.join(repo, "metrix/e1-pilot/SPLIT_MANIFEST.json"), encoding="utf-8"))
    print("working-tree SPLIT_MANIFEST split_sha256:", wt_sm["split_sha256"])
    ok &= wt_sm["split_sha256"].get("test_qa.jsonl") is None
    return bool(ok)


run(main)
