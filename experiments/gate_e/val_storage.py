#!/usr/bin/env python3
"""
Storage test (PREREGISTRATION 9.7, review of 7a0d89e), on one non-formal
checkpoint (seed 99, K=2, OpenMythos, step 200 of val_train.py):
  1. push it as an LFS object to artifacts/gate-e-checkpoints (separate clone
     directory; the staged blob must be an LFS pointer)
  2. clone that branch into a fresh directory, git lfs pull
  3. file sha256 and parameter hash both equal the local values
  4. the research branch tracks no .pt file of Gate E and none was ever
     committed there
Writes validation/storage_test.json; exits non-zero on any failure. The LFS
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
from e_storage import (BRANCH, entry, push_files, remote_url, research_branch_has_no_checkpoints,  # noqa: E402
                       retrieve_and_verify, write_json)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scratch", required=True)
    args = ap.parse_args()
    repo = os.path.abspath(ROOT)
    src = os.path.join(args.scratch, "val_train", "k2a_openmythos", "K2_openmythos_s99_step200.pt")
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True).stdout.strip()
    pub = "gate_e/storage_test/K2_openmythos_s99_step200.pt"
    e = entry(src, pub, "openmythos", 2, 99, 200, commit, "val_train.py (non-formal seed 99, 200 steps)")
    url = remote_url(repo)
    res = {"branch": BRANCH, "entry": e}
    try:
        res["pushed_commit"] = push_files([(src, pub)], os.path.join(args.scratch, "artifacts_clone"), url,
                                          "gate_e: storage test - one non-formal checkpoint (seed 99) as LFS object")
        res["retrieval"] = retrieve_and_verify([e], url, os.path.join(args.scratch, "artifacts_fresh"))
        res["retrieval_pass"] = all(v["file_sha256"] and v["param_sha256"] for v in res["retrieval"].values())
    except (RuntimeError, subprocess.CalledProcessError) as err:
        res["error"] = str(err)[-2000:]
        res["retrieval_pass"] = False
    res["research_branch"] = research_branch_has_no_checkpoints(repo)
    res["lfs_quota"] = "not readable from this session; to be confirmed by the repository owner"
    res["pass"] = res["retrieval_pass"] and res["research_branch"]["pass"]
    write_json(os.path.join(HERE, "validation", "storage_test.json"), res)
    print({k: v for k, v in res.items() if k not in ("entry",)})
    sys.exit(0 if res["pass"] else 1)


if __name__ == "__main__":
    main()
