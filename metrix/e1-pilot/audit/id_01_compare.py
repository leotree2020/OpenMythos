"""ID-1 (implementation stage B, fix commit, task 1): the Executor's regeneration after the fixes (data_d) against
  - my fresh regeneration of this round (ia_03 .. ia_06 into <my_out_d>),
  - my round-2 regeneration (<my_out_c>, the files ic_01 compared with data_c),
  - the Executor's round-2 regeneration (data_c) and round-1 regeneration (data_b),
  - the values the Executor printed in reports/impl_b/t8_fix_commit.txt (lines 11-23 generate, 26-35 cmp data_c/data_d,
    38-42 verify) and, for the file lines, t6_fix_round.txt (lines 12-19) and t3_generate_leakage.txt (lines 12-19).
A. my two regenerations: every file of <my_out_d> and <my_out_c> byte-identical (same names).
B. four frozen hashes read back from data_d by the protocol method (same methods as ib_01 / ic_01):
     facts      : facts.jsonl in line order, each line exactly the 6 fields -> JSON list -> canonical SHA-256 (2.2);
     train_S    : train_S.jsonl parsed -> canonical JSONL SHA-256 (2.6, section 0);
     candidates : candidates.json parsed -> canonical JSON SHA-256 (2.5);
     anchor     : anchor_text.jsonl in file order (doc == line index) -> list of the 512 "text" -> canonical SHA-256
                  (DATA_MANIFEST anchor_text.decoded_texts_hash_rule); also with my own decode of the Executor's ids.
   compared with my value, the current PROTOCOL_FROZEN table (and the freeze-commit manifests), t8 lines 20-23 and 38-41.
C. files without a frozen hash, by content against my regeneration: train_F, train_Y, dev_qa, general_dev, anchor_text.
D. data_d against data_c and data_b: the 8 data files byte-identical; byte / canonical sha256 == t8 lines 12-19 ==
   t6 lines 12-19 == t3 lines 12-19; every file already in canonical form; t8 lines 26-35 (cmp data_c data_d) parsed.
E. data_d listing (8 data files + leakage_report.json; no test_qa.jsonl / general_test.jsonl).
F. t8 line 11 against my own numbers, computed here: rows by split = my binary line-prefix count of eval_sets.jsonl
   (no decode, no parse); "DEV rows decoded and parsed" = my prefix count of dev rows; "windows kept" = the number of
   my general DEV windows (ia_06 output).  Also t8 lines 3-25 against t6 lines 3-25 (expected: only the data
   directory name and the line-11 label differ).
Data Auditor's own script (adapted from my ic_01_compare.py); no Executor code imported, called or copied.
Loads the tokenizer only.
usage: python -I id_01_compare.py <repo_root> <qwen_tok_dir> <my_out_d> <my_out_c> <data_b> <data_c> <data_d>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json, re
from collections import Counter
from ia_common import sha, canon, jsonl_bytes, frozen_json, read_jsonl, load_qwen, run

FACT_FIELDS = ["fact_id", "exposure", "relation", "stratum", "entity", "answer"]
DATA = ["facts.jsonl", "train_F.jsonl", "train_S.jsonl", "train_Y.jsonl", "dev_qa.jsonl", "candidates.json",
        "general_dev.jsonl", "anchor_text.jsonl"]
T3 = "metrix/e1-pilot/reports/impl_b/t3_generate_leakage.txt"
T6 = "metrix/e1-pilot/reports/impl_b/t6_fix_round.txt"
T8 = "metrix/e1-pilot/reports/impl_b/t8_fix_commit.txt"
KEY = b'"split": "'


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


def rows(text_lines, first, last):
    return "\n".join(text_lines[first - 1:last])


def prefix_counts(path):
    """Binary mode; per line only the split value in the line prefix is located and counted (no decode, no parse)."""
    cnt, bad = Counter(), 0
    with open(path, "rb") as fh:
        for line in fh:
            i = line.find(KEY, 0, 80)
            j = line.find(b'"', i + len(KEY), i + len(KEY) + 16) if i >= 0 else -1
            if j < 0:
                bad += 1
                continue
            cnt[line[i + len(KEY):j]] += 1
    return {k.decode("ascii"): v for k, v in sorted(cnt.items())}, bad


def main():
    repo, qdir, mine, mine_c, dir_b, dir_c, dir_d = sys.argv[1:8]
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
    t8 = open(os.path.join(repo, T8), encoding="utf-8").read().split("\n")
    t6 = open(os.path.join(repo, T6), encoding="utf-8").read().split("\n")
    t3 = open(os.path.join(repo, T3), encoding="utf-8").read().split("\n")
    print("Executor t8 lines 3-44 (as recorded):")
    for i in range(3, 45):
        print(f"  t8:{i}: {t8[i - 1]}")
    t8_gen = dict(re.findall(r"^frozen content hash (\w+)\s+([0-9a-f]{64}) = PROTOCOL_FROZEN \(read back from <SCRATCH>/data_d\)$",
                             rows(t8, 20, 23), re.M))
    t8_ver = dict(re.findall(r"^frozen content hash (\w+)\s+([0-9a-f]{64}) = PROTOCOL_FROZEN$", rows(t8, 38, 41), re.M))
    rx = r"^(\S+)\s+rows\s+(\d+)\s+byte_sha256 ([0-9a-f]{64})\s+canonical_sha256 ([0-9a-f]{64})$"
    t8_bytes = {m[0]: (int(m[1]), m[2], m[3]) for m in re.findall(rx, rows(t8, 12, 19), re.M)}
    t6_bytes = {m[0]: (int(m[1]), m[2], m[3]) for m in re.findall(rx, rows(t6, 12, 19), re.M)}
    t3_bytes = {m[0]: (int(m[1]), m[2], m[3]) for m in re.findall(rx, rows(t3, 12, 19), re.M)}
    t8_cmp = re.findall(r"^identical (\S+)$", rows(t8, 27, 34), re.M)
    t8_cmp_exit = t8[34]
    t8_ver_tail = (t8[41], t8[42], t8[43])
    print(f"parsed: t8 generate read-back {len(t8_gen)} | t8 verify {len(t8_ver)} | t8 file lines {len(t8_bytes)} | t6 file lines "
          f"{len(t6_bytes)} | t3 file lines {len(t3_bytes)} | t8 cmp 'identical' lines {len(t8_cmp)} ({t8_cmp_exit}) | t8 verify tail {t8_ver_tail}")
    ok &= len(t8_gen) == len(t8_ver) == 4 and len(t8_bytes) == len(t6_bytes) == len(t3_bytes) == 8
    ok &= sorted(t8_cmp) == sorted(DATA) and t8_cmp_exit == "exit=0"
    ok &= t8_ver_tail == ("all 8 data files byte-identical to their regeneration from the frozen inputs", "RESULT: PASS", "exit=0")

    print("\n== A. my regeneration of this round vs my round-2 regeneration (byte comparison)")
    na, nb = sorted(os.listdir(mine)), sorted(os.listdir(mine_c))
    print(f"files: this round {na} | round 2 {nb} | same names {na == nb}")
    ok &= na == nb
    for n in na:
        a, b = open(os.path.join(mine, n), "rb").read(), open(os.path.join(mine_c, n), "rb").read()
        print(f"  {n}: sha256 {sha(a)} | round 2 {sha(b)} | identical {a == b}")
        ok &= a == b

    tok = load_qwen(qdir)
    J = lambda name: json.load(open(os.path.join(mine, name), encoding="utf-8"))
    X = lambda name: os.path.join(dir_d, name)

    print("\n== B. four frozen hashes: auditor | read back from data_d | PROTOCOL_FROZEN | t8 generate | t8 verify")
    my_facts = J("facts.json")
    ex_lines = read_jsonl(X("facts.jsonl"))
    keys_ok = all(sorted(r) == sorted(FACT_FIELDS) for r in ex_lines)
    ex_facts = [{k: r[k] for k in FACT_FIELDS} for r in ex_lines]
    my_s = read_jsonl(os.path.join(mine, "train_S.jsonl"))
    ex_s = read_jsonl(X("train_S.jsonl"))
    my_c = J("candidates.json")
    ex_c = json.load(open(X("candidates.json"), encoding="utf-8"))
    my_a = J("anchor.json")
    ex_a = read_jsonl(X("anchor_text.jsonl"))
    doc_ok = [r["doc"] for r in ex_a] == list(range(len(ex_a)))
    print(f"facts.jsonl: {len(ex_lines)} lines, every line exactly the 6 fields: {keys_ok} | anchor_text.jsonl: {len(ex_a)} lines, doc == line index: {doc_ok}")
    ok &= keys_ok and doc_ok and len(ex_lines) == 160 and len(ex_a) == 512
    vals = {"facts": (sha(canon(my_facts)), sha(canon(ex_facts))),
            "train_S": (sha(jsonl_bytes(my_s)), sha(jsonl_bytes(ex_s))),
            "candidates": (sha(canon(my_c)), sha(canon(ex_c))),
            "anchor_texts": (sha(canon([a["text"] for a in my_a])), sha(canon([r["text"] for r in ex_a])))}
    for k, (m, e) in vals.items():
        same = m == e == pf_val[k] == t8_gen.get(k) == t8_ver.get(k)
        ok &= same
        print(f"  {k:<12} auditor {m} | from data_d {e} | PROTOCOL_FROZEN {pf_val[k]} | t8 generate {t8_gen.get(k)} | t8 verify {t8_ver.get(k)} | ALL EQUAL {same}")
    dec = sha(canon([tok.decode(r["ids"]) for r in ex_a]))
    print(f"  anchor texts from my decode of the Executor's data_d ids: {dec} | == PROTOCOL_FROZEN {dec == pf_val['anchor_texts']}")
    ok &= dec == pf_val["anchor_texts"]
    el = (my_facts == ex_facts, my_s == ex_s, my_c == ex_c, list(my_c) == list(ex_c))
    print(f"  element-wise equal: facts {el[0]} | train_S records {el[1]} | candidates {el[2]} | candidates key order {el[3]}")
    ok &= all(el)

    print("\n== C. files without a frozen hash (contents, data_d vs my regeneration)")
    tmpl = {t["template_id"]: t for t in sm["templates"]}
    rel_of = {f["fact_id"]: f["relation"] for f in my_facts}

    def cmp(name, a, b):
        same = a == b
        print(f"  {name}: auditor {len(a)} | Executor {len(b)} | identical sequence {same}"
              f"{'' if same else f' | first difference {first_diff(a, b)!r}'}")
        return same

    eF = read_jsonl(X("train_F.jsonl"))
    ok &= cmp("train_F (fact_id, text)", [(r["fact_id"], r["text"]) for r in J("train_F.json")], [(r["fact_id"], r["text"]) for r in eF])
    tF = all(r["template_id"] == f"{rel_of[r['fact_id']]}.TRAIN.1" and tmpl[r["template_id"]]["kind"] == "TRAIN" for r in eF)
    eY = read_jsonl(X("train_Y.jsonl"))
    ok &= cmp("train_Y (fact_id, kind, text)", [(r["fact_id"], r["kind"], r["text"]) for r in J("train_Y.json")],
              [(r["fact_id"], r["kind"], r["text"]) for r in eY])
    tY = all(r["template_id"] == f"{rel_of[r['fact_id']]}.{r['kind']}.1" and tmpl[r["template_id"]]["kind"] == r["kind"] for r in eY)
    eD = read_jsonl(X("dev_qa.jsonl"))
    ok &= cmp("dev_qa (fact_id, template_id, question)", [(r["fact_id"], r["template_id"], r["question"]) for r in J("dev_qa.json")],
              [(r["fact_id"], r["template_id"], r["question"]) for r in eD])
    tD = all(tmpl[r["template_id"]]["kind"] == "DEV" and tmpl[r["template_id"]]["relation"] == rel_of[r["fact_id"]] for r in eD)
    print(f"  template_id fields: train_F <relation>.TRAIN.1 {tF} | train_Y <relation>.<kind>.1 {tY} | dev_qa a DEV template of the fact's relation {tD}")
    ok &= tF and tY and tD
    my_g = J("general.json")
    eG = read_jsonl(X("general_dev.jsonl"))
    ok &= cmp("general_dev (domain, source doc_id, ids)", [(g["domain"], g["doc_id"], g["ids"]) for g in my_g],
              [(r["domain"], r["doc_id"], r["ids"]) for r in eG])
    ok &= cmp("general_dev texts", [g["text"] for g in my_g], [r["text"] for r in eG])
    ok &= cmp("anchor_text (source row, ids)", [(a["row"], a["ids"]) for a in my_a], [(r["source_row"], r["ids"]) for r in ex_a])
    ok &= cmp("anchor_text texts", [a["text"] for a in my_a], [r["text"] for r in ex_a])

    print("\n== D. data_d vs data_c and data_b (bytes) and the printed file hashes")
    for n in DATA:
        rd = open(X(n), "rb").read()
        rc, rb = open(os.path.join(dir_c, n), "rb").read(), open(os.path.join(dir_b, n), "rb").read()
        nrows = len(read_jsonl(X(n))) if n.endswith(".jsonl") else len(json.loads(rd))
        can = jsonl_bytes(read_jsonl(X(n))) if n.endswith(".jsonl") else canon(json.loads(rd))
        b, c = sha(rd), sha(can)
        line = (nrows, b, c)
        same = rd == rc == rb and rd == can and t8_bytes.get(n) == line == t6_bytes.get(n) == t3_bytes.get(n)
        ok &= same
        print(f"  {n}: rows {nrows} | byte {b} | canonical {c} | data_d == data_c {rd == rc} | data_d == data_b {rd == rb} | canonical form {rd == can} "
              f"| == t8 line {t8_bytes.get(n) == line} | == t6 line {t6_bytes.get(n) == line} | == t3 line {t3_bytes.get(n) == line}")

    print("\n== E. data_d listing")
    listing = sorted(os.listdir(dir_d))
    exp = sorted(DATA + ["leakage_report.json"])
    print(f"data_d listing {listing} | == 8 data files + leakage_report.json {listing == exp} | test_qa.jsonl present "
          f"{os.path.exists(X('test_qa.jsonl'))} | general_test.jsonl present {os.path.exists(X('general_test.jsonl'))}")
    ok &= listing == exp
    ld, lc = open(X("leakage_report.json"), "rb").read(), open(os.path.join(dir_c, "leakage_report.json"), "rb").read()
    print(f"leakage_report.json data_d == data_c byte for byte (informational; the leakage check itself is not part of this task): {ld == lc}")

    print("\n== F. t8 line 11 against my own counts")
    m = re.fullmatch(r"eval_sets\.jsonl rows by split \(row prefix only\): (\{.*\}); DEV rows decoded and parsed: (\d+); "
                     r"windows kept \(decoded with the parcae tokenizer\): (\d+)", t8[10])
    print(f"t8:11 parsed: rows by split {m.group(1) if m else None} | DEV rows decoded and parsed {m.group(2) if m else None} | "
          f"windows kept {m.group(3) if m else None}")
    ok &= m is not None
    ev = os.path.join(repo, dm["general_text"]["source_file"])
    counts, bad = prefix_counts(ev)
    print(f"my binary line-prefix count of {dm['general_text']['source_file']}: {counts} | lines without the prefix key {bad}")
    ok &= bad == 0
    if m:
        r1 = m.group(1) == str(counts)
        r2 = int(m.group(2)) == counts.get("dev")
        r3 = int(m.group(3)) == len(my_g)
        print(f"  rows by split == my prefix count: {r1}")
        print(f"  'DEV rows decoded and parsed' {m.group(2)} == my prefix count of dev rows {counts.get('dev')}: {r2}")
        print(f"  'windows kept' {m.group(3)} == my general DEV windows {len(my_g)} (== rows of data_d/general_dev.jsonl {len(eG)}): {r3 and len(eG) == len(my_g)}")
        ok &= r1 and r2 and r3 and len(eG) == len(my_g)
    print("\n  t8 lines 3-25 vs t6 lines 3-25 (differences only, after replacing data_c by data_d in t6):")
    nd = 0
    for i in range(3, 26):
        a, b = t6[i - 1].replace("<SCRATCH>/data_c", "<SCRATCH>/data_d"), t8[i - 1]
        if a != b:
            nd += 1
            print(f"    line {i}: t6 {t6[i - 1]!r}")
            print(f"    line {i}: t8 {b!r}")
    print(f"  differing lines: {nd} (expected: line 11 only, the relabelled count line)")
    ok &= nd == 1 and t6[10] != t8[10]
    return bool(ok)


run(main)
