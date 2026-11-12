#!/usr/bin/env python3
"""Round 3, task 3: the "no change outside metrix/" check, with the two allowed exceptions.

Compared with the base commit of protocol section 0, a revision may change nothing outside metrix/ except:
  1. CLAUDE.md (charter v2.0): the base file must be an exact byte prefix of the new file, and the appended
     bytes must be exactly one new level-2 section that starts with "\\n## 6. Metrix" (charter section 6);
  2. .claude/agents/code-reviewer.md and .claude/agents/data-auditor.md (added).
The two agent files are ignored by .gitignore (".claude/") and are tracked only because they were added with
`git add -f`; any later change to them must also be staged with `git add -f`. The check prints the ignore rule
and the tracked state so that this stays visible.

  python outside_metrix_check.py [--rev HEAD]
Exit code 0 only if every check passes. Reads git objects only; writes nothing.
"""
import argparse
import os
import subprocess
import sys

BASE = "61d3c76705b28cc2ee334abc5bf1baaac4fc30dc"
CHARTER = "CLAUDE.md"
AGENTS = (".claude/agents/code-reviewer.md", ".claude/agents/data-auditor.md")
SECTION6_HEAD = b"\n## 6. Metrix"


def git(*args, check=True):
    r = subprocess.run(["git", *args], capture_output=True, check=False)
    if check and r.returncode != 0:
        sys.exit("git %s failed: %s" % (" ".join(args), r.stderr.decode("utf-8", "replace").strip()))
    return r


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--rev", default="HEAD")
    rev = p.parse_args().rev
    root = git("rev-parse", "--show-toplevel").stdout.decode().strip()
    os.chdir(root)
    failures = []

    # 1. Which paths outside metrix/ differ from the base, and how.
    out = git("diff", "--no-renames", "--name-status", BASE, rev, "--", ".", ":(exclude)metrix").stdout.decode()
    changed = [line.split("\t", 1) for line in out.splitlines() if line]
    print("changed outside metrix/ (base %s .. %s):" % (BASE[:8], rev))
    for status, path in changed:
        print("  %s\t%s" % (status, path))
    allowed = {CHARTER: "M", AGENTS[0]: "A", AGENTS[1]: "A"}
    for status, path in changed:
        if allowed.get(path) != status:
            failures.append("not allowed: %s %s" % (status, path))

    # 2. Charter: base bytes unchanged, only section 6 appended.
    base_b = git("show", "%s:%s" % (BASE, CHARTER)).stdout
    new_r = git("show", "%s:%s" % (rev, CHARTER), check=False)
    new_b = new_r.stdout if new_r.returncode == 0 else b""
    if new_r.returncode != 0:
        failures.append("charter: %s missing at %s" % (CHARTER, rev))
    prefix_ok = new_r.returncode == 0 and new_b.startswith(base_b)
    added = new_b[len(base_b):] if prefix_ok else b""
    print("charter: base %d bytes, new %d bytes, base is exact prefix: %s" % (len(base_b), len(new_b), prefix_ok))
    if not prefix_ok:
        failures.append("charter: original content differs from base")
    elif added:
        heads = [ln for ln in added.split(b"\n") if ln.startswith(b"#")]
        print("charter: appended %d bytes; headings in appended part: %s" % (
            len(added), [h.decode("utf-8") for h in heads]))
        if not added.startswith(SECTION6_HEAD):
            failures.append("charter: appended part does not start with section 6 heading")
        if len(heads) != 1 or not heads[0].startswith(b"## 6. "):
            failures.append("charter: appended part must contain exactly one heading, section 6")

    # 3. Agent files: tracked, and ignored by .gitignore (so changes need `git add -f`).
    tracked = set(git("ls-tree", "-r", "--name-only", rev, "--", ".claude").stdout.decode().split())
    for path in AGENTS:
        ign = git("check-ignore", "-v", "--no-index", path, check=False).stdout.decode().strip()
        print("agent %s: tracked at %s: %s; ignore rule: %s" % (path, rev, path in tracked, ign or "none"))
        if path not in tracked:
            failures.append("agent file not tracked: %s" % path)
    extra = tracked - set(AGENTS)
    if extra:
        failures.append("other tracked files under .claude/: %s" % sorted(extra))

    for f in failures:
        print("FAIL:", f)
    print("RESULT:", "PASS" if not failures else "FAIL")
    sys.exit(0 if not failures else 1)


if __name__ == "__main__":
    main()
