"""R8-1: sha256 of the file bytes of the protocol and the three JSON in the freeze commit, and identity of the working
tree with that commit. Data Auditor's own script; no Executor code is imported, called or copied.
Exceptions -> RESULT: FAIL (r6_guard).

For each of METRIX_E1_PROTOCOL.md, DATA_MANIFEST.json, SPLIT_MANIFEST.json, SEARCH_SPACE.json (metrix/e1-pilot/):
  a. bytes of `git show <commit>:<path>` and of `git cat-file blob <commit>:<path>` (must be identical), size, sha256,
     git blob id (must equal `git rev-parse <commit>:<path>`);
  b. bytes of the working-tree file: sha256, equal to (a);
  c. bytes of HEAD:<path>, equal to (a); `git diff --quiet <commit> -- <path>` exit code;
  d. gitattributes of the path (text / eol conversion would make the working tree differ from the blob).
Also: the commit object (full hash, parents, subject), HEAD, and that each JSON parses (status field printed).
Prints one line per file "AUDIT_VALUE file_sha256:<name> <sha256>" for the final comparison script.
PASS iff (a) = (b) = (c) for all four files and the commit's parent is the expected one.
usage: python -I r8_files.py <repo_root> <commit> <expected_parent_prefix>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json, subprocess
from common import sha
from r6_guard import run

FILES = ["METRIX_E1_PROTOCOL.md", "DATA_MANIFEST.json", "SPLIT_MANIFEST.json", "SEARCH_SPACE.json"]
D = "metrix/e1-pilot/"


def git(repo, *a, check=True):
    r = subprocess.run(["git", "-C", repo, *a], capture_output=True)
    if check and r.returncode != 0:
        raise RuntimeError("git %s failed: %r" % (a, r.stderr))
    return r


def main():
    repo, commit, parent_prefix = sys.argv[1:4]
    ok = True
    full = git(repo, "rev-parse", commit + "^{commit}").stdout.decode().strip()
    head = git(repo, "rev-parse", "HEAD").stdout.decode().strip()
    meta = git(repo, "log", "-1", "--format=%H%n%P%n%aI%n%s", full).stdout.decode().splitlines()
    print("commit", full, "| parents", meta[1], "| author date", meta[2])
    print("subject:", meta[3])
    print("HEAD", head, "| HEAD == commit", head == full)
    par_ok = meta[1].split() and meta[1].split()[0].startswith(parent_prefix) and len(meta[1].split()) == 1
    print("single parent starting with", parent_prefix, ":", bool(par_ok))
    ok &= bool(par_ok)
    for name in FILES:
        path = D + name
        b_show = git(repo, "show", f"{full}:{path}").stdout
        b_cat = git(repo, "cat-file", "blob", f"{full}:{path}").stdout
        blob_id = git(repo, "rev-parse", f"{full}:{path}").stdout.decode().strip()
        b_head = git(repo, "cat-file", "blob", f"HEAD:{path}").stdout
        b_wt = open(os.path.join(repo, path), "rb").read()
        diffq = git(repo, "diff", "--quiet", full, "--", path, check=False).returncode
        attrs = git(repo, "check-attr", "-a", "--", path).stdout.decode().strip() or "(no attributes)"
        import hashlib
        my_blob = hashlib.sha1(b"blob %d\0" % len(b_cat) + b_cat).hexdigest()
        h = sha(b_cat)
        same = b_show == b_cat and b_wt == b_cat and b_head == b_cat and my_blob == blob_id and diffq == 0
        ok &= same
        print(f"== {path}")
        print(f"   commit blob: bytes {len(b_cat)} | sha256 {h} | git blob id {blob_id} (recomputed {my_blob})")
        print(f"   git show bytes == cat-file bytes: {b_show == b_cat} | sha256(git show) {sha(b_show)}")
        print(f"   working tree: bytes {len(b_wt)} | sha256 {sha(b_wt)} | == commit blob: {b_wt == b_cat}")
        print(f"   HEAD blob == commit blob: {b_head == b_cat} | git diff --quiet {full[:8]} exit {diffq}")
        print(f"   gitattributes: {attrs}")
        if name.endswith(".json"):
            j = json.loads(b_cat)
            print(f"   parses as JSON: True | status {j.get('status')!r} | frozen {j.get('frozen')!r}")
        else:
            line = next(l for l in b_cat.decode("utf-8").splitlines() if l.startswith("| 状态"))
            print(f"   status line: {line}")
        print(f"AUDIT_VALUE file_sha256:{name} {h}")
    pf = os.path.join(repo, D, "PROTOCOL_FROZEN")
    print("metrix/e1-pilot/PROTOCOL_FROZEN exists in the working tree:", os.path.exists(pf),
          "| in commit:", git(repo, "cat-file", "-e", f"{full}:{D}PROTOCOL_FROZEN", check=False).returncode == 0)
    return ok


run(main)
