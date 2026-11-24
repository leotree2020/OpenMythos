"""IB-1 (implementation stage B, task 1): the auditor's regeneration (ia_03 .. ia_06 run into <my_out>) against the
Executor's stage B regeneration <executor_dir> (data_b).
A. four frozen hashes, three ways: auditor value | value recomputed by me from the Executor's file by the protocol
   method | frozen value (read from the current PROTOCOL_FROZEN "全部数据哈希" table, which the v1.1 section declares
   valid, and also from the freeze-commit manifests).  Methods:
     facts      : facts.jsonl in line order, each line exactly the 6 fields -> JSON list -> canonical SHA-256
                  (protocol 2.2 "fact 哈希的比对方法"); the JSONL canonical hash of facts.jsonl is only printed;
     train_S    : train_S.jsonl parsed -> canonical JSONL SHA-256 (protocol 2.6, section 0);
     candidates : candidates.json parsed -> canonical JSON SHA-256 (protocol 2.5);
     anchor     : anchor_text.jsonl in file order (doc == line index) -> list of the 512 "text" fields -> canonical
                  SHA-256 (DATA_MANIFEST anchor_text.decoded_texts_hash_rule); and the same with my own decode of the
                  Executor's "ids".
   The four values printed by the Executor (reports/impl_b/t3_generate_leakage.txt lines 20-23) are compared too.
B. files without a frozen hash, by content (record field names are not fixed by the protocol): train_F (fact_id,
   text), train_Y (fact_id, kind, text), dev_qa (fact_id, template_id, question), general_dev (domain, source doc_id,
   ids, text), anchor_text (source row, ids, text).  template_id fields of the Executor are checked against the
   template used.
C. the Executor's data_b listing (8 data files + leakage_report.json, no test_qa.jsonl / general_test.jsonl);
   byte_sha256 / canonical_sha256 of every data_b file == the values printed in t3 lines 12-19 == the byte_sha256 of
   the stage A gen1 files that I recorded in stdout/impl_a/10_ia_compare.txt (stage A audit).
Data Auditor's own script; no Executor code imported, called or copied.  Loads the tokenizer only.
usage: python -I ib_01_compare.py <repo_root> <qwen_tok_dir> <my_out_dir> <executor_dir>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json, re
from ia_common import sha, canon, jsonl_bytes, frozen_json, read_jsonl, load_qwen, run

FACT_FIELDS = ["fact_id", "exposure", "relation", "stratum", "entity", "answer"]
DATA = ["facts.jsonl", "train_F.jsonl", "train_S.jsonl", "train_Y.jsonl", "dev_qa.jsonl", "candidates.json",
        "general_dev.jsonl", "anchor_text.jsonl"]
T3 = "metrix/e1-pilot/reports/impl_b/t3_generate_leakage.txt"
IA10 = "metrix/e1-pilot/audit/stdout/impl_a/10_ia_compare.txt"


def first_diff(a, b):
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            return i, x, y
    return None if len(a) == len(b) else (min(len(a), len(b)), "length", (len(a), len(b)))


def protocol_frozen_table(repo):
    """The 12-row data hash table of the current PROTOCOL_FROZEN (v1 section, declared valid for v1.1)."""
    pf = open(os.path.join(repo, "metrix/e1-pilot/PROTOCOL_FROZEN"), encoding="utf-8").read()
    v11 = pf.split("## v1.1", 1)[1].split("\n## v1", 1)[0]
    assert "与 v1 相同" in v11, "v1.1 section does not refer to the v1 table"
    tab = pf.split("### 全部数据哈希", 1)[1].split("\n### ", 1)[0]
    rows = re.findall(r"^\| (.+?) \| `([0-9a-f]{64})` \|", tab, re.M)
    return dict(rows)


def main():
    repo, qdir, mine, exdir = sys.argv[1:5]
    ok = True
    dm, sm = frozen_json(repo, "DATA_MANIFEST.json"), frozen_json(repo, "SPLIT_MANIFEST.json")
    table = protocol_frozen_table(repo)
    print("PROTOCOL_FROZEN table rows:", len(table))
    pf_val = {"facts": table["fact(160 条)"], "train_S": table["`train_S.jsonl`"],
              "candidates": table["`candidates.json`"], "anchor_texts": table["锚文本(512 篇解码文本)"]}
    man_val = {"facts": dm["name_generation"]["expected_facts_canonical_sha256"],
               "train_S": dm["s_permutation"]["expected_train_S_canonical_sha256"],
               "candidates": sm["candidates"]["candidate_mapping_sha256"],
               "anchor_texts": dm["anchor_text"]["decoded_texts_canonical_sha256"]}
    for k in pf_val:
        print(f"frozen {k:<12} PROTOCOL_FROZEN {pf_val[k]} | freeze-commit manifest {man_val[k]} | same {pf_val[k] == man_val[k]}")
        ok &= pf_val[k] == man_val[k]
    t3 = open(os.path.join(repo, T3), encoding="utf-8").read().split("\n")
    print("Executor t3 lines 12-23 (as recorded):")
    for i in range(11, 23):
        print(f"  t3:{i + 1}: {t3[i]}")
    ex_print = dict(re.findall(r"^frozen content hash (\w+)\s+([0-9a-f]{64}) = PROTOCOL_FROZEN \(read back", "\n".join(t3[19:23]), re.M))
    ex_bytes = {m[0]: (m[1], m[2]) for m in re.findall(r"^(\S+)\s+rows\s+\d+\s+byte_sha256 ([0-9a-f]{64})\s+canonical_sha256 ([0-9a-f]{64})$",
                                                       "\n".join(t3[11:19]), re.M)}
    tok = load_qwen(qdir)
    J = lambda name: json.load(open(os.path.join(mine, name), encoding="utf-8"))
    E = lambda name: os.path.join(exdir, name)

    print("\n== A. four frozen hashes: auditor | recomputed from the Executor's data_b file | PROTOCOL_FROZEN | Executor t3 print")
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
    print(f"facts.jsonl: {len(ex_lines)} lines, every line exactly the 6 fields: {keys_ok} | anchor_text.jsonl: {len(ex_a)} lines, doc == line index: {doc_ok}")
    ok &= keys_ok and doc_ok and len(ex_lines) == 160 and len(ex_a) == 512
    vals = {"facts": (sha(canon(my_facts)), sha(canon(ex_facts))),
            "train_S": (sha(jsonl_bytes(my_s)), sha(jsonl_bytes(ex_s))),
            "candidates": (sha(canon(my_c)), sha(canon(ex_c))),
            "anchor_texts": (sha(canon([a["text"] for a in my_a])), sha(canon([r["text"] for r in ex_a])))}
    for k, (m, e) in vals.items():
        same = m == e == pf_val[k] == ex_print.get(k)
        ok &= same
        print(f"  {k:<12} auditor {m} | from data_b {e} | PROTOCOL_FROZEN {pf_val[k]} | t3 {ex_print.get(k)} | ALL EQUAL {same}")
    dec = sha(canon([tok.decode(r["ids"]) for r in ex_a]))
    print(f"  anchor texts from my decode of the Executor's ids: {dec} | == PROTOCOL_FROZEN {dec == pf_val['anchor_texts']}")
    ok &= dec == pf_val["anchor_texts"]
    print(f"  facts.jsonl JSONL canonical sha256 (a different byte string, not compared with the fact value, protocol 2.2): {sha(jsonl_bytes(ex_lines))}")
    el = (my_facts == ex_facts, my_s == ex_s, my_c == ex_c, list(my_c) == list(ex_c))
    print(f"  element-wise equal: facts {el[0]} | train_S records {el[1]} | candidates {el[2]} | candidates key order {el[3]}")
    ok &= all(el)

    print("\n== B. files without a frozen hash (contents)")
    tmpl = {t["template_id"]: t for t in sm["templates"]}
    rel_of = {f["fact_id"]: f["relation"] for f in my_facts}

    def cmp(name, a, b):
        same = a == b
        print(f"  {name}: auditor {len(a)} | Executor {len(b)} | identical sequence {same}"
              f"{'' if same else f' | first difference {first_diff(a, b)!r}'}")
        return same

    eF = read_jsonl(E("train_F.jsonl"))
    ok &= cmp("train_F (fact_id, text)", [(r["fact_id"], r["text"]) for r in J("train_F.json")], [(r["fact_id"], r["text"]) for r in eF])
    tF = all(r["template_id"] == f"{rel_of[r['fact_id']]}.TRAIN.1" and tmpl[r["template_id"]]["kind"] == "TRAIN" for r in eF)
    eY = read_jsonl(E("train_Y.jsonl"))
    ok &= cmp("train_Y (fact_id, kind, text)", [(r["fact_id"], r["kind"], r["text"]) for r in J("train_Y.json")],
              [(r["fact_id"], r["kind"], r["text"]) for r in eY])
    tY = all(r["template_id"] == f"{rel_of[r['fact_id']]}.{r['kind']}.1" and tmpl[r["template_id"]]["kind"] == r["kind"] for r in eY)
    eD = read_jsonl(E("dev_qa.jsonl"))
    ok &= cmp("dev_qa (fact_id, template_id, question)", [(r["fact_id"], r["template_id"], r["question"]) for r in J("dev_qa.json")],
              [(r["fact_id"], r["template_id"], r["question"]) for r in eD])
    tD = all(tmpl[r["template_id"]]["kind"] == "DEV" and tmpl[r["template_id"]]["relation"] == rel_of[r["fact_id"]] for r in eD)
    print(f"  template_id fields: train_F <relation>.TRAIN.1 {tF} | train_Y <relation>.<kind>.1 {tY} | dev_qa a DEV template of the fact's relation {tD}")
    ok &= tF and tY and tD
    my_g = J("general.json")
    eG = read_jsonl(E("general_dev.jsonl"))
    ok &= cmp("general_dev (domain, source doc_id, ids)", [(g["domain"], g["doc_id"], g["ids"]) for g in my_g],
              [(r["domain"], r["doc_id"], r["ids"]) for r in eG])
    ok &= cmp("general_dev texts", [g["text"] for g in my_g], [r["text"] for r in eG])
    ok &= cmp("anchor_text (source row, ids)", [(a["row"], a["ids"]) for a in my_a], [(r["source_row"], r["ids"]) for r in ex_a])
    ok &= cmp("anchor_text texts", [a["text"] for a in my_a], [r["text"] for r in ex_a])
    print(f"  general_dev ids canonical sha256: auditor {sha(canon([g['ids'] for g in my_g]))} | Executor {sha(canon([r['ids'] for r in eG]))}")
    print(f"  anchor ids canonical sha256: auditor {sha(canon([a['ids'] for a in my_a]))} | Executor {sha(canon([r['ids'] for r in ex_a]))}")

    print("\n== C. data_b listing and file hashes")
    listing = sorted(os.listdir(exdir))
    exp = sorted(DATA + ["leakage_report.json"])
    print(f"data_b listing {listing} | == 8 data files + leakage_report.json {listing == exp} | test_qa.jsonl present "
          f"{os.path.exists(E('test_qa.jsonl'))} | general_test.jsonl present {os.path.exists(E('general_test.jsonl'))}")
    ok &= listing == exp
    ia10 = open(os.path.join(repo, IA10), encoding="utf-8").read()
    gen1 = dict(re.findall(r"^  (\S+): byte_sha256 ([0-9a-f]{64}) \|", ia10, re.M))
    for n in DATA:
        raw = open(E(n), "rb").read()
        can = jsonl_bytes(read_jsonl(E(n))) if n.endswith(".jsonl") else canon(json.loads(raw))
        b, c = sha(raw), sha(can)
        t = ex_bytes.get(n)
        same = t == (b, c) and gen1.get(n) == b and raw == can
        ok &= same
        print(f"  {n}: byte {b} | canonical {c} | bytes are the canonical form {raw == can} | t3 {t == (b, c)} "
              f"| == stage A gen1 byte_sha256 recorded by me {gen1.get(n) == b}")
    return bool(ok)


run(main)
