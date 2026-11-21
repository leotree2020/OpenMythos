#!/usr/bin/env python3
"""Round 3, task 3: the "no change outside metrix/" check, with the two allowed exceptions.

Compared with the base commit of protocol section 0, a revision may change nothing outside metrix/ except:
  1. CLAUDE.md (charter v2.0): the base file must be an exact byte prefix of the new file, and the appended
     bytes must start with "\\n## 6. Metrix" and contain exactly one level-1 or level-2 heading, the section 6
     heading (charter section 6). Lower-level headings (### ...) inside section 6 are allowed; lines inside
     fenced code blocks are not headings;
  2. .claude/agents/code-reviewer.md and .claude/agents/data-auditor.md (added).
The two agent files are ignored by .gitignore (".claude/") and are tracked only because they were added with
`git add -f`; any later change to them must also be staged with `git add -f`. The check prints the ignore rule
and the tracked state so that this stays visible. `git check-ignore` reads the working-tree .gitignore, not the
one at --rev; the check prints whether the two files are identical (informational, not part of the result).

  python outside_metrix_check.py [--rev HEAD]
Exit code 0 only if every check passes. Reads git objects and the working-tree .gitignore; writes nothing.
"""
import argparse
import os
import re
import subprocess
import sys

BASE = "61d3c76705b28cc2ee334abc5bf1baaac4fc30dc"
CHARTER = "CLAUDE.md"
AGENTS = (".claude/agents/code-reviewer.md", ".claude/agents/data-auditor.md")
SECTION6_HEAD = b"\n## 6. Metrix"
HEADING_1_2 = re.compile(rb" {0,3}#{1,2}(?:[ \t]|$)")      # ATX heading of level 1 or 2
FENCE = re.compile(rb" {0,3}(```|~~~)")


def git(*args, check=True):
    r = subprocess.run(["git", *args], capture_output=True, check=False)
    if check and r.returncode != 0:
        sys.exit("git %s failed: %s" % (" ".join(args), r.stderr.decode("utf-8", "replace").strip()))
    return r


def top_headings(md):
    """Level-1 and level-2 heading lines of Markdown bytes, skipping fenced code blocks."""
    heads, fence = [], None
    for ln in md.split(b"\n"):
        m = FENCE.match(ln)
        if m:
            if fence is None:
                fence = m.group(1)
            elif m.group(1) == fence:
                fence = None
            continue
        if fence is None and HEADING_1_2.match(ln):
            heads.append(ln)
    return heads


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
        heads = top_headings(added)
        print("charter: appended %d bytes; level-1/2 headings in appended part: %s" % (
            len(added), [h.decode("utf-8") for h in heads]))
        if not added.startswith(SECTION6_HEAD):
            failures.append("charter: appended part does not start with section 6 heading")
        if len(heads) != 1 or not heads[0].startswith(b"## 6. "):
            failures.append("charter: appended part must contain exactly one level-1/2 heading, section 6")

    # 3. Agent files: tracked, and ignored by .gitignore (so changes need `git add -f`).
    tracked = set(git("ls-tree", "-r", "--name-only", rev, "--", ".claude").stdout.decode().split())
    rev_gi = git("show", "%s:.gitignore" % rev, check=False)
    wt_gi = open(".gitignore", "rb").read() if os.path.exists(".gitignore") else None
    same = rev_gi.returncode == 0 and wt_gi == rev_gi.stdout
    print("ignore rules below come from the working-tree .gitignore; identical to .gitignore at %s: %s" % (rev, same))
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
