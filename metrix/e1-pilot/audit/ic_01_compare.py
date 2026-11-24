"""IC-1 (implementation stage B, round 2, task 1): the Executor's regeneration after the round-1 fixes (data_c) against
  - my fresh regeneration of this round (ia_03 .. ia_06 into <my_out_c>),
  - my round-1 regeneration (<my_out_b>, the files ib_01 compared with data_b),
  - the Executor's round-1 regeneration (data_b),
  - the values the Executor printed in reports/impl_b/t6_fix_round.txt (lines 11-23 generate, 39-42 verify) and in
    reports/impl_b/t3_generate_leakage.txt (lines 12-19, round 1).
A. my two regenerations: every file of <my_out_b> and <my_out_c> byte-identical (same names).
B. four frozen hashes read back from data_c by the protocol method (same methods as ib_01):
     facts      : facts.jsonl in line order, each line exactly the 6 fields -> JSON list -> canonical SHA-256 (2.2);
     train_S    : train_S.jsonl parsed -> canonical JSONL SHA-256 (2.6, section 0);
     candidates : candidates.json parsed -> canonical JSON SHA-256 (2.5);
     anchor     : anchor_text.jsonl in file order (doc == line index) -> list of the 512 "text" -> canonical SHA-256
                  (DATA_MANIFEST anchor_text.decoded_texts_hash_rule); also with my own decode of the Executor's ids.
   compared with my value, the current PROTOCOL_FROZEN table (and the freeze-commit manifests), t6 lines 20-23 and 39-42.
C. files without a frozen hash, by content against my regeneration: train_F, train_Y, dev_qa, general_dev, anchor_text.
D. data_c against data_b: the 8 data files byte-identical; byte / canonical sha256 == t6 lines 12-19 == t3 lines 12-19;
   every file is already in canonical form.
E. data_c listing (8 data files + leakage_report.json; no test_qa.jsonl / general_test.jsonl).
F. t6 line 11 (eval_sets rows by split) against my prefix count (ic_00) and my dev-window count (ia_06 output).
Data Auditor's own script; no Executor code imported, called or copied.  Loads the tokenizer only.
usage: python -I ic_01_compare.py <repo_root> <qwen_tok_dir> <my_out_c> <my_out_b> <data_b> <data_c>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json, re
from ia_common import sha, canon, jsonl_bytes, frozen_json, read_jsonl, load_qwen, run

FACT_FIELDS = ["fact_id", "exposure", "relation", "stratum", "entity", "answer"]
DATA = ["facts.jsonl", "train_F.jsonl", "train_S.jsonl", "train_Y.jsonl", "dev_qa.jsonl", "candidates.json",
        "general_dev.jsonl", "anchor_text.jsonl"]
T3 = "metrix/e1-pilot/reports/impl_b/t3_generate_leakage.txt"
T6 = "metrix/e1-pilot/reports/impl_b/t6_fix_round.txt"


def first_diff(a, b):
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            return i, x, y
    return None if len(a) == len(b) else (min(len(a), len(b)), "length", (len(a), len(b)))


def protocol_frozen_table(repo):
    pf = open(os.path.join(repo, "metrix/e1-pilot/PROTOCOL_FROZEN"), encoding="utf-8").read()
    v11 = pf.split("## v1.1", 1)[1].split("\n## v1", 1)[0]
    assert "与 v1 相同" in v11, "v1.1 section does not refer to the v1 table"
    tab = pf.split("### 全部数据哈希", 1)[1].split("\n### ", 1)[0]
    return dict(re.findall(r"^\| (.+?) \| `([0-9a-f]{64})` \|", tab, re.M))


def file_rows(text_lines, first, last):
    return "\n".join(text_lines[first - 1:last])


def main():
    repo, qdir, mine, mine_b, dir_b, dir_c = sys.argv[1:7]
    ok = True
    dm, sm = frozen_json(repo, "DATA_MANIFEST.json"), frozen_json(repo, "SPLIT_MANIFEST.json")
    table = protocol_frozen_table(repo)
    pf_val = {"facts": table["fact(160 条)"], "train_S": table["`train_S.jsonl`"],
              "candidates": table["`candidates.json`"], "anchor_texts": table["锚文本(512 篇解码文本)"]}
    man_val = {"facts": dm["name_generation"]["expected_facts_canonical_sha256"],
               "train_S": dm["s_permutation"]["expected_train_S_canonical_sha256"],
               "candidates": sm["candidates"]["candidate_mapping_sha256"],
               "anchor_texts": dm["anchor_text"]["decoded_texts_canonical_sha256"]}
    for k in pf_val:
        print(f"frozen {k:<12} PROTOCOL_FROZEN {pf_val[k]} | freeze-commit manifest {man_val[k]} | same {pf_val[k] == man_val[k]}")
        ok &= pf_val[k] == man_val[k]
    t6 = open(os.path.join(repo, T6), encoding="utf-8").read().split("\n")
    t3 = open(os.path.join(repo, T3), encoding="utf-8").read().split("\n")
    print("Executor t6 lines 11-25 and 37-45 (as recorded):")
    for i in list(range(11, 26)) + list(range(37, 46)):
        print(f"  t6:{i}: {t6[i - 1]}")
    t6_gen = dict(re.findall(r"^frozen content hash (\w+)\s+([0-9a-f]{64}) = PROTOCOL_FROZEN \(read back from <SCRATCH>/data_c\)$",
                             file_rows(t6, 20, 23), re.M))
    t6_ver = dict(re.findall(r"^frozen content hash (\w+)\s+([0-9a-f]{64}) = PROTOCOL_FROZEN$", file_rows(t6, 39, 42), re.M))
    rx = r"^(\S+)\s+rows\s+(\d+)\s+byte_sha256 ([0-9a-f]{64})\s+canonical_sha256 ([0-9a-f]{64})$"
    t6_bytes = {m[0]: (int(m[1]), m[2], m[3]) for m in re.findall(rx, file_rows(t6, 12, 19), re.M)}
    t3_bytes = {m[0]: (int(m[1]), m[2], m[3]) for m in re.findall(rx, file_rows(t3, 12, 19), re.M)}
    print(f"parsed: t6 generate read-back {len(t6_gen)} | t6 verify {len(t6_ver)} | t6 file lines {len(t6_bytes)} | t3 file lines {len(t3_bytes)}")
    ok &= len(t6_gen) == len(t6_ver) == 4 and len(t6_bytes) == len(t3_bytes) == 8

    print("\n== A. my regeneration of this round vs my round-1 regeneration (byte comparison)")
    na, nb = sorted(os.listdir(mine)), sorted(os.listdir(mine_b))
    print(f"files: this round {na} | round 1 {nb} | same names {na == nb}")
    ok &= na == nb
    for n in na:
        a, b = open(os.path.join(mine, n), "rb").read(), open(os.path.join(mine_b, n), "rb").read()
        print(f"  {n}: sha256 {sha(a)} | round 1 {sha(b)} | identical {a == b}")
        ok &= a == b

    tok = load_qwen(qdir)
    J = lambda name: json.load(open(os.path.join(mine, name), encoding="utf-8"))
    C = lambda name: os.path.join(dir_c, name)

    print("\n== B. four frozen hashes: auditor | read back from data_c | PROTOCOL_FROZEN | t6 generate | t6 verify")
    my_facts = J("facts.json")
    ex_lines = read_jsonl(C("facts.jsonl"))
    keys_ok = all(sorted(r) == sorted(FACT_FIELDS) for r in ex_lines)
    ex_facts = [{k: r[k] for k in FACT_FIELDS} for r in ex_lines]
    my_s = read_jsonl(os.path.join(mine, "train_S.jsonl"))
    ex_s = read_jsonl(C("train_S.jsonl"))
    my_c = J("candidates.json")
    ex_c = json.load(open(C("candidates.json"), encoding="utf-8"))
    my_a = J("anchor.json")
    ex_a = read_jsonl(C("anchor_text.jsonl"))
    doc_ok = [r["doc"] for r in ex_a] == list(range(len(ex_a)))
    print(f"facts.jsonl: {len(ex_lines)} lines, every line exactly the 6 fields: {keys_ok} | anchor_text.jsonl: {len(ex_a)} lines, doc == line index: {doc_ok}")
    ok &= keys_ok and doc_ok and len(ex_lines) == 160 and len(ex_a) == 512
    vals = {"facts": (sha(canon(my_facts)), sha(canon(ex_facts))),
            "train_S": (sha(jsonl_bytes(my_s)), sha(jsonl_bytes(ex_s))),
            "candidates": (sha(canon(my_c)), sha(canon(ex_c))),
            "anchor_texts": (sha(canon([a["text"] for a in my_a])), sha(canon([r["text"] for r in ex_a])))}
    for k, (m, e) in vals.items():
        same = m == e == pf_val[k] == t6_gen.get(k) == t6_ver.get(k)
        ok &= same
        print(f"  {k:<12} auditor {m} | from data_c {e} | PROTOCOL_FROZEN {pf_val[k]} | t6 generate {t6_gen.get(k)} | t6 verify {t6_ver.get(k)} | ALL EQUAL {same}")
    dec = sha(canon([tok.decode(r["ids"]) for r in ex_a]))
    print(f"  anchor texts from my decode of the Executor's data_c ids: {dec} | == PROTOCOL_FROZEN {dec == pf_val['anchor_texts']}")
    ok &= dec == pf_val["anchor_texts"]
    el = (my_facts == ex_facts, my_s == ex_s, my_c == ex_c, list(my_c) == list(ex_c))
    print(f"  element-wise equal: facts {el[0]} | train_S records {el[1]} | candidates {el[2]} | candidates key order {el[3]}")
    ok &= all(el)

    print("\n== C. files without a frozen hash (contents, data_c vs my regeneration)")
    tmpl = {t["template_id"]: t for t in sm["templates"]}
    rel_of = {f["fact_id"]: f["relation"] for f in my_facts}

    def cmp(name, a, b):
        same = a == b
        print(f"  {name}: auditor {len(a)} | Executor {len(b)} | identical sequence {same}"
              f"{'' if same else f' | first difference {first_diff(a, b)!r}'}")
        return same

    eF = read_jsonl(C("train_F.jsonl"))
    ok &= cmp("train_F (fact_id, text)", [(r["fact_id"], r["text"]) for r in J("train_F.json")], [(r["fact_id"], r["text"]) for r in eF])
    tF = all(r["template_id"] == f"{rel_of[r['fact_id']]}.TRAIN.1" and tmpl[r["template_id"]]["kind"] == "TRAIN" for r in eF)
    eY = read_jsonl(C("train_Y.jsonl"))
    ok &= cmp("train_Y (fact_id, kind, text)", [(r["fact_id"], r["kind"], r["text"]) for r in J("train_Y.json")],
              [(r["fact_id"], r["kind"], r["text"]) for r in eY])
    tY = all(r["template_id"] == f"{rel_of[r['fact_id']]}.{r['kind']}.1" and tmpl[r["template_id"]]["kind"] == r["kind"] for r in eY)
    eD = read_jsonl(C("dev_qa.jsonl"))
    ok &= cmp("dev_qa (fact_id, template_id, question)", [(r["fact_id"], r["template_id"], r["question"]) for r in J("dev_qa.json")],
              [(r["fact_id"], r["template_id"], r["question"]) for r in eD])
    tD = all(tmpl[r["template_id"]]["kind"] == "DEV" and tmpl[r["template_id"]]["relation"] == rel_of[r["fact_id"]] for r in eD)
    print(f"  template_id fields: train_F <relation>.TRAIN.1 {tF} | train_Y <relation>.<kind>.1 {tY} | dev_qa a DEV template of the fact's relation {tD}")
    ok &= tF and tY and tD
    my_g = J("general.json")
    eG = read_jsonl(C("general_dev.jsonl"))
    ok &= cmp("general_dev (domain, source doc_id, ids)", [(g["domain"], g["doc_id"], g["ids"]) for g in my_g],
              [(r["domain"], r["doc_id"], r["ids"]) for r in eG])
    ok &= cmp("general_dev texts", [g["text"] for g in my_g], [r["text"] for r in eG])
    ok &= cmp("anchor_text (source row, ids)", [(a["row"], a["ids"]) for a in my_a], [(r["source_row"], r["ids"]) for r in ex_a])
    ok &= cmp("anchor_text texts", [a["text"] for a in my_a], [r["text"] for r in ex_a])

    print("\n== D. data_c vs data_b (bytes) and the printed file hashes")
    for n in DATA:
        rc, rb = open(C(n), "rb").read(), open(os.path.join(dir_b, n), "rb").read()
        rows = len(read_jsonl(C(n))) if n.endswith(".jsonl") else len(json.loads(rc))
        can = jsonl_bytes(read_jsonl(C(n))) if n.endswith(".jsonl") else canon(json.loads(rc))
        b, c = sha(rc), sha(can)
        same = rc == rb and rc == can and t6_bytes.get(n) == (rows, b, c) == t3_bytes.get(n)
        ok &= same
        print(f"  {n}: rows {rows} | byte {b} | canonical {c} | data_c == data_b byte for byte {rc == rb} | canonical form {rc == can} "
              f"| == t6 line {t6_bytes.get(n) == (rows, b, c)} | == t3 line {t3_bytes.get(n) == (rows, b, c)}")

    print("\n== E. data_c listing")
    listing = sorted(os.listdir(dir_c))
    exp = sorted(DATA + ["leakage_report.json"])
    print(f"data_c listing {listing} | == 8 data files + leakage_report.json {listing == exp} | test_qa.jsonl present "
          f"{os.path.exists(C('test_qa.jsonl'))} | general_test.jsonl present {os.path.exists(C('general_test.jsonl'))}")
    ok &= listing == exp
    lc, lb = open(C("leakage_report.json"), "rb").read(), open(os.path.join(dir_b, "leakage_report.json"), "rb").read()
    print(f"leakage_report.json data_c == data_b byte for byte (informational; the leakage check itself is not part of this task): {lc == lb}")

    print("\n== F. t6 line 11")
    m = re.fullmatch(r"eval_sets\.jsonl rows by split \(row prefix only\): (\{.*\}); rows parsed and decoded: (\d+)", t6[10])
    print(f"t6:11 parsed: rows by split {m.group(1) if m else None} | 'rows parsed and decoded' {m.group(2) if m else None}")
    ok &= m is not None and m.group(1) == "{'dev': 400, 'test': 800}"
    print(f"my prefix count (ic_00): {{'dev': 400, 'test': 800}} | rows by split in t6 equal to it: {bool(m) and m.group(1) == str({'dev': 400, 'test': 800})}")
    print(f"my general DEV windows (= rows decoded with the parcae tokenizer): {len(my_g)} | == t6 number {bool(m) and int(m.group(2)) == len(my_g)}")
    print("note: the dev rows that build_general_dev UTF-8-decodes and JSON-parses are all 400 dev rows (static reading, ic_06 b);"
          " the printed 100 is the number of windows kept (= rows token-decoded), not of rows parsed")
    return bool(ok)


run(main)
