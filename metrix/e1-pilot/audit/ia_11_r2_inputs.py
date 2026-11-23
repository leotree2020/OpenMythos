"""IA-11 (implementation stage A, audit round 2): inputs before regenerating the auditor's data for the gen4 comparison.
  1. sha256 of every file the auditor downloaded in round 1 (<dl_dir>: qwen_tok/, parcae_tok/, parquet/) == the
     freeze-commit DATA_MANIFEST value (model.tokenizer.files_sha256, general_text.decode_tokenizer_json_sha256, the
     sha256 pinned in anchor_text.source); no weight-like file under <dl_dir>.
  2. the same for the Executor's input copies in <executor_inputs_dir> (qwen_tokenizer/, parcae_tokenizer/,
     anchor_source/), which the Executor used for gen4 (informational for the provenance of gen4; checked anyway).
  3. eval_sets.jsonl: whole-file sha256 only (no line read here) == DATA_MANIFEST general_text.source_file_sha256.
  4. provenance of gen4: sha256 of the STAGED blobs (git index) of src/metrix_e1/{data,frozen,leakage,errors}.py ==
     the values the Executor printed in reports/impl_a/t2_fetch_generate.txt right before generating gen4; the working
     tree equals the index for these files.  The Executor's code is only hashed as bytes: not imported, run or copied.
  5. modification times of the gen4 files vs the working-tree source files (informational).
Data Auditor's own script; no Executor code imported, called or copied.
usage: python -I ia_11_r2_inputs.py <repo_root> <dl_dir> <executor_inputs_dir> <gen4_dir>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import re, datetime
from ia_common import sha, file_sha, frozen_json, git, run

PQ = "data/sample-100BT/train/shard_00000.parquet"
WEIGHT_EXT = (".safetensors", ".bin", ".pt", ".pth", ".gguf", ".h5", ".msgpack", ".ckpt", ".onnx")
SRC = ["data.py", "frozen.py", "leakage.py", "errors.py"]


def ts(p):
    return datetime.datetime.fromtimestamp(os.path.getmtime(p), datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f UTC")


def main():
    repo, dl, exin, gen4 = sys.argv[1:5]
    ok = True
    dm = frozen_json(repo, "DATA_MANIFEST.json")
    pin = re.findall(r"sha256 ([0-9a-f]{64})", dm["anchor_text"]["source"])
    expected = {f"qwen_tok/{f}": v for f, v in dm["model"]["tokenizer"]["files_sha256"].items()}
    expected["parcae_tok/tokenizer.json"] = dm["general_text"]["decode_tokenizer_json_sha256"]
    expected[f"parquet/{PQ}"] = pin[0]
    ok &= len(pin) == 1 and len(expected) == 6
    exmap = {"qwen_tok": "qwen_tokenizer", "parcae_tok": "parcae_tokenizer", "parquet": "anchor_source"}
    print("== 1/2. input files: auditor copy (round-1 download) | Executor copy | freeze-commit manifest")
    for rel, exp in expected.items():
        sub, rest = rel.split("/", 1)
        a = file_sha(os.path.join(dl, rel))
        ep = os.path.join(exin, exmap[sub], rest)
        e = file_sha(ep) if os.path.exists(ep) else None
        same = a == e == exp
        ok &= same
        print(f"  {rel}: auditor {a} | Executor {e} | manifest {exp} | ALL EQUAL {same}")
    files = sorted(os.path.relpath(os.path.join(r, x), dl) for r, _, fs in os.walk(dl) for x in fs if "/.cache" not in r)
    weights = [x for x in files if x.endswith(WEIGHT_EXT)]
    print("files under the auditor's dl dir (without .cache):", files, "| weight-like:", weights)
    ok &= not weights and sorted(files) == sorted(expected)
    ev = os.path.join(repo, dm["general_text"]["source_file"])
    evh = file_sha(ev)
    print(f"== 3. eval_sets.jsonl (whole file, no line read): {evh} | manifest {dm['general_text']['source_file_sha256']} "
          f"| MATCH {evh == dm['general_text']['source_file_sha256']}")
    ok &= evh == dm["general_text"]["source_file_sha256"]

    print("== 4. provenance of gen4: staged source blobs vs the hashes printed before the gen4 run")
    rep = open(os.path.join(repo, "metrix/e1-pilot/reports/impl_a/t2_fetch_generate.txt"), encoding="utf-8").read()
    k = rep.index("--out " + gen4.rstrip("/"))
    printed = dict((m.group(2), m.group(1)) for m in re.finditer(r"^([0-9a-f]{64})  src/metrix_e1/(\w+\.py)$", rep[:k], re.M))
    for f in SRC:
        path = f"metrix/e1-pilot/src/metrix_e1/{f}"
        staged = sha(git(repo, "show", f":{path}").stdout)
        wt = file_sha(os.path.join(repo, path))
        same = staged == wt == printed.get(f)
        ok &= same
        print(f"  {f}: staged blob {staged} | working tree {wt} | printed before the gen4 run {printed.get(f)} | ALL EQUAL {same}")
    print("== 5. modification times (informational)")
    for f in SRC:
        print(f"  src/metrix_e1/{f}: {ts(os.path.join(repo, 'metrix/e1-pilot/src/metrix_e1', f))}")
    for f in sorted(os.listdir(gen4)):
        print(f"  gen4/{f}: {ts(os.path.join(gen4, f))}")
    return bool(ok)


run(main)
