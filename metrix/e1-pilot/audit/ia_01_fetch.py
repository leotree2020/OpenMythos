"""IA-1: fixed external inputs.  Downloads, at the pinned revisions, into a NEW directory (must not exist):
  qwen_tok/   Qwen/Qwen3-1.7B@70d244cc86ccca08cf5af4e1e306ecf908b1ad5e : tokenizer.json, tokenizer_config.json,
              vocab.json, merges.txt  (tokenizer files only; no config, no weights)
  parcae_tok/ SandyResearch/parcae-tokenizer@6247b5d0592876b73660f34c2dd16c9db9e9045c : tokenizer.json
  parquet/    dataset SandyResearch/fineweb-edu-shuffled@4d1138c0e4d51d98813997ce3560e05a32bf91de :
              data/sample-100BT/train/shard_00000.parquet
For every file: size and sha256 of the downloaded bytes == Hub metadata at the same revision (LFS sha256, or git blob
sha1 for non-LFS files) == freeze-commit manifest value; and == sha256 of the copy the Executor supplied in
<executor_inputs_dir> (qwen_tokenizer/, parcae_tokenizer/, anchor_source/).  eval_sets.jsonl (in the repository) is
hashed as a whole file only (no line is parsed).  No weight-like file may exist under <out_dir>.
Data Auditor's own script; no Executor code imported, called or copied.
usage: python -I ia_01_fetch.py <repo_root> <out_dir (new)> <executor_inputs_dir>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hashlib, re
from ia_common import file_sha, frozen_json, run

PQ = "data/sample-100BT/train/shard_00000.parquet"
SOURCES = [
    ("Qwen/Qwen3-1.7B", "70d244cc86ccca08cf5af4e1e306ecf908b1ad5e", "model",
     ["tokenizer.json", "tokenizer_config.json", "vocab.json", "merges.txt"], "qwen_tok", "qwen_tokenizer"),
    ("SandyResearch/parcae-tokenizer", "6247b5d0592876b73660f34c2dd16c9db9e9045c", "model", ["tokenizer.json"],
     "parcae_tok", "parcae_tokenizer"),
    ("SandyResearch/fineweb-edu-shuffled", "4d1138c0e4d51d98813997ce3560e05a32bf91de", "dataset", [PQ],
     "parquet", "anchor_source"),
]
WEIGHT_EXT = (".safetensors", ".bin", ".pt", ".pth", ".gguf", ".h5", ".msgpack", ".ckpt", ".onnx")


def git_blob_sha1(path):
    n = os.path.getsize(path)
    g = hashlib.sha1(b"blob %d\0" % n)
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            g.update(chunk)
    return n, g.hexdigest()


def main():
    repo, out, exin = sys.argv[1:4]
    if os.path.exists(out):
        print("out_dir exists already; refusing to reuse:", out)
        return False
    os.makedirs(out)
    dm = frozen_json(repo, "DATA_MANIFEST.json")
    pin = re.findall(r"sha256 ([0-9a-f]{64})", dm["anchor_text"]["source"])
    expected = {("qwen_tok", f): v for f, v in dm["model"]["tokenizer"]["files_sha256"].items()}
    expected[("parcae_tok", "tokenizer.json")] = dm["general_text"]["decode_tokenizer_json_sha256"]
    expected[("parquet", PQ)] = pin[0]
    print("freeze-commit expected sha256:", {f"{a}/{b}": v for (a, b), v in expected.items()})
    ok = len(pin) == 1 and len(expected) == 6
    ok &= dm["model"]["tokenizer"]["revision"] == SOURCES[0][1] and SOURCES[1][1] in dm["general_text"]["decode_with"] \
        and SOURCES[2][1] in dm["anchor_text"]["source"]
    from huggingface_hub import HfApi, hf_hub_download
    api = HfApi()
    for repo_id, rev, rtype, files, sub, exsub in SOURCES:
        info = api.repo_info(repo_id, revision=rev, repo_type=rtype)
        same = info.sha == rev
        ok &= same
        print(f"== {rtype} {repo_id}@{rev}: hub resolves the revision to {info.sha} | same {same}")
        meta = {p.path: p for p in api.get_paths_info(repo_id, files, revision=rev, repo_type=rtype)}
        d = os.path.join(out, sub)
        os.makedirs(d)
        for f in files:
            p = hf_hub_download(repo_id, f, revision=rev, repo_type=rtype, local_dir=d)
            s256 = file_sha(p)
            n, b1 = git_blob_sha1(p)
            m = meta[f]
            ref, got, kind = (m.lfs.sha256, s256, "lfs sha256") if m.lfs is not None else (m.blob_id, b1, "git blob sha1")
            hub_ok = ref == got and m.size == n
            man_ok = s256 == expected[(sub, f)]
            exp_path = os.path.join(exin, exsub, f)
            ex_sha = file_sha(exp_path) if os.path.exists(exp_path) else None
            ex_ok = ex_sha == s256
            ok &= hub_ok and man_ok and ex_ok
            print(f"  {f}: bytes {n} | sha256 {s256} | hub {kind} {ref} size {m.size} -> {hub_ok} | manifest {man_ok} "
                  f"| Executor copy {exp_path} sha256 {ex_sha} -> {ex_ok}")
    ev = os.path.join(repo, dm["general_text"]["source_file"])
    evh = file_sha(ev)
    print(f"eval_sets.jsonl (whole file, no line parsed): {evh} | manifest {dm['general_text']['source_file_sha256']} "
          f"| MATCH {evh == dm['general_text']['source_file_sha256']}")
    ok &= evh == dm["general_text"]["source_file_sha256"]
    weights = [os.path.join(r, x) for r, _, fs in os.walk(out) for x in fs if x.endswith(WEIGHT_EXT)]
    print("weight-like files under out_dir:", weights)
    ok &= not weights
    ex_files = sorted(os.path.relpath(os.path.join(r, x), exin) for r, _, fs in os.walk(exin) for x in fs if "/.cache/" not in os.path.join(r, x))
    print("Executor input files (without .cache):", ex_files)
    print("files under out_dir (without .cache):",
          sorted(os.path.relpath(os.path.join(r, x), out) for r, _, fs in os.walk(out) for x in fs if "/.cache/" not in os.path.join(r, x)))
    return bool(ok)


run(main)
