"""R8-0: download, at the pinned revisions, the external files needed for the round-8 freeze-hash audit, into a new
directory that must not exist yet (no file of an earlier download or of the Executor's scratchpad is reused).
Data Auditor's own script; no Executor code is imported, called or copied. Exceptions -> RESULT: FAIL (r6_guard).

Files (each repo into its own new subdirectory):
  qwen_tok/   Qwen/Qwen3-1.7B@70d244cc86ccca08cf5af4e1e306ecf908b1ad5e : tokenizer.json, tokenizer_config.json,
              vocab.json, merges.txt  (tokenizer files only; no config, no weights)
  parcae_tok/ SandyResearch/parcae-tokenizer@6247b5d0592876b73660f34c2dd16c9db9e9045c : tokenizer.json
  parquet/    dataset SandyResearch/fineweb-edu-shuffled@4d1138c0e4d51d98813997ce3560e05a32bf91de :
              data/sample-100BT/train/shard_00000.parquet
For every file: size, sha256 and git-blob sha1 of the downloaded bytes, compared with the Hub metadata of the same
path at the same revision (LFS sha256 for LFS files, git blob id otherwise). The pinned revisions are also resolved
on the Hub (repo info at the revision must report the same commit sha).
PASS iff every revision resolves to itself and every downloaded file matches the Hub metadata; afterwards no
weight-like file exists under <out_dir>.
usage: python -I r8_fetch.py <out_dir (must not exist)>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hashlib, platform, socket
from r6_guard import run

QWEN = ("Qwen/Qwen3-1.7B", "70d244cc86ccca08cf5af4e1e306ecf908b1ad5e", "model",
        ["tokenizer.json", "tokenizer_config.json", "vocab.json", "merges.txt"], "qwen_tok")
PARCAE = ("SandyResearch/parcae-tokenizer", "6247b5d0592876b73660f34c2dd16c9db9e9045c", "model",
          ["tokenizer.json"], "parcae_tok")
ANCHOR = ("SandyResearch/fineweb-edu-shuffled", "4d1138c0e4d51d98813997ce3560e05a32bf91de", "dataset",
          ["data/sample-100BT/train/shard_00000.parquet"], "parquet")
WEIGHT_EXT = (".safetensors", ".bin", ".pt", ".pth", ".gguf", ".h5", ".msgpack", ".ckpt", ".onnx")


def file_hashes(path):
    h, n = hashlib.sha256(), 0
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk); n += len(chunk)
    g = hashlib.sha1(b"blob %d\0" % n)
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            g.update(chunk)
    return n, h.hexdigest(), g.hexdigest()


def main():
    out = sys.argv[1]
    if os.path.exists(out):
        print("out_dir exists already; refusing to reuse:", out)
        return False
    os.makedirs(out)
    import huggingface_hub, transformers, tokenizers, pyarrow
    from huggingface_hub import HfApi, hf_hub_download
    print("host:", socket.gethostname(), "|", platform.platform(), "| python", sys.version.split()[0], sys.executable)
    print("huggingface_hub", huggingface_hub.__version__, "| transformers", transformers.__version__,
          "| tokenizers", tokenizers.__version__, "| pyarrow", pyarrow.__version__)
    api = HfApi()
    ok = True
    for repo, rev, rtype, files, sub in (QWEN, PARCAE, ANCHOR):
        info = api.repo_info(repo, revision=rev, repo_type=rtype)
        same = info.sha == rev
        ok &= same
        print(f"== {rtype} {repo}@{rev}: hub resolves revision to {info.sha} | same {same}")
        meta = {p.path: p for p in api.get_paths_info(repo, files, revision=rev, repo_type=rtype)}
        d = os.path.join(out, sub)
        os.makedirs(d)
        for f in files:
            p = hf_hub_download(repo, f, revision=rev, repo_type=rtype, local_dir=d)
            n, s256, blob = file_hashes(p)
            m = meta[f]
            if m.lfs is not None:
                ref, got, kind = m.lfs.sha256, s256, "lfs sha256"
            else:
                ref, got, kind = m.blob_id, blob, "git blob sha1"
            match = (ref == got) and (m.size == n)
            ok &= match
            print(f"  {f}: bytes {n} | sha256 {s256} | git-blob {blob} | hub size {m.size} {kind} {ref} | MATCH {match}")
            print(f"    local path {p}")
    weights = [os.path.join(r, x) for r, _, fs in os.walk(out) for x in fs if x.endswith(WEIGHT_EXT)]
    print("weight-like files under out_dir:", weights)
    ok &= not weights
    listing = sorted(os.path.relpath(os.path.join(r, x), out) for r, _, fs in os.walk(out) for x in fs)
    print("all files under out_dir (incl. hub metadata):", listing)
    return ok


run(main)
