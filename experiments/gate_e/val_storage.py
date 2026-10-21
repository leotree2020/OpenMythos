#!/usr/bin/env python3
"""
Storage test (PREREGISTRATION 9.7), on one non-formal checkpoint (seed 99,
K=2, OpenMythos, step 200 of val_train.py):
  1. push it as an LFS object to --url / --branch from --workdir (a separate
     clone; the staged blob must be an LFS pointer). Default: the owner's
     choice after the first plan failed, leotree2020/openmythos-artifacts
     (private, not a fork), branch main. The first run (public fork, branch
     artifacts/gate-e-checkpoints) failed; its record
     validation/storage_test.json is kept unchanged.
  2. clone that branch into a fresh directory, git lfs pull
  3. file sha256 and parameter hash both equal the local values
  4. the research branch tracks no .pt file of Gate E and none was ever
     committed there
Writes --out; exits non-zero on any failure. The LFS
quota of the repository owner's account cannot be read from this session and
is reported as unchecked.
"""

import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import e_common  # noqa: F401,E402  (first: puts the archived modules on sys.path)
from e_common import ROOT  # noqa: E402
from e_storage import (ARTIFACTS_URL, BRANCH, entry, push_files, research_branch_has_no_checkpoints,  # noqa: E402
                       retrieve_and_verify, write_json)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scratch", required=True)
    ap.add_argument("--url", default=ARTIFACTS_URL)
    ap.add_argument("--branch", default=BRANCH)
    ap.add_argument("--workdir", default="/home/user/openmythos-artifacts")
    ap.add_argument("--fresh", default=None, help="fresh retrieval directory (must not exist)")
    ap.add_argument("--out", default=os.path.join(HERE, "validation", "storage_test_artifacts_repo.json"))
    args = ap.parse_args()
    repo = os.path.abspath(ROOT)
    src = os.path.join(args.scratch, "val_train", "k2a_openmythos", "K2_openmythos_s99_step200.pt")
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True).stdout.strip()
    pub = "gate_e/storage_test/K2_openmythos_s99_step200.pt"
    e = entry(src, pub, "openmythos", 2, 99, 200, commit, "val_train.py (non-formal seed 99, 200 steps)")
    url = args.url
    fresh = args.fresh or os.path.join(args.scratch, "artifacts_fresh_" + args.branch.replace("/", "_"))
    res = {"url": url, "branch": args.branch, "entry": e}
    try:
        res["pushed_commit"] = push_files([(src, pub)], args.workdir, url,
                                          "gate_e: storage test - one non-formal checkpoint (seed 99) as LFS object",
                                          branch=args.branch)
        res["retrieval"] = retrieve_and_verify([e], url, fresh, branch=args.branch)
        res["retrieval_pass"] = all(v["file_sha256"] and v["param_sha256"] for v in res["retrieval"].values())
    except (RuntimeError, subprocess.CalledProcessError) as err:
        res["error"] = str(err)[-2000:]
        res["retrieval_pass"] = False
    res["research_branch"] = research_branch_has_no_checkpoints(repo)
    res["lfs_quota"] = "not readable from this session; to be confirmed by the repository owner"
    res["pass"] = res["retrieval_pass"] and res["research_branch"]["pass"]
    write_json(args.out, res)
    print({k: v for k, v in res.items() if k not in ("entry",)})
    sys.exit(0 if res["pass"] else 1)


if __name__ == "__main__":
    main()
