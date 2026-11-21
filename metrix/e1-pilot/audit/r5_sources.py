"""R5-A/D: provenance of the inputs used for L6 and the anchor text.
- eval_sets.jsonl and data_lock.json: sha256, tracked in git, last commit touching them, working tree == HEAD object
- local files vs the Hugging Face Hub file metadata at the pinned revisions (metadata request only, get_paths_info;
  nothing is downloaded): blob id (git sha1) for small files, LFS sha256 for LFS files
usage: python -I r5_sources.py <repo_root> <qwen_tok_dir> <parcae_tokenizer.json> <anchor_parquet>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hashlib, subprocess
from common import sha

repo, qdir, ptok, parquet = sys.argv[1:5]
R = "research/mini_mythos/stage1/results/r1/"
for fn in ("eval_sets.jsonl", "data_lock.json"):
    p = R + fn
    b = open(os.path.join(repo, p), "rb").read()
    tracked = subprocess.run(["git", "-C", repo, "ls-files", "--error-unmatch", p], capture_output=True).returncode == 0
    last = subprocess.check_output(["git", "-C", repo, "log", "-1", "--format=%H %cI %s", "--", p]).decode().strip()
    headobj = subprocess.check_output(["git", "-C", repo, "show", f"HEAD:{p}"])
    print(f"{p}: sha256 {sha(b)} bytes {len(b)} | tracked {tracked} | working tree == HEAD object {headobj == b} | last commit {last}")


def blob(b):
    return hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest()


checks = [("Qwen/Qwen3-1.7B", "model", "70d244cc86ccca08cf5af4e1e306ecf908b1ad5e",
           [(f, os.path.join(qdir, f)) for f in ("config.json", "generation_config.json", "merges.txt", "tokenizer.json", "tokenizer_config.json", "vocab.json")]),
          ("SandyResearch/parcae-tokenizer", "model", "6247b5d0592876b73660f34c2dd16c9db9e9045c", [("tokenizer.json", ptok)]),
          ("SandyResearch/fineweb-edu-shuffled", "dataset", "4d1138c0e4d51d98813997ce3560e05a32bf91de",
           [("data/sample-100BT/train/shard_00000.parquet", parquet)])]
try:
    from huggingface_hub import HfApi
    api = HfApi()
    for repo_id, rtype, rev, files in checks:
        info = {x.path: x for x in api.get_paths_info(repo_id, [f for f, _ in files], revision=rev, repo_type=rtype)}
        for f, local in files:
            b = open(local, "rb").read()
            x = info.get(f)
            if x is None:
                print(f"{repo_id}@{rev[:8]} {f}: NOT FOUND on the hub"); continue
            lfs = getattr(x, "lfs", None)
            hub_sha = (lfs.get("sha256") if isinstance(lfs, dict) else getattr(lfs, "sha256", None)) if lfs else None
            ok = (hub_sha == sha(b)) if hub_sha else (x.blob_id == blob(b))
            print(f"{repo_id}@{rev[:8]} {f}: hub size {x.size} local {len(b)} | hub blob_id {x.blob_id} local git-blob {blob(b)} | "
                  f"hub lfs sha256 {hub_sha} local sha256 {sha(b)} | MATCH {ok and x.size == len(b)}")
except Exception as e:
    print("hub metadata check not possible:", type(e).__name__, str(e)[:300])
