"""R4-0: environment, tokenizer identity, absence of model weights / torch / PROTOCOL_FROZEN.
Data Auditor's own script; no Executor code is imported, called or copied.
usage: python -I r4_env.py <tokenizer_dir> <repo_root>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hashlib, importlib.util, platform, socket, subprocess
from common import sha

tokdir, repo = sys.argv[1:3]
print("hostname:", socket.gethostname(), "| platform:", platform.platform(), "| cpus:", os.cpu_count())
print("python:", sys.version.split()[0], sys.executable)
for m in ("transformers", "tokenizers", "jinja2", "pyarrow", "huggingface_hub"):
    mod = __import__(m)
    print(f"  {m} {getattr(mod, '__version__', '?')}")
print("torch importable:", importlib.util.find_spec("torch") is not None)
print("nvidia-smi on PATH:", any(os.path.exists(os.path.join(p, "nvidia-smi")) for p in os.environ.get("PATH", "").split(os.pathsep)))
print("git HEAD:", subprocess.check_output(["git", "-C", repo, "rev-parse", "HEAD"], text=True).strip())

# tokenizer files: sha256, git-blob sha1, and the revision / etag recorded by huggingface_hub at download time
print("== tokenizer dir", tokdir)
weights = []
for root, _, files in os.walk(tokdir):
    for fn in files:
        if fn.endswith((".safetensors", ".bin", ".pt", ".pth", ".gguf", ".h5", ".msgpack", ".ckpt")):
            weights.append(os.path.join(root, fn))
print("weight-like files under tokenizer dir:", weights)
for fn in sorted(f for f in os.listdir(tokdir) if os.path.isfile(os.path.join(tokdir, f))):
    b = open(os.path.join(tokdir, fn), "rb").read()
    blob = hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest()
    meta = os.path.join(tokdir, ".cache", "huggingface", "download", fn + ".metadata")
    rev = etag = None
    if os.path.exists(meta):
        rev, etag = open(meta).read().split("\n")[:2]
    print(f"  {fn:24s} bytes {len(b):9d} sha256 {sha(b)} git-blob-sha1 {blob}")
    print(f"  {'':24s} hf metadata revision {rev} etag {etag} etag==sha256 or git-blob: {etag in (sha(b), blob)}")

# PROTOCOL_FROZEN: tracked files and files on disk whose name contains it
tracked = subprocess.check_output(["git", "-C", repo, "ls-files"], text=True).split("\n")
print("tracked files whose name contains PROTOCOL_FROZEN:", [t for t in tracked if "PROTOCOL_FROZEN" in os.path.basename(t)])
ondisk = []
for root, dirs, files in os.walk(repo):
    if ".git" in dirs:
        dirs.remove(".git")
    ondisk += [os.path.join(root, f) for f in files if "PROTOCOL_FROZEN" in f]
print("files on disk whose name contains PROTOCOL_FROZEN:", ondisk)
st = [l for l in open(os.path.join(repo, "metrix/e1-pilot/METRIX_E1_PROTOCOL.md"), encoding="utf-8").read().split("\n") if l.startswith("| 状态 |")]
print("protocol status row:", st)
