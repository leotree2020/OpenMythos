"""IF-1 (implementation stage B, report commit, task 2): the four data content hashes that leakage.verify_authorization
compares a committed freeze record with, against PROTOCOL_FROZEN and against data_d.
  A. PROTOCOL_FROZEN read by my own method (not the Executor's parser, not my id_01 regexes): working-tree bytes ==
     HEAD blob == index blob; lines; the line "当前有效版本：<v>"; the section "## <v>(当前有效)" (to the next "## ");
     in it the row "<v> 冻结提交(完整 hash)" (cells split on "|") and the sentence naming the number of values of the
     table "全部数据哈希"; the table under the unique line "### 全部数据哈希": every "|"-row split into cells, header and
     separator rows skipped; label -> value (backticks stripped) -> location cell.  Each location cell
     ("<FILE>.json: a.b.c", "同上" = previous file and path) is resolved by me in the freeze-commit manifest (git cat-file).
  B. which four values verify_authorization uses (static; Executor files read as text and parsed with ast, never
     imported or run): frozen.CONTENT_HASH_KEYS and frozen.DATA_TABLE_ROWS (ast.literal_eval); the data path
     PROTOCOL_FROZEN table row label -> DATA_TABLE_ROWS[label][0] -> FrozenRecord.data_sha256 (parse_protocol_frozen)
     -> Frozen.data_hash(key) -> verify_authorization's `content` -> 3rd argument of record.freeze_record_problem ->
     compared with the record's data_content_hashes; load() binds data_sha256 to the frozen-commit manifests.  Applying
     DATA_TABLE_ROWS to MY parsed table gives the four values verify_authorization compares with.
  C. the same four hashes recomputed by me from <data_d> by the protocol rules (section 0 canonical JSON / JSONL;
     2.2 fact list from facts.jsonl in line order, the 6 fields; 2.6 train_S JSONL; 2.5 candidates object; anchor
     texts: list of the 512 texts in document order, DATA_MANIFEST anchor_text.decoded_texts_hash_rule; also from my own
     decode of data_d's anchor ids with the pinned tokenizer), and from my own round-3 regeneration (<my_out>).
  D. data_d unchanged since my round 3 (byte sha256 of the 8 files == stdout/impl_b/36_id_compare.txt section D) and
     the Executor's printed values (reports/impl_b/t8_fix_commit.txt lines 20-23 and 38-41).
Data Auditor's own script; no Executor code imported, called or copied.  Loads the tokenizer only.
usage: python -I if_01_content_hashes.py <repo_root> <qwen_tok_dir> <data_d> <my_out>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ast, json, re
from ia_common import FROZEN, git, blob, sha, canon, jsonl_bytes, frozen_protocol, read_jsonl, load_qwen, run

PF = "metrix/e1-pilot/PROTOCOL_FROZEN"
SRC = "metrix/e1-pilot/src/metrix_e1/"
FACT_FIELDS = ["fact_id", "exposure", "relation", "stratum", "entity", "answer"]
DATA = ["facts.jsonl", "train_F.jsonl", "train_S.jsonl", "train_Y.jsonl", "dev_qa.jsonl", "candidates.json",
        "general_dev.jsonl", "anchor_text.jsonl"]
# my own reading of the protocol: which table row holds which content hash (by the row's own label and definition cell)
MY_ROWS = {"facts": ("fact(160 条)", "协议第 2.2 节"), "train_S": ("`train_S.jsonl`", "协议第 2.6 节"),
           "candidates": ("`candidates.json`", "协议第 2.5 节"), "anchor_texts": ("锚文本(512 篇解码文本)", "JSON 列表")}


def cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def fn(tree, name):
    return next(n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name == name)


def body(f):
    return [s for s in f.body if not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant) and isinstance(s.value.value, str))]


def main():
    repo, qdir, dd, mine = sys.argv[1:5]
    ok = True
    print("== A. PROTOCOL_FROZEN, my own reading")
    wt = open(os.path.join(repo, PF), "rb").read()
    hb = blob(repo, "HEAD", PF)
    ib = git(repo, "cat-file", "blob", f":{PF}").stdout
    print(f"{PF}: sha256 {sha(wt)} | working tree == HEAD blob {wt == hb} | == index blob {wt == ib}")
    ok &= wt == hb == ib
    lines = wt.decode("utf-8").split("\n")
    vl = [ln for ln in lines if ln.startswith("当前有效版本")]
    ver = vl[0].split("：", 1)[1].strip() if len(vl) == 1 and "：" in vl[0] else None
    print(f"current-version lines {vl} -> version {ver}")
    ok &= ver == "v1.1"
    starts = [i for i, ln in enumerate(lines) if ln == f"## {ver}(当前有效)"]
    s0 = starts[0] if len(starts) == 1 else None
    s1 = next(i for i in range(s0 + 1, len(lines)) if lines[i].startswith("## ")) if s0 is not None else None
    sec = lines[s0:s1] if s0 is not None else []
    print(f"current section: lines {s0 + 1 if s0 is not None else None}..{s1} ({lines[s0] if s0 is not None else None!r})")
    crow = [cells(ln) for ln in sec if ln.startswith("|") and cells(ln)[0] == f"{ver} 冻结提交(完整 hash)"]
    commit = crow[0][1].strip("`") if len(crow) == 1 else None
    print(f"frozen commit of the current section: {commit} | == {FROZEN}: {commit == FROZEN}")
    ok &= commit == FROZEN
    ref = [m.group(1) for ln in sec for m in [re.search(r"“全部数据哈希”表中的 (\d+) 个值", ln)] if m]
    print(f"the current section refers to the table '全部数据哈希' with {ref} values")
    ok &= ref == ["12"]
    th = [i for i, ln in enumerate(lines) if ln == "### 全部数据哈希"]
    ok &= len(th) == 1
    table, i = [], th[0] + 1
    while i < len(lines) and not lines[i].startswith("#"):
        if lines[i].startswith("|"):
            table.append(cells(lines[i]))
        i += 1
    header, rows = table[0], [r for r in table[1:] if not set("".join(r)) <= set("-: ")]
    print(f"table header {header} | rows {len(rows)}")
    ok &= header == ["项", "SHA-256", "定义", "冻结提交中的位置"] and len(rows) == 12
    my_table, loc = {}, {}
    prev = None
    for r in rows:
        label, val, dfn, where = r[0], r[1].strip("`"), r[2], r[3]
        ok &= re.fullmatch(r"[0-9a-f]{64}", val) is not None and label not in my_table
        my_table[label] = (val, dfn)
        if where == "同上":
            where = prev
        prev = where
        loc[label] = where.strip("`")
    for k, (label, dmark) in MY_ROWS.items():
        v, dfn = my_table.get(label, (None, ""))
        print(f"  my reading: {k:<12} row {label!r} -> {v} | definition cell {dfn!r} names {dmark!r}: {dmark in dfn} | location {loc.get(label)!r}")
        ok &= v is not None and dmark in dfn
    mf = {}
    for k, (label, _) in MY_ROWS.items():
        fname, path = loc[label].split(": ", 1)
        if fname not in mf:
            mf[fname] = json.loads(blob(repo, FROZEN, f"metrix/e1-pilot/{fname}"))
        x = mf[fname]
        for part in path.split("."):
            x = x[part]
        same = x == my_table[label][0]
        print(f"  freeze-commit {fname}: {path} = {x} | == table value {same}")
        ok &= same
    proto = frozen_protocol(repo)
    for k, pat in (("facts", r"规范化 SHA-256 必须等于 `([0-9a-f]{64})`。参考实现 `reports/round2/names.py`"),
                   ("candidates", r"`candidates\.json` 的规范化 SHA-256 必须等于 `([0-9a-f]{64})`"),
                   ("train_S", r"`train_S\.jsonl` 的规范化 SHA-256 必须等于 `([0-9a-f]{64})`")):
        found = re.findall(pat, proto)
        same = found == [my_table[MY_ROWS[k][0]][0]]
        print(f"  freeze-commit protocol text, {k}: {found} | == table value {same}")
        ok &= same
    print(f"  freeze-commit DATA_MANIFEST anchor_text.decoded_texts_hash_rule: {mf['DATA_MANIFEST.json']['anchor_text']['decoded_texts_hash_rule']!r}")
    print(f"  freeze-commit DATA_MANIFEST hashing: serialization {mf['DATA_MANIFEST.json']['hashing']['serialization']!r} | jsonl {mf['DATA_MANIFEST.json']['hashing']['jsonl']!r}")

    print("\n== B. the four values verify_authorization compares with (static trace; Executor files read as text)")
    src = {n: open(os.path.join(repo, SRC + n), encoding="utf-8").read() for n in ("frozen.py", "leakage.py", "record.py", "test_data.py")}
    tr = {n: ast.parse(s, n) for n, s in src.items()}
    ft = tr["frozen.py"]
    assign = {ast.unparse(n.targets[0]): n.value for n in ft.body if isinstance(n, ast.Assign) and len(n.targets) == 1}
    chk = ast.literal_eval(assign["CONTENT_HASH_KEYS"])
    dtr = ast.literal_eval(assign["DATA_TABLE_ROWS"])
    print(f"frozen.CONTENT_HASH_KEYS = {chk}")
    ok &= chk == ("facts", "train_S", "candidates", "anchor_texts")
    print(f"frozen.DATA_TABLE_ROWS: {len(dtr)} labels | labels == my table's labels: {sorted(dtr) == sorted(my_table)}")
    ok &= sorted(dtr) == sorted(my_table)
    ppf = fn(ft, "parse_protocol_frozen")
    dh = [ast.unparse(s) for s in ast.walk(ppf) if isinstance(s, ast.Assign) and ast.unparse(s.targets[0]) == "data_hashes"]
    ret = [ast.unparse(s) for s in ast.walk(ppf) if isinstance(s, ast.Return)]
    tbl = [ast.unparse(s) for s in ast.walk(ppf) if isinstance(s, ast.Assign) and ast.unparse(s.targets[0]) == "table_at"]
    print(f"parse_protocol_frozen: {tbl} | {dh} | {ret}")
    ok &= dh == ["data_hashes = {DATA_TABLE_ROWS[label][0]: sha for label, sha in rows}"] and len(ret) == 1 and "data_sha256=data_hashes" in ret[0] \
        and len(tbl) == 1 and "'### 全部数据哈希'" in tbl[0]
    dhf = fn(fn(ft, "Frozen"), "data_hash")
    dhb = [ast.unparse(s) for s in body(dhf)]
    print(f"Frozen.data_hash: {dhb}")
    ok &= dhb == ["return self.record.data_sha256[key]"]
    ld = fn(ft, "load")
    bind = [ast.unparse(s).split("\n")[0] for s in ast.walk(ld) if isinstance(s, ast.If) and "record.data_sha256[key]" in ast.unparse(s.test)]
    print(f"frozen.load binds data_sha256 to the frozen-commit manifests: {bind}")
    ok &= bind == ["if found != [record.data_sha256[key]]:"]
    va = fn(tr["leakage.py"], "verify_authorization")
    content = [ast.unparse(s) for s in ast.walk(va) if isinstance(s, ast.Assign) and ast.unparse(s.targets[0]) == "content"]
    frp = [c for c in ast.walk(va) if isinstance(c, ast.Call) and ast.unparse(c.func) == "R.freeze_record_problem"]
    frp_args = [ast.unparse(a) for a in frp[0].args] if len(frp) == 1 else None
    print(f"verify_authorization: {content} | R.freeze_record_problem arguments {frp_args}")
    ok &= content == ["content = {k: fz.data_hash(k) for k in FZ.CONTENT_HASH_KEYS}"] and frp_args is not None and frp_args[2] == "content"
    frf = fn(tr["record.py"], "freeze_record_problem")
    params = [a.arg for a in frf.args.args]
    cmpx = [ast.unparse(s.test) for s in ast.walk(frf) if isinstance(s, ast.If) and "data_content_hashes" in ast.unparse(s.test)]
    print(f"record.freeze_record_problem({', '.join(params)}): data hash comparison {cmpx}")
    ok &= params[2] == "content_hashes" and cmpx == ["rec.get('data_content_hashes') != content_hashes"]
    cp = fn(tr["test_data.py"], "check_preconditions")
    cpl = [ast.unparse(s) for s in body(cp)]
    print(f"test_data.check_preconditions (the generator's condition 3 gets `content`): {cpl[2]!r} -> {cpl[4]!r}")
    ok &= cpl[2] == "content = fz.check_data_dir(data_dir)" and "content" in cpl[4]
    cdd = fn(fn(ft, "Frozen"), "check_data_dir")
    cc = fn(fn(ft, "Frozen"), "check_content")
    chs = fn(fn(ft, "Frozen"), "content_hashes")
    keys = [ast.literal_eval(k) for r in ast.walk(chs) if isinstance(r, ast.Return) and isinstance(r.value, ast.Dict) for k in r.value.keys]
    print(f"Frozen.content_hashes returns keys {keys} (== CONTENT_HASH_KEYS as a set: {sorted(keys) == sorted(chk)}) | check_content: "
          f"{[ast.unparse(s).split(chr(10))[0] for s in body(cc)]} | check_data_dir: got[key] = check_content(key, sha) for each: "
          f"{'got[key] = self.check_content(key, sha)' in ast.unparse(cdd)}")
    ok &= sorted(keys) == sorted(chk) and "got[key] = self.check_content(key, sha)" in ast.unparse(cdd)
    used = {}
    for k in chk:
        labels = [lab for lab, (key, _) in dtr.items() if key == k]
        used[k] = my_table[labels[0]][0] if len(labels) == 1 else None
        same_row = len(labels) == 1 and labels[0] == MY_ROWS[k][0]
        print(f"  {k:<12} DATA_TABLE_ROWS label {labels} -> value in my reading of PROTOCOL_FROZEN {used[k]} | same row as my own reading: {same_row}")
        ok &= same_row and used[k] is not None

    print("\n== C. recomputed from data_d by the protocol rules, and from my round-3 regeneration")
    ex_lines = read_jsonl(os.path.join(dd, "facts.jsonl"))
    six = all(list(r) == FACT_FIELDS or sorted(r) == sorted(FACT_FIELDS) for r in ex_lines)
    facts = [{k: r[k] for k in FACT_FIELDS} for r in ex_lines]
    s_rows = read_jsonl(os.path.join(dd, "train_S.jsonl"))
    cands = json.load(open(os.path.join(dd, "candidates.json"), encoding="utf-8"))
    anchor = read_jsonl(os.path.join(dd, "anchor_text.jsonl"))
    docs = [r["doc"] for r in anchor] == list(range(len(anchor)))
    print(f"facts.jsonl {len(ex_lines)} lines, each exactly the 6 fields: {six} | train_S.jsonl {len(s_rows)} rows | candidates.json "
          f"{len(cands)} facts | anchor_text.jsonl {len(anchor)} rows, doc == line index: {docs}")
    ok &= six and len(ex_lines) == 160 and len(s_rows) == 120 and len(cands) == 160 and len(anchor) == 512 and docs
    tok = load_qwen(qdir)
    dec = [tok.decode(r["ids"]) for r in anchor]
    from_dd = {"facts": sha(canon(facts)), "train_S": sha(jsonl_bytes(s_rows)), "candidates": sha(canon(cands)),
               "anchor_texts": sha(canon([r["text"] for r in anchor]))}
    J = lambda n: json.load(open(os.path.join(mine, n), encoding="utf-8"))
    from_mine = {"facts": sha(canon(J("facts.json"))), "train_S": sha(jsonl_bytes(read_jsonl(os.path.join(mine, "train_S.jsonl")))),
                 "candidates": sha(canon(J("candidates.json"))), "anchor_texts": sha(canon([a["text"] for a in J("anchor.json")]))}
    print(f"anchor texts from my decode of data_d's ids: {sha(canon(dec))} | every decoded text == the stored text: {dec == [r['text'] for r in anchor]}")
    ok &= sha(canon(dec)) == from_dd["anchor_texts"] and dec == [r["text"] for r in anchor]
    for k in chk:
        same = from_dd[k] == from_mine[k] == used[k]
        print(f"  {k:<12} data_d {from_dd[k]} | my round-3 regeneration {from_mine[k]} | value verify_authorization compares with {used[k]} | ALL EQUAL {same}")
        ok &= same
    print(f"  -> the generator's condition 3 (content = check_data_dir(data_d)) and verify_authorization (content = data_hash) would compare the "
          f"record with the same dict for data_d: {all(from_dd[k] == used[k] for k in chk)}")

    print("\n== D. data_d unchanged since my round 3; the Executor's printed values")
    r3 = open(os.path.join(repo, "metrix/e1-pilot/audit/stdout/impl_b/36_id_compare.txt"), encoding="utf-8").read()
    rec3 = dict(re.findall(r"^  (\S+): rows \d+ \| byte ([0-9a-f]{64}) \|", r3, re.M))
    print(f"36_id_compare.txt section D lines parsed: {len(rec3)}")
    ok &= sorted(rec3) == sorted(DATA)
    for n in DATA:
        now = sha(open(os.path.join(dd, n), "rb").read())
        print(f"  {n}: now {now} | round 3 {rec3.get(n)} | unchanged {now == rec3.get(n)}")
        ok &= now == rec3.get(n)
    extra = sorted(set(os.listdir(dd)) - set(DATA))
    print(f"  other files in data_d: {extra} | test_qa.jsonl / general_test.jsonl present: {[x for x in ('test_qa.jsonl', 'general_test.jsonl') if x in extra]}")
    ok &= extra == ["leakage_report.json"]
    t8 = open(os.path.join(repo, "metrix/e1-pilot/reports/impl_b/t8_fix_commit.txt"), encoding="utf-8").read().split("\n")
    gen = dict(re.findall(r"^frozen content hash (\w+)\s+([0-9a-f]{64}) = PROTOCOL_FROZEN \(read back from <SCRATCH>/data_d\)$", "\n".join(t8[19:23]), re.M))
    ver_ = dict(re.findall(r"^frozen content hash (\w+)\s+([0-9a-f]{64}) = PROTOCOL_FROZEN$", "\n".join(t8[37:41]), re.M))
    for k in chk:
        same = gen.get(k) == ver_.get(k) == used[k]
        print(f"  {k:<12} Executor t8 generate (line {20 + list(chk).index(k)}) {gen.get(k)} | t8 verify (line {38 + list(chk).index(k)}) {ver_.get(k)} | == mine {same}")
        ok &= same
    return bool(ok)


run(main)
