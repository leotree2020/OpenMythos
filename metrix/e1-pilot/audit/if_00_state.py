"""IF-0 (implementation stage B, report commit, round 5 of the auditor): the state audited in this round, and the fixed inputs.
  a. HEAD == 493d7f9c102cae3ebb916f1d72fcc1759b26bee8 (the second fix commit, audited in my round 4); no unstaged change
     under metrix/ except my own new files of this round (audit/if_*.py, audit/stdout/impl_b/5x_*.txt, untracked);
     the staged change == the review inputs of this round:
       (1) review_report/report_commit_input.diff == `git diff --cached --stat`, an empty line, `git diff --cached`;
       (2) review_report/report_commit_input_src_tests_reports.diff == the same restricted to metrix/e1-pilot/src,
           tests, reports;
     their sha256 == the values in review_report/preflight_tools_check_report-commit.txt; nothing staged outside
     metrix/e1-pilot/; the staged files listed by area; every staged file under audit/ has index bytes == working-tree
     bytes; files the staged change does NOT touch and that my checks rely on: working tree == HEAD blob.
  b. input files: sha256 of my own download (<my_dl>) and of the Executor's copies (<executor_inputs>) == the
     freeze-commit DATA_MANIFEST values; no weight-like file in either directory.
  c. eval_sets.jsonl: sha256 of the whole file == DATA_MANIFEST general_text.source_file_sha256; then, reading the
     file in BINARY mode, for every line only the split value located in the line prefix (b'"split": "' within the
     first 80 bytes) is counted.  No line is UTF-8-decoded or JSON-parsed here; nothing else about any line is computed.
Data Auditor's own script (adapted from my ie_00_state.py); no Executor code imported, called or copied.
usage: python -I if_00_state.py <repo_root> <scratch_dir> <my_dl_dir> <executor_inputs_dir>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import re
from collections import Counter
from ia_common import git, sha, file_sha, frozen_json, run

EXPECT_HEAD = "493d7f9c102cae3ebb916f1d72fcc1759b26bee8"
PQ = "data/sample-100BT/train/shard_00000.parquet"
WEIGHT_EXT = (".safetensors", ".bin", ".pt", ".pth", ".gguf", ".h5", ".msgpack", ".ckpt", ".onnx")
KEY = b'"split": "'
AREAS = ("metrix/e1-pilot/src", "metrix/e1-pilot/tests", "metrix/e1-pilot/reports")
UNTOUCHED = ["metrix/e1-pilot/src/metrix_e1/data.py", "metrix/e1-pilot/src/metrix_e1/stops.py",
             "metrix/e1-pilot/src/metrix_e1/mode.py", "metrix/e1-pilot/src/metrix_e1/contract.py",
             "metrix/e1-pilot/src/metrix_e1/train.py", "metrix/e1-pilot/src/metrix_e1/interpretations.py",
             "metrix/e1-pilot/reports/round5/l6_check.py", "metrix/e1-pilot/reports/round2/anchor_check.py",
             "metrix/e1-pilot/reports/round2/gen_facts.py", "metrix/e1-pilot/reports/round7/gen_s_cands.py",
             "metrix/e1-pilot/tests/conftest.py", "metrix/e1-pilot/tests/test_st12.py",
             "metrix/e1-pilot/PROTOCOL_FROZEN", "metrix/e1-pilot/DATA_MANIFEST.json", "metrix/e1-pilot/SPLIT_MANIFEST.json",
             "metrix/e1-pilot/SEARCH_SPACE.json", "metrix/e1-pilot/METRIX_E1_PROTOCOL.md"]
MINE_THIS_ROUND = re.compile(r"^metrix/e1-pilot/audit/(if_\d\d_[a-z_]+\.py|stdout/impl_b/5\d_[a-z0-9_]+\.txt|stdout/impl_b/trials/if_[a-z0-9_]+\.txt)$")


def main():
    repo, scratch, dl, exin = sys.argv[1:5]
    ok = True
    print("== a. state")
    head = git(repo, "rev-parse", "HEAD").stdout.decode().strip()
    print(f"HEAD {head} | == {EXPECT_HEAD}: {head == EXPECT_HEAD} | branch {git(repo, 'branch', '--show-current').stdout.decode().strip()}")
    ok &= head == EXPECT_HEAD
    unstaged = git(repo, "diff", "--name-only", "--", "metrix").stdout.decode().split()
    untracked = git(repo, "ls-files", "--others", "--exclude-standard", "--", "metrix").stdout.decode().split()
    not_mine = [u for u in untracked if not MINE_THIS_ROUND.match(u)]
    print(f"unstaged changes under metrix/ (working tree vs index): {unstaged}")
    print(f"untracked files under metrix/: {len(untracked)}, all my own new files of this round (audit/if_*.py, audit/stdout/impl_b/5x_*.txt, audit/stdout/impl_b/trials/if_*.txt): "
          f"{not not_mine} | others: {not_mine}")
    ok &= not unstaged and not not_mine
    rr = os.path.join(scratch, "review_report")
    staged = git(repo, "diff", "--cached").stdout
    stat = git(repo, "diff", "--cached", "--stat").stdout
    full = open(os.path.join(rr, "report_commit_input.diff"), "rb").read()
    whole = stat + b"\n" + staged
    print(f"(git diff --cached --stat; echo; git diff --cached) sha256 {sha(whole)} | "
          f"report_commit_input.diff sha256 {sha(full)} | identical {whole == full}")
    ok &= whole == full
    sub_staged = git(repo, "diff", "--cached", "--", *AREAS).stdout
    sub_stat = git(repo, "diff", "--cached", "--stat", "--", *AREAS).stdout
    sub = open(os.path.join(rr, "report_commit_input_src_tests_reports.diff"), "rb").read()
    sub_whole = sub_stat + b"\n" + sub_staged
    same_sub = sub_whole == sub
    print(f"(same, restricted to src/ tests/ reports/) sha256 {sha(sub_whole)} | "
          f"report_commit_input_src_tests_reports.diff sha256 {sha(sub)} | identical {same_sub}")
    ok &= same_sub
    pre = open(os.path.join(rr, "preflight_tools_check_report-commit.txt"), encoding="utf-8").read()
    for name, blob_ in (("report_commit_input.diff", full), ("report_commit_input_src_tests_reports.diff", sub)):
        rec = re.findall(r"^([0-9a-f]{64})  <SCRATCH>/review_report/" + re.escape(name) + "$", pre, re.M)
        print(f"{name}: sha256 {sha(blob_)} | recorded in preflight_tools_check_report-commit.txt {rec} | MATCH {rec == [sha(blob_)]}")
        ok &= rec == [sha(blob_)]
    for tag in ("data-auditor_TOOLS_LINE_IDENTICAL", "data-auditor_FRONTMATTER_IDENTICAL"):
        print(f"preflight_tools_check_report-commit.txt records {tag}: {tag in pre}")
        ok &= tag in pre
    names = [ln.split("\t") for ln in git(repo, "diff", "--cached", "--name-status").stdout.decode().strip().split("\n")]
    outside = [n for n in names if not n[-1].startswith("metrix/e1-pilot/")]
    print(f"staged files: {len(names)} | outside metrix/e1-pilot/: {outside}")
    ok &= not outside
    groups = {}
    for st, p in ((n[0], n[-1]) for n in names):
        parts = p.split("/")
        key = "/".join(parts[:4]) if parts[2] in ("audit", "reviews") and len(parts) > 4 else "/".join(parts[:3])
        if p.startswith("metrix/e1-pilot/audit/stdout/impl_b/"):
            key = "metrix/e1-pilot/audit/stdout/impl_b/trials" if "/trials/" in p else "metrix/e1-pilot/audit/stdout/impl_b"
        elif p.startswith("metrix/e1-pilot/audit/"):
            key = "metrix/e1-pilot/audit (scripts)"
        elif p.startswith("metrix/e1-pilot/src/") or p.startswith("metrix/e1-pilot/tests/") or p.startswith("metrix/e1-pilot/reports/"):
            key = p
        groups.setdefault(key, []).append((st, p))
    for k in sorted(groups):
        v = groups[k]
        if len(v) == 1 and v[0][1] == k:
            print(f"  {v[0][0]} {k}")
        else:
            print(f"  {k}: {len(v)} files, status {sorted(Counter(s for s, _ in v).items())}"
                  + (f" | {[os.path.basename(p) for _, p in v]}" if "audit" in k else ""))
    audit_staged = [p for st, p in ((n[0], n[-1]) for n in names) if p.startswith("metrix/e1-pilot/audit/")]
    diffs = []
    for p in audit_staged:
        idx = git(repo, "cat-file", "blob", f":{p}").stdout
        wt = open(os.path.join(repo, p), "rb").read()
        if idx != wt:
            diffs.append(p)
    print(f"staged files under audit/: {len(audit_staged)} | index bytes != working-tree bytes: {diffs}")
    ok &= not diffs
    audit_wt = sorted(os.path.relpath(os.path.join(r, f), repo) for r, _, fs in os.walk(os.path.join(repo, "metrix/e1-pilot/audit")) for f in fs)
    in_index = set(git(repo, "ls-files", "--", "metrix/e1-pilot/audit").stdout.decode().split())
    not_in_index = [p for p in audit_wt if p not in in_index]
    print(f"files under audit/ in the working tree: {len(audit_wt)} | not in the index: {not_in_index} (expected: only this round's own new files)")
    ok &= all(MINE_THIS_ROUND.match(p) for p in not_in_index)
    head_audit = set(git(repo, "ls-tree", "-r", "--name-only", "HEAD", "--", "metrix/e1-pilot/audit").stdout.decode().split())
    added = sorted(in_index - head_audit)
    print(f"audit/ files in the index but not at HEAD: {len(added)} | == the staged audit/ files: {sorted(added) == sorted(audit_staged)}")
    ok &= sorted(added) == sorted(audit_staged)
    staged_paths = {n[-1] for n in names}
    for rel in UNTOUCHED:
        wt = open(os.path.join(repo, rel), "rb").read()
        hb = git(repo, "cat-file", "blob", f"HEAD:{rel}").stdout
        same = wt == hb and rel not in staged_paths
        ok &= same
        print(f"  not in the staged change, working tree == HEAD blob: {rel}: {same}")

    print("\n== b. input files vs the freeze-commit DATA_MANIFEST")
    dm = frozen_json(repo, "DATA_MANIFEST.json")
    pin = re.findall(r"sha256 ([0-9a-f]{64})", dm["anchor_text"]["source"])
    expected = [(("qwen_tok", f), ("qwen_tokenizer", f), v) for f, v in dm["model"]["tokenizer"]["files_sha256"].items()]
    expected.append((("parcae_tok", "tokenizer.json"), ("parcae_tokenizer", "tokenizer.json"), dm["general_text"]["decode_tokenizer_json_sha256"]))
    expected.append((("parquet", PQ), ("anchor_source", PQ), pin[0]))
    ok &= len(pin) == 1 and len(expected) == 6
    for (a, f), (b, g), v in expected:
        mine = file_sha(os.path.join(dl, a, f))
        ex = file_sha(os.path.join(exin, b, g))
        same = mine == ex == v
        ok &= same
        print(f"  {a}/{f}: mine {mine} | Executor {b}/{g} {ex} | manifest {v} | ALL EQUAL {same}")
    for d in (dl, exin):
        w = [os.path.join(r, x) for r, _, fs in os.walk(d) for x in fs if x.endswith(WEIGHT_EXT)]
        print(f"  weight-like files under {d}: {w}")
        ok &= not w

    print("\n== c. eval_sets.jsonl (whole-file hash; split value from the line prefix, counted; binary mode)")
    ev = os.path.join(repo, dm["general_text"]["source_file"])
    evh = file_sha(ev)
    print(f"{dm['general_text']['source_file']}: sha256 {evh} | manifest {dm['general_text']['source_file_sha256']} | MATCH {evh == dm['general_text']['source_file_sha256']}")
    ok &= evh == dm["general_text"]["source_file_sha256"]
    cnt, bad = Counter(), 0
    with open(ev, "rb") as fh:
        for line in fh:
            i = line.find(KEY, 0, 80)
            if i < 0:
                bad += 1
                continue
            j = line.find(b'"', i + len(KEY), i + len(KEY) + 16)
            if j < 0:
                bad += 1
                continue
            cnt[line[i + len(KEY):j]] += 1
    counts = {k.decode("ascii"): v for k, v in sorted(cnt.items())}
    print(f"rows by split value (line prefix only): {counts} | lines without the prefix key: {bad}")
    ok &= bad == 0 and counts == {"dev": 400, "test": 800}
    return bool(ok)


run(main)
