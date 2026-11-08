#!/usr/bin/env python3
"""Free disk space in the project Codespace. Default is a DRY RUN: it only lists what it
would delete and how big it is. Nothing is deleted without --apply.

  python3 codespace_cleanup.py                  # list everything, delete nothing
  python3 codespace_cleanup.py --apply caches   # delete regenerable caches only
  python3 codespace_cleanup.py --apply caches,worktrees,evidence,envs

Groups
  caches     pip / Hugging Face / npm caches and our temp files (always regenerable)
  worktrees  old experiment checkouts /workspaces/mythos-*: only if clean (no changes, no
             untracked files) and their HEAD commit is already on GitHub; removed with
             `git worktree remove` when they are worktrees
  evidence   old raw run directories under /workspaces/mythos-evidence/base_v01/ whose
             summaries are already committed (large raw logits, checkpoints, copies)
  envs       old extra virtual environments (official CORE eval, M2) - rebuildable

Never touched (hard-coded): the B1 run that holds the model weights, the Stage 0 evidence,
the frozen CPU environment, the pinned upstream, the main checkout /workspaces/OpenMythos,
the old-32 input data, and anything outside /workspaces or the home cache directories.
"""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

W = Path(os.environ.get("CLEANUP_ROOT", "/workspaces"))   # override only for testing
HOME = Path.home()
PROTECTED = [
    W / "OpenMythos",
    W / "mythos-base-v01-cpu312",
    W / "mythos-parcae-pinned",
    W / "mythos-evidence" / "stage0",
    W / "stage0-data-env",
    W / "mythos-evidence" / "base_v01" / "b1",
    W / "mythos-evidence" / "base_v01" / "boundary_repair",
]
CACHES = [HOME / ".cache" / "pip", HOME / ".cache" / "huggingface", HOME / ".npm" / "_cacache"]
# The frozen CPU env was built from /usr/bin/python3.12 (see B1 build_context.txt), so these are
# not its base interpreter. mythos-m2-cpu312 is the old D1/M2 environment.
ENVS = [W / "mythos-parcae-official-eval-cpu312", W / "mythos-m2-cpu312"]


def protected(path):
    p = Path(path).resolve()
    for keep in PROTECTED:
        k = keep.resolve() if keep.exists() else keep
        if p == k or k in p.parents or p in k.parents:   # the path, inside it, or containing it
            return True
    return False


def size(path):
    total = 0
    for root, dirs, files in os.walk(path, onerror=lambda e: None):
        for name in files:
            try:
                total += os.lstat(os.path.join(root, name)).st_size
            except OSError:
                pass
    return total


def human(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return "%.1f %s" % (n, unit)
        n /= 1024


def git(path, *args):
    r = subprocess.run(["git", "-C", str(path), *args], capture_output=True, text=True)
    return r.returncode, r.stdout.strip()


def worktree_candidates():
    out = []
    for p in sorted(W.glob("mythos-*")):
        if not p.is_dir() or protected(p) or not (p / ".git").exists():
            continue
        code, status = git(p, "status", "--porcelain", "--untracked-files=all")
        _, head = git(p, "rev-parse", "HEAD")
        git(p, "fetch", "-q", "origin")
        _, remote = git(p, "branch", "-r", "--contains", head)
        if code != 0:
            out.append((p, None, "skip: git status failed"))
        elif status:
            out.append((p, None, "skip: has local changes or untracked files"))
        elif not remote:
            out.append((p, None, "skip: HEAD %s is not on GitHub" % head[:8]))
        else:
            out.append((p, "worktree" if (p / ".git").is_file() else "clone", "clean and pushed (%s)" % head[:8]))
    return out


def evidence_candidates():
    base = W / "mythos-evidence" / "base_v01"
    return [p for p in sorted(base.iterdir()) if p.is_dir() and not protected(p)] if base.is_dir() else []


def remove(path, kind):
    if protected(path) or not (W in Path(path).resolve().parents or HOME in Path(path).resolve().parents):
        raise SystemExit("refusing to delete %s" % path)
    if kind == "worktree":
        _, common = git(path, "rev-parse", "--git-common-dir")
        main = Path(common).resolve().parent if common else None
        r = subprocess.run(["git", "-C", str(main), "worktree", "remove", str(path)], capture_output=True, text=True)
        if r.returncode != 0:
            print("   git worktree remove failed: %s" % r.stderr.strip())
            return False
        return True
    shutil.rmtree(path)
    return True


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--apply", default="", help="comma list of groups to actually delete")
    args = p.parse_args()
    apply = {g for g in args.apply.split(",") if g}
    unknown = apply - {"caches", "worktrees", "evidence", "envs"}
    if unknown:
        raise SystemExit("unknown group(s): %s" % sorted(unknown))
    print(subprocess.run(["df", "-h", str(W)], capture_output=True, text=True).stdout)
    plan = []
    plan += [("caches", c, "cache", "regenerable") for c in CACHES if c.exists()]
    plan += [("worktrees", path, kind, note) for path, kind, note in worktree_candidates()]
    plan += [("evidence", e, "dir", "old raw run data") for e in evidence_candidates()]
    plan += [("envs", e, "dir", "rebuildable environment") for e in ENVS if e.exists() and not protected(e)]
    freed = 0
    for group, path, kind, note in plan:
        n = size(path)
        action = "DELETE" if group in apply and kind is not None else "keep  "
        if kind is None:
            action = "keep  "
        print("%s [%-9s] %9s  %s  (%s)" % (action, group, human(n), path, note))
        if action == "DELETE":
            if remove(path, kind if kind != "cache" else "dir"):
                freed += n
    print("\nfreed %s" % human(freed) if apply else "\nDRY RUN: nothing deleted. Re-run with --apply <groups>.")
    print(subprocess.run(["df", "-h", str(W)], capture_output=True, text=True).stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
