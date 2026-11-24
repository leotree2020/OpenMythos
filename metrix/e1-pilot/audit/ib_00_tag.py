"""IB-0 (implementation stage B): the v1.1 freeze tag, read-only.
ia_00_frozen.py looks the tag up in the local clone (git rev-parse metrix-e1-pilot-frozen-v1.1^{commit}); this
session's clone has no local tags (git tag -l is empty), so that one line fails there.  Fetching the tags would write
to .git (outside metrix/e1-pilot/audit/), so the tag is read here from the remote with `git ls-remote --tags origin`
(no write) and compared with the v1.1 freeze commit named in the current PROTOCOL_FROZEN.
Also: the freeze commit exists locally as a commit and is an ancestor of HEAD.
Data Auditor's own script; no Executor code imported, called or copied.
usage: python -I ib_00_tag.py <repo_root>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import re
from ia_common import FROZEN, git, run


def main():
    repo = sys.argv[1]
    ok = True
    pf = open(os.path.join(repo, "metrix/e1-pilot/PROTOCOL_FROZEN"), encoding="utf-8").read()
    cur = re.search(r"^当前有效版本：(\S+)$", pf, re.M)
    sec = pf.split("## v1.1", 1)[1].split("\n## v1", 1)[0]
    named = re.findall(r"v1\.1 冻结提交\(完整 hash\) \| `([0-9a-f]{40})`", sec)
    print("PROTOCOL_FROZEN current version:", cur.group(1) if cur else None, "| v1.1 freeze commit named:", named,
          "| == audit constant", named == [FROZEN])
    ok &= cur is not None and cur.group(1) == "v1.1" and named == [FROZEN]
    local_tags = git(repo, "tag", "-l").stdout.decode().split()
    print("local tags in this clone:", local_tags)
    r = git(repo, "ls-remote", "--tags", "origin", check=False)
    print("git ls-remote --tags origin: exit", r.returncode)
    lines = r.stdout.decode().splitlines()
    for ln in lines:
        if "metrix-e1-pilot" in ln:
            print("  " + ln)
    peeled = {ln.split("\t")[1]: ln.split("\t")[0] for ln in lines if "\t" in ln}
    t11 = peeled.get("refs/tags/metrix-e1-pilot-frozen-v1.1^{}")
    print("remote tag metrix-e1-pilot-frozen-v1.1 (peeled) ->", t11, "| == freeze commit:", t11 == FROZEN)
    ok &= r.returncode == 0 and t11 == FROZEN
    typ = git(repo, "cat-file", "-t", FROZEN, check=False).stdout.decode().strip()
    anc = git(repo, "merge-base", "--is-ancestor", FROZEN, "HEAD", check=False).returncode == 0
    print("freeze commit object type in the local clone:", typ, "| ancestor of HEAD:", anc)
    ok &= typ == "commit" and anc
    return bool(ok)


run(main)
