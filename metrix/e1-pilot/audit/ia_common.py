"""Implementation stage A audit helpers (Data Auditor's own code, written for this audit).
No Executor code is imported, called or copied (nothing from metrix/e1-pilot/src/ or reports/).

run(main): main() returns True / False.  True -> "RESULT: PASS" exit 0; False -> "RESULT: FAIL" exit 1;
any exception (incl. SystemExit / KeyboardInterrupt inside main) -> traceback, "RESULT: FAIL (exception)" exit 2;
any other return value -> "RESULT: FAIL" exit 3.  Before the RESULT line every script prints which heavy modules
were imported (torch, transformers modeling modules) to show that no model was built or loaded."""
import hashlib
import json
import os
import platform
import random
import socket
import subprocess
import sys
import traceback

FROZEN = "87a244db28a901f9e89282b50df76778ab5c2887"
RELS = ["capital", "currency", "founder", "river"]
STRATA = ["natural", "random"]
DOMAINS = ["books", "c4", "fineweb", "wikitext"]


def canon(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def jsonl_bytes(rows):
    return b"\n".join(canon(r) for r in rows) + b"\n"


def sha(b):
    return hashlib.sha256(b).hexdigest()


def file_sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def rng_rule(seed, purpose):
    return random.Random(int.from_bytes(hashlib.sha256(f"{seed}:{purpose}".encode("utf-8")).digest()[:8], "big"))


def git(repo, *args, check=True):
    r = subprocess.run(["git", "-C", repo, *args], capture_output=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"git {args} failed: {r.stderr!r}")
    return r


def blob(repo, rev, path):
    return git(repo, "cat-file", "blob", f"{rev}:{path}").stdout


def frozen_json(repo, name):
    return json.loads(blob(repo, FROZEN, f"metrix/e1-pilot/{name}"))


def frozen_protocol(repo):
    return blob(repo, FROZEN, "metrix/e1-pilot/METRIX_E1_PROTOCOL.md").decode("utf-8")


def read_jsonl(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh.read().split("\n") if line != ""]


def load_qwen(d):
    from transformers import AutoTokenizer
    return AutoTokenizer.from_pretrained(d, local_files_only=True)


def enc(tok, s):
    return tok.encode(s, add_special_tokens=False)


def env_banner():
    import importlib.metadata as md
    vers = {}
    for p in ("transformers", "tokenizers", "pyarrow", "huggingface_hub", "torch"):
        try:
            vers[p] = md.version(p)
        except md.PackageNotFoundError:
            vers[p] = "not installed"
    print(f"env: host {socket.gethostname()} | {platform.platform()} | python {sys.version.split()[0]} "
          f"({sys.executable}) | installed {vers} | nvidia device nodes: {sorted(x for x in os.listdir('/dev') if x.startswith('nvidia'))}")


def modules_report():
    heavy = sorted(m for m in sys.modules if m == "torch" or ".modeling_" in m or m.endswith(".modeling_utils"))
    print(f"modules: torch imported={'torch' in sys.modules} | transformers modeling modules imported={heavy[:8]}"
          f"{' ...' if len(heavy) > 8 else ''} | this script never calls a model class or from_pretrained on a model")


def run(main):
    try:
        env_banner()
        ok = main()
        modules_report()
    except BaseException:                      # noqa: B902 - every failure path ends in RESULT: FAIL
        sys.stdout.flush()
        traceback.print_exc(file=sys.stdout)
        print("RESULT: FAIL (exception)")
        sys.stdout.flush()
        sys.exit(2)
    if ok is True:
        print("RESULT: PASS")
        sys.stdout.flush()
        sys.exit(0)
    if ok is False:
        print("RESULT: FAIL")
        sys.stdout.flush()
        sys.exit(1)
    print("RESULT: FAIL (main returned %r, not a bool)" % (ok,))
    sys.stdout.flush()
    sys.exit(3)
