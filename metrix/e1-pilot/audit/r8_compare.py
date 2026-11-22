"""R8-C: one table of every frozen hash: auditor value (AUDIT_VALUE lines of this round's auditor stdout files),
value written in the freeze commit (manifests / protocol, read again here from git objects), and the value(s) printed
in the Executor's raw outputs of round 8. Data Auditor's own script; the Executor's files are read as text only
(regular expressions over their printed output); no Executor code is imported, called or copied.
Exceptions -> RESULT: FAIL (r6_guard).

Executor outputs used:
  reports/round8/t0_env.txt, t1d_data_hashes.txt, t1_protocol_checks.txt   (git objects of the freeze commit)
  reports/round8/t5_frozen_hashes.txt                                     (working tree; untracked at audit time)
The Executor's text files are decoded with errors="replace" (t1_protocol_checks.txt has lines cut in the middle of
UTF-8 sequences; only ASCII hashes are parsed, so replacement characters cannot change a parsed value).
PASS iff for every item the auditor value equals the freeze-commit value and every Executor value found equals it,
and every item has at least one Executor value.
usage: python -I r8_compare.py <repo_root> <commit> <auditor_stdout_dir>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import glob, json, re, subprocess
from r6_guard import run

H = r"([0-9a-f]{64})"


def git_blob(repo, commit, path):
    return subprocess.run(["git", "-C", repo, "cat-file", "blob", f"{commit}:{path}"], capture_output=True, check=True).stdout


def main():
    repo, commit, sdir = sys.argv[1:4]
    mine = {}
    for f in sorted(glob.glob(os.path.join(sdir, "0[2-8]_r8_*.txt"))):
        for line in open(f, encoding="utf-8"):
            m = re.match(r"AUDIT_VALUE (\S+) ([0-9a-f]{64})$", line.rstrip("\n"))
            if m:
                assert m.group(1) not in mine or mine[m.group(1)] == m.group(2), m.group(1)
                mine[m.group(1)] = m.group(2)
    print("auditor values read:", len(mine), "from", sorted(os.path.basename(x) for x in glob.glob(os.path.join(sdir, "0[2-8]_r8_*.txt"))))
    dm = json.loads(git_blob(repo, commit, "metrix/e1-pilot/DATA_MANIFEST.json"))
    sm = json.loads(git_blob(repo, commit, "metrix/e1-pilot/SPLIT_MANIFEST.json"))
    r8 = "metrix/e1-pilot/reports/round8/"
    t0 = git_blob(repo, commit, r8 + "t0_env.txt").decode("utf-8", errors="replace")
    t1d = git_blob(repo, commit, r8 + "t1d_data_hashes.txt").decode("utf-8", errors="replace")
    t1 = git_blob(repo, commit, r8 + "t1_protocol_checks.txt").decode("utf-8", errors="replace")
    t5p = os.path.join(repo, r8, "t5_frozen_hashes.txt")
    t5 = open(t5p, encoding="utf-8", errors="replace").read() if os.path.exists(t5p) else ""
    print("Executor t5_frozen_hashes.txt present in working tree:", bool(t5))

    def ex(*pairs):
        vals = []
        for text, pat in pairs:
            vals += re.findall(pat, text, flags=re.M)
        return vals

    rows = []
    for name in ("METRIX_E1_PROTOCOL.md", "DATA_MANIFEST.json", "SPLIT_MANIFEST.json", "SEARCH_SPACE.json"):
        rows.append((f"1 file sha256 {name}@{commit[:8]}", f"file_sha256:{name}",
                     "(no manifest field; PROTOCOL_FROZEN not yet written)", None,
                     ex((t5, H + r"  metrix/e1-pilot/" + re.escape(name) + "@" + commit + "$"),
                        (t1, H + r"  metrix/e1-pilot/" + re.escape(name) + "$"))))
    rows.append(("2 facts (160) canonical", "facts_canonical_sha256", "DATA_MANIFEST name_generation.expected_facts_canonical_sha256",
                 dm["name_generation"]["expected_facts_canonical_sha256"], ex((t1d, r"facts canonical sha256: " + H))))
    pin = re.search(r"sha256 ([0-9a-f]{64})", dm["anchor_text"]["source"]).group(1)
    rows.append(("3 anchor parquet file sha256", "parquet_sha256", "DATA_MANIFEST anchor_text.source (sha256 ...)", pin,
                 ex((t1d, r"file sha256 " + H + ", pinned"), (t0, H + r"  \./parquet/data/sample-100BT/train/shard_00000\.parquet$"))))
    rows.append(("3 anchor 512 decoded texts canonical", "anchor_decoded_texts_canonical_sha256",
                 "DATA_MANIFEST anchor_text.decoded_texts_canonical_sha256", dm["anchor_text"]["decoded_texts_canonical_sha256"],
                 ex((t1d, r"anchor texts canonical sha256 " + H), (t1d, r"\(protocol section 0 rule\) " + H))))
    rows.append(("4 train_S.jsonl canonical", "train_S_canonical_sha256", "DATA_MANIFEST s_permutation.expected_train_S_canonical_sha256",
                 dm["s_permutation"]["expected_train_S_canonical_sha256"],
                 ex((t1d, r"train_S\.jsonl\s+rows 120, byte_sha256 [0-9a-f]{64}, canonical_sha256 " + H))))
    rows.append(("4 candidates.json canonical", "candidates_canonical_sha256", "SPLIT_MANIFEST candidates.candidate_mapping_sha256",
                 sm["candidates"]["candidate_mapping_sha256"],
                 ex((t1d, r"candidates\.json facts 160, byte_sha256 [0-9a-f]{64}, canonical_sha256 " + H))))
    ex_tmpl_ok = "normalized / normalized_sha256 not reproduced: []" in t1
    for t in sm["templates"]:
        rows.append((f"5 template {t['template_id']}", f"template_normalized_sha256:{t['template_id']}",
                     "SPLIT_MANIFEST templates[].normalized_sha256", t["normalized_sha256"],
                     [t["normalized_sha256"]] if ex_tmpl_ok else []))
    rows.append(("5 template_set_sha256", "template_set_sha256", "SPLIT_MANIFEST template_freeze.template_set_sha256",
                 sm["template_freeze"]["template_set_sha256"], ex((t1, r"template_set_sha256 recomputed " + H))))
    for f, v in dm["model"]["tokenizer"]["files_sha256"].items():
        rows.append((f"6 Qwen {f}", f"qwen_tokenizer_sha256:{f}", "DATA_MANIFEST model.tokenizer.files_sha256", v,
                     ex((t0, H + r"  \./qwen_tok/" + re.escape(f) + "$"), (t1d, H + r"  " + re.escape(f) + "$"))))
    rows.append(("7 parcae tokenizer.json", "parcae_tokenizer_json_sha256", "DATA_MANIFEST general_text.decode_tokenizer_json_sha256",
                 dm["general_text"]["decode_tokenizer_json_sha256"], ex((t0, H + r"  \./parcae_tok/tokenizer\.json$"))))
    rows.append(("7 eval_sets.jsonl", "eval_sets_jsonl_sha256", "DATA_MANIFEST general_text.source_file_sha256",
                 dm["general_text"]["source_file_sha256"], ex((t0, H + r"  \.\./\.\./research/mini_mythos/stage1/results/r1/eval_sets\.jsonl$"))))
    ok = True
    print("\nitem | auditor value | freeze-commit value (field) | Executor value(s) | auditor==commit | Executor==auditor")
    for label, key, field, commit_v, exv in rows:
        a = mine.get(key)
        c_ok = True if commit_v is None else (a == commit_v)
        e_ok = bool(exv) and all(v == a for v in exv)
        ok &= a is not None and c_ok and e_ok
        print(f"{label}\n    auditor  {a}\n    commit   {commit_v if commit_v else '-'}  [{field}]\n"
              f"    Executor {sorted(set(exv)) if exv else 'NOT FOUND'} (occurrences {len(exv)})\n"
              f"    auditor==commit {c_ok if commit_v else 'n/a'} | Executor==auditor {e_ok}")
    if ex_tmpl_ok:
        print("\nnote: for the 32 per-template values the Executor printed only that no template failed to reproduce "
              "(t1_protocol_checks.txt: 'normalized / normalized_sha256 not reproduced: []'); its value is therefore the manifest value.")
    unused = sorted(set(mine) - {r[1] for r in rows})
    print("auditor values not used in the table:", unused)
    ok &= not unused
    print("rows:", len(rows))
    return ok


run(main)
