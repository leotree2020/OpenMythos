"""IC-0 (implementation stage B, round 2): the state audited in this round, and the fixed inputs.
  a. HEAD; no unstaged change under metrix/ (working tree == index), so the staged content is what the Executor's
     modules execute; the staged diff (git diff --cached) == the body of the review input the Executor recorded for this
     round (review_work/review_input_round2.diff, from its first "diff --git" line); the sha256 of both review diffs
     == the values in review_work/preflight_tools_check_round2.txt.
  b. input files: sha256 of my own download (round 1, <my_dl>) and of the Executor's copies (<executor_inputs>) ==
     the freeze-commit DATA_MANIFEST values (Qwen tokenizer files, parcae tokenizer.json, anchor parquet); no
     weight-like file in either directory.
  c. eval_sets.jsonl: sha256 of the whole file == DATA_MANIFEST general_text.source_file_sha256; then, reading the
     file in BINARY mode, for every line only the split value located in the line prefix (b'"split": "' within the
     first 80 bytes) is counted.  No line is UTF-8-decoded or JSON-parsed here; nothing else about any line is computed.
Data Auditor's own script; no Executor code imported, called or copied.
usage: python -I ic_00_state.py <repo_root> <scratch_dir> <my_dl_dir> <executor_inputs_dir>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import re
from collections import Counter
from ia_common import git, sha, file_sha, frozen_json, run

EXPECT_HEAD = "0bc0eecf1f684773248c198afb94e7026dcfb16d"
PQ = "data/sample-100BT/train/shard_00000.parquet"
WEIGHT_EXT = (".safetensors", ".bin", ".pt", ".pth", ".gguf", ".h5", ".msgpack", ".ckpt", ".onnx")
KEY = b'"split": "'


def main():
    repo, scratch, dl, exin = sys.argv[1:5]
    ok = True
    print("== a. state")
    head = git(repo, "rev-parse", "HEAD").stdout.decode().strip()
    print(f"HEAD {head} | == {EXPECT_HEAD}: {head == EXPECT_HEAD} | branch {git(repo, 'branch', '--show-current').stdout.decode().strip()}")
    ok &= head == EXPECT_HEAD
    unstaged = git(repo, "diff", "--name-only", "--", "metrix").stdout.decode().split()
    print(f"unstaged changes under metrix/ (working tree vs index): {unstaged}")
    ok &= not unstaged
    staged = git(repo, "diff", "--cached").stdout
    names = git(repo, "diff", "--cached", "--name-only").stdout.decode().split()
    print(f"staged files: {len(names)} | staged files under metrix/e1-pilot/audit/: {[n for n in names if n.startswith('metrix/e1-pilot/audit/')]}")
    rw = os.path.join(scratch, "review_work")
    inp = open(os.path.join(rw, "review_input_round2.diff"), "rb").read()
    body = inp[inp.index(b"diff --git"):]
    print(f"git diff --cached sha256 {sha(staged)} | review_input_round2.diff body sha256 {sha(body)} | identical {staged == body}")
    ok &= staged == body
    pre = open(os.path.join(rw, "preflight_tools_check_round2.txt"), encoding="utf-8").read()
    rec = dict((n, h) for h, n in re.findall(r"^([0-9a-f]{64})  <SCRATCH>/review_work/(\S+)$", pre, re.M))
    for n in ("review_input_round2.diff", "review_fixes_round2.diff"):
        got = file_sha(os.path.join(rw, n))
        print(f"{n}: sha256 {got} | recorded in preflight_tools_check_round2.txt {rec.get(n)} | MATCH {got == rec.get(n)}")
        ok &= got == rec.get(n)

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
