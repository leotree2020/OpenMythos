"""R9-C: one table of every hash of round 9 item 5 for the v1.1 freeze commit: auditor value (AUDIT_VALUE lines of
this round's auditor stdout files), the v1 values (PROTOCOL_FROZEN table / sha256 block and the v1 freeze commit's
manifests), the values written in the commit under audit (manifests, read from git objects), and the Executor's
printed values. Data Auditor's own script; the Executor's files are read as text only (regular expressions over
printed output); no Executor code is imported, called or copied. Exceptions -> RESULT: FAIL (r6_guard).

Executor outputs used:
  reports/round9/t5_frozen_hashes_<commit[:8]>.txt (working tree, untracked at audit time; required)
  reports/round9/t1_protocol_checks.txt at the commit (pre-commit sha256sum of the working tree; informational)
PASS iff
  - item 1: the auditor's four file sha256 equal the Executor's t5 values; the auditor's v1 file sha256 equal the
    PROTOCOL_FROZEN sha256 block and the Executor's v1 lines;
  - item 2: for every data hash the auditor value == PROTOCOL_FROZEN table value (where the table has the item)
    == v1 freeze-commit manifest value == commit manifest value, and every Executor value found equals it;
    every one of the 12 PROTOCOL_FROZEN table rows is compared; the 32 per-template values are compared with both
    manifests;
  - every auditor value is used in the table.
usage: python -I r9_compare.py <repo_root> <commit> <v1_commit> <auditor_stdout_dir>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import glob, json, re, subprocess
from r6_guard import run

H = r"([0-9a-f]{64})"
D = "metrix/e1-pilot/"


def git_blob(repo, rev, path):
    return subprocess.run(["git", "-C", repo, "cat-file", "blob", f"{rev}:{path}"], capture_output=True, check=True).stdout


def manifest_values(repo, rev):
    dm = json.loads(git_blob(repo, rev, D + "DATA_MANIFEST.json"))
    sm = json.loads(git_blob(repo, rev, D + "SPLIT_MANIFEST.json"))
    pin = re.findall(r"sha256 ([0-9a-f]{64})", dm["anchor_text"]["source"])
    assert len(pin) == 1, pin
    v = {"facts_canonical_sha256": dm["name_generation"]["expected_facts_canonical_sha256"],
         "facts_canonical_sha256_from_jsonl": dm["name_generation"]["expected_facts_canonical_sha256"],
         "anchor_decoded_texts_canonical_sha256": dm["anchor_text"]["decoded_texts_canonical_sha256"],
         "parquet_sha256": pin[0],
         "train_S_canonical_sha256": dm["s_permutation"]["expected_train_S_canonical_sha256"],
         "candidates_canonical_sha256": sm["candidates"]["candidate_mapping_sha256"],
         "template_set_sha256": sm["template_freeze"]["template_set_sha256"],
         "parcae_tokenizer_json_sha256": dm["general_text"]["decode_tokenizer_json_sha256"],
         "eval_sets_jsonl_sha256": dm["general_text"]["source_file_sha256"]}
    for f, h in dm["model"]["tokenizer"]["files_sha256"].items():
        v[f"qwen_tokenizer_sha256:{f}"] = h
    for t in sm["templates"]:
        v[f"template_normalized_sha256:{t['template_id']}"] = t["normalized_sha256"]
    return v


def main():
    repo, commit, v1, sdir = sys.argv[1:5]
    rp = lambda r: subprocess.run(["git", "-C", repo, "rev-parse", r + "^{commit}"], capture_output=True, check=True, text=True).stdout.strip()
    commit, v1 = rp(commit), rp(v1)
    mine = {}
    files = sorted(f for f in glob.glob(os.path.join(sdir, "[0-9][0-9]_r[89]_*.txt")) if "_compare" not in os.path.basename(f))
    for f in files:
        for line in open(f, encoding="utf-8"):
            m = re.match(r"AUDIT_VALUE (\S+) ([0-9a-f]{64})$", line.rstrip("\n"))
            if m:
                assert m.group(1) not in mine or mine[m.group(1)] == m.group(2), m.group(1)
                mine[m.group(1)] = m.group(2)
    print("auditor values read:", len(mine), "from", [os.path.basename(x) for x in files])
    for f in files:
        last = [l.rstrip("\n") for l in open(f, encoding="utf-8")][-2:]
        print(f"  {os.path.basename(f)}: {last}")

    pf = git_blob(repo, commit, D + "PROTOCOL_FROZEN").decode("utf-8")
    pf_files = {p: h for h, p in re.findall(r"^" + H + r"  (metrix/e1-pilot/\S+)$", pf, flags=re.M)}
    pf_rows = re.findall(r"^\| (.+?) \| `" + H + r"` \|", pf, flags=re.M)
    print("PROTOCOL_FROZEN (at the commit): sha256-block lines", len(pf_files), "| data-table rows", len(pf_rows))
    pf_map = {"fact(160 条)": "facts_canonical_sha256", "锚文本(512 篇解码文本)": "anchor_decoded_texts_canonical_sha256",
              "锚文本源 parquet": "parquet_sha256", "`train_S.jsonl`": "train_S_canonical_sha256",
              "`candidates.json`": "candidates_canonical_sha256", "模板集合(32 个)": "template_set_sha256",
              "Qwen `tokenizer.json`": "qwen_tokenizer_sha256:tokenizer.json",
              "Qwen `tokenizer_config.json`": "qwen_tokenizer_sha256:tokenizer_config.json",
              "Qwen `vocab.json`": "qwen_tokenizer_sha256:vocab.json", "Qwen `merges.txt`": "qwen_tokenizer_sha256:merges.txt",
              "parcae 分词器 `tokenizer.json`": "parcae_tokenizer_json_sha256", "`eval_sets.jsonl`": "eval_sets_jsonl_sha256"}
    pf_vals = {}
    for label, h in pf_rows:
        key = pf_map.get(label)
        print(f"  PROTOCOL_FROZEN row {label!r} -> {key}")
        pf_vals[key] = h
    ok = len(pf_rows) == 12 and None not in pf_vals and set(pf_vals) == set(pf_map.values())
    print("all 12 PROTOCOL_FROZEN data rows mapped:", ok)
    pf_vals["facts_canonical_sha256_from_jsonl"] = pf_vals.get("facts_canonical_sha256")

    t5p = os.path.join(repo, D, "reports/round9", f"t5_frozen_hashes_{commit[:8]}.txt")
    t5 = open(t5p, encoding="utf-8").read() if os.path.exists(t5p) else ""
    t1 = git_blob(repo, commit, D + "reports/round9/t1_protocol_checks.txt").decode("utf-8", errors="replace")
    print(f"Executor {os.path.basename(t5p)} present: {bool(t5)} | t1_protocol_checks.txt@{commit[:8]} bytes {len(t1.encode('utf-8'))}")
    ok &= bool(t5)
    ex_lab = {"facts": "facts_canonical_sha256", "anchor decoded texts": "anchor_decoded_texts_canonical_sha256",
              "train_S": "train_S_canonical_sha256", "candidates": "candidates_canonical_sha256",
              "template set": "template_set_sha256", "eval_sets.jsonl": "eval_sets_jsonl_sha256",
              "parcae tokenizer.json": "parcae_tokenizer_json_sha256"}
    ex = {commit: {}, v1: {}}
    for rev in (commit, v1):
        m = re.search(r"^" + rev[:8] + r" (\d+) values\n((?:  .+\n)+)", t5, flags=re.M)
        if not m:
            print(f"Executor t5: no value block for {rev[:8]}")
            continue
        for line in m.group(2).splitlines():
            mm = re.fullmatch(r"  (.+?) +" + H, line)
            lab = mm.group(1)
            key = ex_lab.get(lab) or ("qwen_tokenizer_sha256:" + lab[5:] if lab.startswith("qwen ") else None)
            assert key, lab
            ex[rev][key] = mm.group(2)
        print(f"Executor t5 block {rev[:8]}: {m.group(1)} values parsed {len(ex[rev])}")
    ex[commit]["facts_canonical_sha256_from_jsonl"] = ex[commit].get("facts_canonical_sha256")
    ex[v1]["facts_canonical_sha256_from_jsonl"] = ex[v1].get("facts_canonical_sha256")

    used = set()
    print("\n== item 1: file sha256 of the protocol and the three JSON")
    for name in ("METRIX_E1_PROTOCOL.md", "DATA_MANIFEST.json", "SPLIT_MANIFEST.json", "SEARCH_SPACE.json"):
        a, a1 = mine.get(f"file_sha256:{name}"), mine.get(f"v1_file_sha256:{name}")
        used |= {f"file_sha256:{name}", f"v1_file_sha256:{name}"}
        e = re.findall(r"^" + H + r"  " + re.escape(D + name) + "$", t5, flags=re.M)
        e1 = re.findall(r"^" + H + r"  " + re.escape(D + name) + r" \(v1 freeze commit " + v1[:8] + r"\)$", t5, flags=re.M)
        et1 = re.findall(r"^" + H + r"  " + re.escape(D + name) + "$", t1, flags=re.M)
        r_ok = a is not None and bool(e) and all(x == a for x in e) and all(x == a for x in et1)
        r1_ok = a1 is not None and a1 == pf_files.get(D + name) and bool(e1) and all(x == a1 for x in e1)
        ok &= r_ok and r1_ok
        print(f"{name}\n    {commit[:8]} auditor {a}\n             Executor t5 {sorted(set(e))} | Executor t1 (pre-commit working tree) "
              f"{sorted(set(et1))} | equal: {r_ok}\n    v1 {v1[:8]} auditor {a1}\n             PROTOCOL_FROZEN {pf_files.get(D + name)} | "
              f"Executor t5 {sorted(set(e1))} | equal: {r1_ok}")

    print("\n== item 2: data hashes (auditor | PROTOCOL_FROZEN | v1 manifest | commit manifest | Executor t5 v1 / commit)")
    mv1, mc = manifest_values(repo, v1), manifest_values(repo, commit)
    print("manifest value keys: v1", len(mv1), "| commit", len(mc), "| same keys:", set(mv1) == set(mc))
    ok &= set(mv1) == set(mc)
    n_rows = n_ok = 0
    for key in mc:
        a = mine.get(key)
        used.add(key)
        p, x1, xc = pf_vals.get(key), ex[v1].get(key), ex[commit].get(key)
        vals = [a, mv1[key], mc[key]] + ([p] if p else []) + [x for x in (x1, xc) if x]
        r_ok = a is not None and all(v == a for v in vals)
        n_rows += 1
        n_ok += r_ok
        ok &= r_ok
        print(f"{key}\n    auditor {a}\n    PROTOCOL_FROZEN {p or '- (no row)'} | v1 manifest {'same' if mv1[key] == a else mv1[key]} | "
              f"commit manifest {'same' if mc[key] == a else mc[key]} | Executor t5 v1 {'same' if x1 == a else (x1 or 'not printed')} | "
              f"commit {'same' if xc == a else (xc or 'not printed')} | ALL EQUAL {r_ok}")
    print(f"\ndata rows: {n_rows} | all values equal: {n_ok}/{n_rows}")
    unused = sorted(set(mine) - used)
    print("auditor values not used in the table:", unused)
    ok &= not unused
    pf_only = sorted(set(pf_vals) - set(mc))
    print("PROTOCOL_FROZEN rows without a manifest key (must be empty):", pf_only)
    ok &= not pf_only
    return ok


run(main)
