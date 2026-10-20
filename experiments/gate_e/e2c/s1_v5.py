#!/usr/bin/env python3
"""
V5: non-formal Git LFS storage test of E2-c (E2C_PREREG_DRAFT 6, 8.3, 13), with
two non-formal checkpoints of gate 3 (seed 99: C1 OpenMythos and C2
Transformer, step 300):

    1  push them as LFS objects to leotree2020/openmythos-artifacts, branch
       main, under gate_e/e2c_stage1_storage_test/ (not the formal path
       gate_e/e2c/), from a separate clone directory; the staged blobs must
       be LFS pointers (e_storage.push_files)
    2  clone into a fresh directory, git lfs pull, check file sha256 and
       parameter hash (e_storage.retrieve_and_verify)
    3  the research branch tracks no .pt file and none was ever committed
    4  record sizes and transfer times; project the stage-3 volume from the
       planned runs (13 archived checkpoints each) and the measured size
The account's LFS storage and bandwidth quota cannot be read from this
session: reported as "owner confirmation required" (8.3: confirmed by the
owner before stage 3).
"""

import json
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
GE = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(GE, "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, GE)

import e_common  # noqa: E402,F401
from e_storage import ARTIFACTS_URL, entry, push_files, research_branch_has_no_checkpoints, retrieve_and_verify  # noqa: E402
from s1_budget import STAGE1, Ledger  # noqa: E402

OUT = os.path.join(STAGE1, "v5")
WORKDIR = "/home/user/openmythos-artifacts-e2c-stage1"
PREFIX = "gate_e/e2c_stage1_storage_test"
FILES = (("C1", "openmythos"), ("C2", "transformer"))


def main():
    os.makedirs(OUT, exist_ok=True)
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    ents = []
    for cond, arm in FILES:
        src = os.path.join(STAGE1, "gate3", "ckpt", f"{cond}_{arm}_s99_step300.pt")
        e = entry(src, f"{PREFIX}/{cond}_{arm}_s99_step300.pt", arm, 2, 99, 300, commit,
                  f"train_e2c.py --cond {cond} (non-formal seed 99, 300 updates, stage-1 gate 3)")
        e["local"] = src
        ents.append(e)
    res = {"url": ARTIFACTS_URL, "branch": "main", "published_prefix": PREFIX, "formal_prefix_untouched": "gate_e/e2c/",
           "entries": ents}
    fresh = os.path.join(OUT, "fresh")
    led = Ledger()
    with led.job("v5"):
        try:
            t = time.time()
            res["pushed_commit"] = push_files([(e["local"], e["published"]) for e in ents], WORKDIR, ARTIFACTS_URL,
                                              "gate_e/e2c: stage-1 storage test (V5) - two non-formal checkpoints, seed 99")
            res["push_seconds"] = time.time() - t
            t = time.time()
            res["retrieval"] = retrieve_and_verify(ents, ARTIFACTS_URL, fresh)
            res["retrieve_seconds"] = time.time() - t
            res["retrieval_pass"] = all(v["file_sha256"] and v["param_sha256"] for v in res["retrieval"].values())
        except (RuntimeError, subprocess.CalledProcessError) as err:
            res["error"] = str(err)[-2000:]
            res["retrieval_pass"] = False
    shutil.rmtree(fresh, ignore_errors=True)
    res["research_branch"] = research_branch_has_no_checkpoints(ROOT)
    size = sum(e["bytes"] for e in ents) / len(ents)
    n_runs = 72 + 30 + 20
    res["projection"] = {"mean_checkpoint_bytes": size, "planned_runs": n_runs, "archived_per_run": 13,
                         "stage3_bytes": size * 13 * n_runs, "stage3_GB": size * 13 * n_runs / 1e9,
                         "with_E1_GB": size * 13 * n_runs / 1e9 + 0.64, "quota_documented_GB": 10,
                         "retrieval_check_download_GB": size * 13 * n_runs / 1e9,
                         "final_20pct_plus_12000_download_GB_approx": size * (13 * n_runs * 0.2 + n_runs) / 1e9}
    if res.get("push_seconds"):
        res["measured_MB_per_s"] = {"push": sum(e["bytes"] for e in ents) / 1e6 / res["push_seconds"],
                                    "retrieve": sum(e["bytes"] for e in ents) / 1e6 / res["retrieve_seconds"]}
    res["quota"] = "not readable from this session; storage and bandwidth to be confirmed by the repository owner before stage 3 (8.3)"
    res["owner_confirmation"] = "pending"
    res["pass"] = res["retrieval_pass"] and res["research_branch"]["pass"]
    res["stage1_ledger_seconds"] = led.total()
    json.dump(res, open(os.path.join(OUT, "v5.json"), "w"), indent=1)
    print(json.dumps({k: res.get(k) for k in ("pushed_commit", "retrieval", "retrieval_pass", "projection", "measured_MB_per_s", "pass")},
                     indent=1))
    sys.exit(0 if res["pass"] else 5)


if __name__ == "__main__":
    main()
