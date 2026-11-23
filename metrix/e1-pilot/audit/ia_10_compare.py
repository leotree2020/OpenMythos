"""IA-10: comparison of the auditor's independently generated data with the Executor's generated files.
A. four frozen hashes, three ways (auditor value | value recomputed from the Executor's file by the protocol method |
   frozen value of the freeze-commit manifests):
   facts      : facts.jsonl read in line order, each line exactly the 6 fields fact_id, exposure, relation, stratum,
                entity, answer -> JSON list -> canonical SHA-256 (protocol 2.2 "fact 哈希的比对方法"); the JSONL
                canonical hash of facts.jsonl is a different byte string and is only printed;
   train_S    : train_S.jsonl parsed -> canonical JSONL SHA-256 (protocol 2.6, section 0);
   candidates : candidates.json parsed -> canonical JSON SHA-256 (protocol 2.5);
   anchor     : anchor_text.jsonl in file order (doc must equal the line index) -> list of the 512 "text" fields ->
                canonical SHA-256 (DATA_MANIFEST anchor_text.decoded_texts_hash_rule); the same with the auditor's
                decode of the Executor's "ids".
B. files without a frozen hash: contents only (text, id sequences, order, count; record field names are not
   prescribed by the protocol): train_F (fact_id, text), train_Y (fact_id, kind, text), dev_qa (fact_id,
   template_id, question), general_dev (domain, source doc_id, ids, text), anchor_text (source row, ids, text);
   template_id fields of the Executor are checked against the template used.
C. informational: byte_sha256 vs canonical_sha256 of every Executor file; gen2 / gen3 byte-identical to gen1.
Data Auditor's own script; no Executor code imported, called or copied.
usage: python -I ia_10_compare.py <repo_root> <qwen_tok_dir> <my_out_dir> <executor_dir> [<other executor dirs>...]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json
from ia_common import sha, canon, jsonl_bytes, file_sha, frozen_json, read_jsonl, load_qwen, run

FACT_FIELDS = ["fact_id", "exposure", "relation", "stratum", "entity", "answer"]


def first_diff(a, b):
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            return i, x, y
    return (None if len(a) == len(b) else (min(len(a), len(b)), "length", (len(a), len(b))))


def main():
    repo, qdir, mine, exdir = sys.argv[1:5]
    others = sys.argv[5:]
    ok = True
    dm, sm = frozen_json(repo, "DATA_MANIFEST.json"), frozen_json(repo, "SPLIT_MANIFEST.json")
    frozen = {"facts": dm["name_generation"]["expected_facts_canonical_sha256"],
              "train_S": dm["s_permutation"]["expected_train_S_canonical_sha256"],
              "candidates": sm["candidates"]["candidate_mapping_sha256"],
              "anchor_texts": dm["anchor_text"]["decoded_texts_canonical_sha256"]}
    tok = load_qwen(qdir)
    J = lambda name: json.load(open(os.path.join(mine, name), encoding="utf-8"))
    E = lambda name: os.path.join(exdir, name)

    print("== A. four frozen hashes: auditor | from the Executor's file | frozen")
    my_facts = J("facts.json")
    ex_lines = read_jsonl(E("facts.jsonl"))
    keys_ok = all(sorted(r) == sorted(FACT_FIELDS) for r in ex_lines)
    ex_facts = [{k: r[k] for k in FACT_FIELDS} for r in ex_lines]
    my_s = read_jsonl(os.path.join(mine, "train_S.jsonl"))
    ex_s = read_jsonl(E("train_S.jsonl"))
    my_c = J("candidates.json")
    ex_c = json.load(open(E("candidates.json"), encoding="utf-8"))
    my_a = J("anchor.json")
    ex_a = read_jsonl(E("anchor_text.jsonl"))
    doc_ok = [r["doc"] for r in ex_a] == list(range(len(ex_a)))
    vals = {
        "facts": (sha(canon(my_facts)), sha(canon(ex_facts))),
        "train_S": (sha(jsonl_bytes(my_s)), sha(jsonl_bytes(ex_s))),
        "candidates": (sha(canon(my_c)), sha(canon(ex_c))),
        "anchor_texts": (sha(canon([a["text"] for a in my_a])), sha(canon([r["text"] for r in ex_a]))),
    }
    print(f"facts.jsonl: {len(ex_lines)} lines, every line exactly the 6 fields: {keys_ok}; anchor_text.jsonl doc == line index: {doc_ok}")
    ok &= keys_ok and doc_ok and len(ex_lines) == 160 and len(ex_a) == 512
    for k, (m, e) in vals.items():
        same = m == e == frozen[k]
        ok &= same
        print(f"  {k:<12} auditor {m} | Executor file {e} | frozen {frozen[k]} | ALL THREE EQUAL {same}")
        print(f"AUDIT_VALUE compare:{k} auditor={m} executor={e} frozen={frozen[k]}")
    dec = sha(canon([tok.decode(r["ids"]) for r in ex_a]))
    print(f"  anchor texts from the auditor's decode of the Executor's ids: {dec} | == frozen {dec == frozen['anchor_texts']}")
    ok &= dec == frozen["anchor_texts"]
    print(f"  facts.jsonl JSONL canonical sha256 (not compared with the fact value, protocol 2.2): {sha(jsonl_bytes(ex_lines))}")
    print(f"  element-wise equal: facts {my_facts == ex_facts} | train_S records {my_s == ex_s} | candidates {my_c == ex_c} "
          f"| candidates key order {list(my_c) == list(ex_c)}")
    ok &= my_facts == ex_facts and my_s == ex_s and my_c == ex_c

    print("\n== B. files without a frozen hash (contents only)")
    tmpl = {t["template_id"]: t for t in sm["templates"]}
    rel_of = {f["fact_id"]: f["relation"] for f in my_facts}

    def cmp(name, mine_seq, ex_seq, extra=""):
        same = mine_seq == ex_seq
        d = None if same else first_diff(mine_seq, ex_seq)
        print(f"  {name}: auditor {len(mine_seq)} | Executor {len(ex_seq)} | identical sequence {same}"
              f"{'' if same else f' | first difference {d!r}'}"
              f"{'' if same else f' | same multiset {sorted(map(repr, mine_seq)) == sorted(map(repr, ex_seq))}'}{extra}")
        return same

    eF = read_jsonl(E("train_F.jsonl"))
    ok &= cmp("train_F (fact_id, text)", [(r["fact_id"], r["text"]) for r in J("train_F.json")], [(r["fact_id"], r["text"]) for r in eF])
    tF = all(r["template_id"] == f"{rel_of[r['fact_id']]}.TRAIN.1" for r in eF)
    print(f"    Executor train_F template_id == <relation>.TRAIN.1: {tF}")
    eY = read_jsonl(E("train_Y.jsonl"))
    ok &= cmp("train_Y (fact_id, kind, text)", [(r["fact_id"], r["kind"], r["text"]) for r in J("train_Y.json")],
              [(r["fact_id"], r["kind"], r["text"]) for r in eY])
    tY = all(r["template_id"] == f"{rel_of[r['fact_id']]}.{r['kind']}.1" and tmpl[r["template_id"]]["kind"] == r["kind"] for r in eY)
    print(f"    Executor train_Y template_id == <relation>.<kind>.1: {tY}")
    eD = read_jsonl(E("dev_qa.jsonl"))
    ok &= cmp("dev_qa (fact_id, template_id, question)", [(r["fact_id"], r["template_id"], r["question"]) for r in J("dev_qa.json")],
              [(r["fact_id"], r["template_id"], r["question"]) for r in eD])
    tD = all(tmpl[r["template_id"]]["kind"] == "DEV" and tmpl[r["template_id"]]["relation"] == rel_of[r["fact_id"]] for r in eD)
    print(f"    Executor dev_qa template_id is a DEV template of the fact's relation: {tD}")
    ok &= tF and tY and tD
    my_g = J("general.json")
    eG = read_jsonl(E("general_dev.jsonl"))
    ok &= cmp("general_dev (domain, source doc_id, ids)", [(g["domain"], g["doc_id"], g["ids"]) for g in my_g],
              [(r["domain"], r["doc_id"], r["ids"]) for r in eG])
    ok &= cmp("general_dev texts", [g["text"] for g in my_g], [r["text"] for r in eG])
    print(f"    general_dev n_w total: auditor {sum(len(g['ids']) for g in my_g)} | Executor {sum(len(r['ids']) for r in eG)}")
    ok &= cmp("anchor_text (source row, ids)", [(a["row"], a["ids"]) for a in my_a], [(r["source_row"], r["ids"]) for r in ex_a])
    ok &= cmp("anchor_text texts", [a["text"] for a in my_a], [r["text"] for r in ex_a])
    print(f"AUDIT_VALUE compare:general_dev_ids auditor={sha(canon([g['ids'] for g in my_g]))} executor={sha(canon([r['ids'] for r in eG]))}")
    print(f"AUDIT_VALUE compare:anchor_ids auditor={sha(canon([a['ids'] for a in my_a]))} executor={sha(canon([r['ids'] for r in ex_a]))}")

    print("\n== C. informational: Executor file bytes")
    names = sorted(x for x in os.listdir(exdir) if x.endswith((".jsonl", ".json")))
    for n in names:
        p = E(n)
        raw = open(p, "rb").read()
        can = jsonl_bytes(read_jsonl(p)) if n.endswith(".jsonl") else canon(json.load(open(p, encoding="utf-8")))
        print(f"  {n}: byte_sha256 {sha(raw)} | canonical_sha256 {sha(can)} | bytes are the canonical form {raw == can}")
    for o in others:
        same = {n: (file_sha(os.path.join(o, n)) if os.path.exists(os.path.join(o, n)) else None) == file_sha(E(n)) for n in names}
        print(f"  {o}: files byte-identical to {exdir}: {same}")
    return bool(ok)


run(main)
