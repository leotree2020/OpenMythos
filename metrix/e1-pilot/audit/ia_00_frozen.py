"""IA-0: frozen state used by this audit (Data Auditor's own script; no Executor code imported, called or copied).

  a. metrix/e1-pilot/PROTOCOL_FROZEN (working tree == HEAD blob, nothing staged for it) names v1.1 as the current
     version and 87a244db28a901f9e89282b50df76778ab5c2887 as the v1.1 freeze commit; the tag
     metrix-e1-pilot-frozen-v1.1 points to it.
  b. the four sha256 lines of the v1.1 section == sha256 of `git cat-file blob <freeze>:<path>` == sha256 of the
     working-tree file (protocol and the three JSON unchanged since the freeze commit).
  c. the 12 rows of the "全部数据哈希" table == the values at the named places of the freeze-commit manifests;
     the protocol text of the freeze commit carries the same fact (2.2), candidates (2.5) and train_S (2.6) values.
Prints AUDIT_VALUE frozen:<name> lines (the expected values used by the other ia_ scripts, which read them from the
freeze commit themselves).
usage: python -I ia_00_frozen.py <repo_root>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import re
from ia_common import FROZEN, git, blob, sha, file_sha, frozen_json, frozen_protocol, run

FILES = ["metrix/e1-pilot/METRIX_E1_PROTOCOL.md", "metrix/e1-pilot/DATA_MANIFEST.json",
         "metrix/e1-pilot/SPLIT_MANIFEST.json", "metrix/e1-pilot/SEARCH_SPACE.json"]


def main():
    repo = sys.argv[1]
    ok = True
    print("HEAD:", git(repo, "rev-parse", "HEAD").stdout.decode().strip(),
          "| branch:", git(repo, "branch", "--show-current").stdout.decode().strip())
    pf_path = "metrix/e1-pilot/PROTOCOL_FROZEN"
    pf_wt = open(os.path.join(repo, pf_path), "rb").read()
    pf_head = blob(repo, "HEAD", pf_path)
    staged = git(repo, "diff", "--cached", "--name-only", "--", pf_path).stdout.decode().split()
    print(f"\n== a. PROTOCOL_FROZEN: working tree == HEAD blob {pf_wt == pf_head} | staged changes to it: {staged}")
    ok &= pf_wt == pf_head and not staged
    pf = pf_wt.decode("utf-8")
    cur = re.search(r"^当前有效版本[:：]\s*(v[0-9.]+)\s*$", pf, re.M)
    print("  current valid version line:", cur and cur.group(0))
    ok &= bool(cur) and cur.group(1) == "v1.1"
    sec11 = pf.split("## v1.1(当前有效)", 1)[1].split("\n## v1(", 1)[0]
    m = re.search(r"\| v1\.1 冻结提交\(完整 hash\) \| `([0-9a-f]{40})` \|", sec11)
    print("  v1.1 freeze commit in the current section:", m and m.group(1), "| == audit constant:", bool(m) and m.group(1) == FROZEN)
    ok &= bool(m) and m.group(1) == FROZEN
    tag = git(repo, "rev-parse", "metrix-e1-pilot-frozen-v1.1^{commit}", check=False).stdout.decode().strip()
    print("  tag metrix-e1-pilot-frozen-v1.1 ->", tag, "| == freeze commit:", tag == FROZEN)
    ok &= tag == FROZEN
    anc = git(repo, "merge-base", "--is-ancestor", FROZEN, "HEAD", check=False).returncode
    print("  freeze commit is an ancestor of HEAD:", anc == 0)
    ok &= anc == 0

    print("\n== b. four files: PROTOCOL_FROZEN v1.1 value | git cat-file blob <freeze> | working tree")
    listed = dict((p, h) for h, p in re.findall(r"^([0-9a-f]{64})  (\S+)$", sec11, re.M))
    for p in FILES:
        hb = sha(blob(repo, FROZEN, p))
        hw = file_sha(os.path.join(repo, p))
        eq = listed.get(p) == hb == hw
        ok &= eq
        print(f"  {p}: listed {listed.get(p)} | blob {hb} | worktree {hw} | ALL EQUAL {eq}")

    print("\n== c. data hash table (v1 section, valid for v1.1) vs freeze-commit manifests")
    dm, sm = frozen_json(repo, "DATA_MANIFEST.json"), frozen_json(repo, "SPLIT_MANIFEST.json")
    proto = frozen_protocol(repo)
    rows = re.findall(r"^\| (.+?) \| `([0-9a-f]{64})` \| (.+?) \| (.+?) \|$", pf.split("### 全部数据哈希", 1)[1].split("\n### ", 1)[0], re.M)
    print("  table rows parsed:", len(rows))
    ok &= len(rows) == 12
    parquet_pin = re.findall(r"sha256 ([0-9a-f]{64})", dm["anchor_text"]["source"])
    tokf = dm["model"]["tokenizer"]["files_sha256"]
    where = {
        "fact(160 条)": ("facts", dm["name_generation"]["expected_facts_canonical_sha256"]),
        "锚文本(512 篇解码文本)": ("anchor_texts", dm["anchor_text"]["decoded_texts_canonical_sha256"]),
        "锚文本源 parquet": ("anchor_parquet", parquet_pin[0] if len(parquet_pin) == 1 else None),
        "`train_S.jsonl`": ("train_S", dm["s_permutation"]["expected_train_S_canonical_sha256"]),
        "`candidates.json`": ("candidates", sm["candidates"]["candidate_mapping_sha256"]),
        "模板集合(32 个)": ("template_set", sm["template_freeze"]["template_set_sha256"]),
        "Qwen `tokenizer.json`": ("qwen:tokenizer.json", tokf["tokenizer.json"]),
        "Qwen `tokenizer_config.json`": ("qwen:tokenizer_config.json", tokf["tokenizer_config.json"]),
        "Qwen `vocab.json`": ("qwen:vocab.json", tokf["vocab.json"]),
        "Qwen `merges.txt`": ("qwen:merges.txt", tokf["merges.txt"]),
        "parcae 分词器 `tokenizer.json`": ("parcae:tokenizer.json", dm["general_text"]["decode_tokenizer_json_sha256"]),
        "`eval_sets.jsonl`": ("eval_sets.jsonl", dm["general_text"]["source_file_sha256"]),
    }
    seen = set()
    for item, val, _d, _loc in rows:
        key, mval = where.get(item, (None, None))
        eq = key is not None and val == mval
        ok &= eq
        seen.add(item)
        print(f"  {item}: table {val} | manifest {mval} | MATCH {eq}")
        if key:
            print(f"AUDIT_VALUE frozen:{key} {val}")
    ok &= seen == set(where)
    for label, pat, key in (("2.2 fact", r"规范化 SHA-256 必须等于 `([0-9a-f]{64})`。参考实现 `reports/round2/names.py`", "facts"),
                            ("2.5 candidates", r"`candidates\.json` 的规范化 SHA-256 必须等于 `([0-9a-f]{64})`", "candidates"),
                            ("2.6 train_S", r"`train_S\.jsonl` 的规范化 SHA-256 必须等于 `([0-9a-f]{64})`", "train_S")):
        mm = re.search(pat, proto)
        exp = {v[0]: v[1] for v in where.values()}[key]
        eq = bool(mm) and mm.group(1) == exp
        ok &= eq
        print(f"  protocol (freeze commit) {label} value {mm and mm.group(1)} | == manifest: {eq}")
    print("  anchor hash rule (DATA_MANIFEST anchor_text.decoded_texts_hash_rule):", dm["anchor_text"]["decoded_texts_hash_rule"])
    print("  manifest files.* status:", {k: v["status"] for k, v in dm["files"].items()})
    print("  SPLIT_MANIFEST split_sha256:", sm["split_sha256"])
    return bool(ok)


run(main)
