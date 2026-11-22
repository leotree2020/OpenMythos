"""R6-0: environment, tokenizer / source-file identity, absence of model weights / torch / PROTOCOL_FROZEN.
Data Auditor's own script; no Executor code is imported, called or copied. Exceptions -> RESULT: FAIL (r6_guard).

Identity of the local files:
  - sha256 and git-blob sha1 of every file in the Qwen tokenizer dir, the parcae tokenizer.json and the anchor parquet;
  - compared with the values the auditor recorded in round 5 (audit/stdout/2724144b.../01_r4_env.txt and 19_r5_sources.txt,
    which were matched there against the Hugging Face Hub metadata at the pinned revisions);
  - compared again with the Hub metadata now (get_paths_info, metadata only, nothing downloaded) when --hub is given.
usage: python -I r6_env.py <qwen_tok_dir> <parcae_tokenizer.json> <anchor_parquet> <repo_root> [--hub]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hashlib, importlib.util, platform, socket, subprocess
from common import sha
from r6_guard import run

R5_QWEN = {  # file: (bytes, sha256) as recorded by the auditor in round 5 (hub-verified there)
    "config.json": (726, "1ddb5b89ebc90dcb417a45c213d818577e65976454d29385c8f6140771d95197"),
    "generation_config.json": (239, "2325da0f15bb848e018c5ae071b7943332e9f871d6b60e2ed22ca97d4cb993d2"),
    "merges.txt": (1671853, "8831e4f1a044471340f7c0a83d7bd71306a5b867e95fd870f74d0c5308a904d5"),
    "tokenizer.json": (11422654, "aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4"),
    "tokenizer_config.json": (9732, "d5d09f07b48c3086c508b30d1c9114bd1189145b74e982a265350c923acd8101"),
    "vocab.json": (2776833, "ca10d7e9fb3ed18575dd1e277a2579c16d108e32f27439684afa0e10b1440910"),
}
R5_PARCAE = (2326980, "e0021e26057088d68047dbe6e77e2ba1c9fe9ae45bae3df9d67d48c82405ea77")
R5_PARQUET = (94511680, "6a3450ea745ee6b6830c09819c0f2c72682eba443022de595bcb50ceb3092c22")
WEIGHT_EXT = (".safetensors", ".bin", ".pt", ".pth", ".gguf", ".h5", ".msgpack", ".ckpt", ".onnx")


def blob(b):
    return hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest()


def main():
    args = [a for a in sys.argv[1:] if a != "--hub"]
    hub = "--hub" in sys.argv[1:]
    qdir, ptok, parquet, repo = args
    ok = True
    print("hostname:", socket.gethostname(), "| platform:", platform.platform(), "| cpus:", os.cpu_count())
    print("python:", sys.version.split()[0], sys.executable)
    for m in ("transformers", "tokenizers", "jinja2", "pyarrow", "huggingface_hub"):
        print(f"  {m} {getattr(__import__(m), '__version__', '?')}")
    torch_present = importlib.util.find_spec("torch") is not None
    print("torch importable:", torch_present)
    print("nvidia-smi on PATH:", any(os.path.exists(os.path.join(p, "nvidia-smi")) for p in os.environ.get("PATH", "").split(os.pathsep)))
    ok &= not torch_present
    head = subprocess.check_output(["git", "-C", repo, "rev-parse", "HEAD"], text=True).strip()
    print("git HEAD:", head)

    local = {}
    print("== Qwen tokenizer dir", qdir)
    weights = [os.path.join(r, f) for r, _, fs in os.walk(qdir) for f in fs if f.endswith(WEIGHT_EXT)]
    weights += [os.path.join(r, f) for r, _, fs in os.walk(os.path.dirname(ptok)) for f in fs if f.endswith(WEIGHT_EXT)]
    print("weight-like files under the two tokenizer dirs:", weights)
    ok &= not weights
    files = sorted(f for f in os.listdir(qdir) if os.path.isfile(os.path.join(qdir, f)))
    print("files:", files, "| same set as round 5:", files == sorted(R5_QWEN))
    ok &= files == sorted(R5_QWEN)
    for fn in files:
        b = open(os.path.join(qdir, fn), "rb").read()
        meta = os.path.join(qdir, ".cache", "huggingface", "download", fn + ".metadata")
        rev = open(meta).read().split("\n")[0] if os.path.exists(meta) else None
        same = R5_QWEN.get(fn) == (len(b), sha(b))
        ok &= same
        local[("Qwen/Qwen3-1.7B", fn)] = b
        print(f"  {fn:24s} bytes {len(b):9d} sha256 {sha(b)} | == round-5 record: {same} | hf metadata revision {rev}")
    for label, path, rec, key in (("parcae tokenizer.json", ptok, R5_PARCAE, ("SandyResearch/parcae-tokenizer", "tokenizer.json")),
                                  ("anchor parquet", parquet, R5_PARQUET,
                                   ("SandyResearch/fineweb-edu-shuffled", "data/sample-100BT/train/shard_00000.parquet"))):
        b = open(path, "rb").read()
        same = rec == (len(b), sha(b))
        ok &= same
        local[key] = b
        print(f"== {label}: bytes {len(b)} sha256 {sha(b)} | == round-5 record: {same}")

    if hub:
        from huggingface_hub import HfApi
        api = HfApi()
        plan = [("Qwen/Qwen3-1.7B", "model", "70d244cc86ccca08cf5af4e1e306ecf908b1ad5e", sorted(R5_QWEN)),
                ("SandyResearch/parcae-tokenizer", "model", "6247b5d0592876b73660f34c2dd16c9db9e9045c", ["tokenizer.json"]),
                ("SandyResearch/fineweb-edu-shuffled", "dataset", "4d1138c0e4d51d98813997ce3560e05a32bf91de",
                 ["data/sample-100BT/train/shard_00000.parquet"])]
        for repo_id, rtype, rev, fns in plan:
            info = {x.path: x for x in api.get_paths_info(repo_id, fns, revision=rev, repo_type=rtype)}
            for fn in fns:
                b, x = local[(repo_id, fn)], info.get(fn)
                if x is None:
                    print(f"  hub {repo_id}@{rev[:8]} {fn}: NOT FOUND"); ok = False; continue
                lfs = x.lfs
                hub_sha = (lfs.get("sha256") if isinstance(lfs, dict) else getattr(lfs, "sha256", None)) if lfs else None
                match = x.size == len(b) and ((hub_sha == sha(b)) if hub_sha else (x.blob_id == blob(b)))
                ok &= match
                print(f"  hub {repo_id}@{rev[:8]} {fn}: size {x.size} | {'lfs sha256 ' + hub_sha if hub_sha else 'blob ' + x.blob_id} | MATCH {match}")

    tracked = subprocess.check_output(["git", "-C", repo, "ls-files"], text=True).split("\n")
    t_frozen = [t for t in tracked if "PROTOCOL_FROZEN" in os.path.basename(t)]
    ondisk = []
    for root, dirs, fs in os.walk(repo):
        if ".git" in dirs:
            dirs.remove(".git")
        ondisk += [os.path.join(root, f) for f in fs if "PROTOCOL_FROZEN" in f]
    print("tracked files whose name contains PROTOCOL_FROZEN:", t_frozen, "| on disk:", ondisk)
    ok &= not t_frozen and not ondisk
    st = [l for l in open(os.path.join(repo, "metrix/e1-pilot/METRIX_E1_PROTOCOL.md"), encoding="utf-8").read().split("\n")
          if l.startswith("| 状态 |")][0]
    print("protocol status row:", st)
    ok &= "AWAITING_REVIEW_GATE" in st
    return bool(ok)


if __name__ == "__main__":
    run(main)
