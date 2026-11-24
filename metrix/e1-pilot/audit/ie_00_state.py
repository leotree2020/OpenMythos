"""IE-0 (implementation stage B, second fix commit, round 4 of the auditor): the state audited in this round, and the fixed inputs.
  a. HEAD == the first fix commit fdbb9def89351aa187c1b1ae9749884bc3a80fe9 (the content of my round 3); no unstaged
     change under metrix/ (working tree == index), so the staged content is what the Executor's modules execute; the
     staged diff == the review input the Executor recorded for this round (review_fix2/review_input.diff): (1) its body
     from the first "diff --git" line, (2) the whole file == `git diff --cached --stat`, an empty line,
     `git diff --cached`; sha256 of review_input.diff == the value in review_fix2/preflight_tools_check.txt; the staged
     file list; no staged file under metrix/e1-pilot/audit/ or outside metrix/e1-pilot/; files the staged change does
     NOT touch and that my checks rely on (data.py, frozen.py, record.py, test_data.py, stops.py, mode.py,
     reports/round5/l6_check.py and the three other reference scripts run by tests/test_data_hashes.py,
     tests/conftest.py, tests/test_st12.py): working tree == HEAD blob.
  b. input files: sha256 of my own download (round 1, <my_dl>) and of the Executor's copies (<executor_inputs>) ==
     the freeze-commit DATA_MANIFEST values (Qwen tokenizer files, parcae tokenizer.json, anchor parquet); no
     weight-like file in either directory.
  c. eval_sets.jsonl: sha256 of the whole file == DATA_MANIFEST general_text.source_file_sha256; then, reading the
     file in BINARY mode, for every line only the split value located in the line prefix (b'"split": "' within the
     first 80 bytes) is counted.  No line is UTF-8-decoded or JSON-parsed here; nothing else about any line is computed.
Data Auditor's own script (adapted from my id_00_state.py); no Executor code imported, called or copied.
usage: python -I ie_00_state.py <repo_root> <scratch_dir> <my_dl_dir> <executor_inputs_dir>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import re
from collections import Counter
from ia_common import git, sha, file_sha, frozen_json, run

EXPECT_HEAD = "fdbb9def89351aa187c1b1ae9749884bc3a80fe9"
PQ = "data/sample-100BT/train/shard_00000.parquet"
WEIGHT_EXT = (".safetensors", ".bin", ".pt", ".pth", ".gguf", ".h5", ".msgpack", ".ckpt", ".onnx")
KEY = b'"split": "'
UNTOUCHED = ["metrix/e1-pilot/src/metrix_e1/data.py", "metrix/e1-pilot/src/metrix_e1/frozen.py",
             "metrix/e1-pilot/src/metrix_e1/record.py", "metrix/e1-pilot/src/metrix_e1/test_data.py",
             "metrix/e1-pilot/src/metrix_e1/stops.py", "metrix/e1-pilot/src/metrix_e1/mode.py",
             "metrix/e1-pilot/reports/round5/l6_check.py", "metrix/e1-pilot/reports/round2/anchor_check.py",
             "metrix/e1-pilot/reports/round2/gen_facts.py", "metrix/e1-pilot/reports/round7/gen_s_cands.py",
             "metrix/e1-pilot/tests/conftest.py", "metrix/e1-pilot/tests/test_st12.py"]


def main():
    repo, scratch, dl, exin = sys.argv[1:5]
    ok = True
    print("== a. state")
    head = git(repo, "rev-parse", "HEAD").stdout.decode().strip()
    print(f"HEAD {head} | == {EXPECT_HEAD}: {head == EXPECT_HEAD} | branch {git(repo, 'branch', '--show-current').stdout.decode().strip()}")
    ok &= head == EXPECT_HEAD
    parent = git(repo, "rev-parse", "HEAD^").stdout.decode().strip()
    print(f"HEAD^ {parent} (the work commit of my round 2)")
    unstaged = git(repo, "diff", "--name-only", "--", "metrix").stdout.decode().split()
    print(f"unstaged changes under metrix/ (working tree vs index): {unstaged}")
    ok &= not unstaged
    staged = git(repo, "diff", "--cached").stdout
    stat = git(repo, "diff", "--cached", "--stat").stdout
    names = git(repo, "diff", "--cached", "--name-status").stdout.decode().strip().split("\n")
    print(f"staged files ({len(names)}):")
    for n in names:
        print(f"  {n}")
    in_audit = [n for n in names if "metrix/e1-pilot/audit/" in n]
    outside = [n for n in names if not n.split("\t")[-1].startswith("metrix/e1-pilot/")]
    print(f"staged files under metrix/e1-pilot/audit/: {in_audit} | staged files outside metrix/e1-pilot/: {outside}")
    ok &= not in_audit and not outside
    rf = os.path.join(scratch, "review_fix2")
    inp = open(os.path.join(rf, "review_input.diff"), "rb").read()
    body = inp[inp.index(b"diff --git"):]
    print(f"git diff --cached sha256 {sha(staged)} | review_input.diff body sha256 {sha(body)} | identical {staged == body}")
    whole = stat + b"\n" + staged
    print(f"(git diff --cached --stat; echo; git diff --cached) sha256 {sha(whole)} | review_input.diff sha256 {sha(inp)} | identical {whole == inp}")
    ok &= staged == body and whole == inp
    pre = open(os.path.join(rf, "preflight_tools_check.txt"), encoding="utf-8").read()
    rec = re.findall(r"^([0-9a-f]{64})  <SCRATCH>/review_fix2/review_input\.diff$", pre, re.M)
    got = file_sha(os.path.join(rf, "review_input.diff"))
    print(f"review_input.diff: sha256 {got} | recorded in preflight_tools_check.txt {rec} | MATCH {rec == [got]}")
    ok &= rec == [got]
    for tag in ("data-auditor_TOOLS_LINE_IDENTICAL", "data-auditor_FRONTMATTER_IDENTICAL"):
        print(f"preflight_tools_check.txt records {tag}: {tag in pre}")
    staged_paths = {n.split("\t")[-1] for n in names}
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
