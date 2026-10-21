#!/usr/bin/env python3
"""
Stage-1 pre-execution check (STAGE 1 GO, item 1). Read-only on every E1
file; writes only stage1/precheck.json, stage1/environment.json and the
fresh LFS retrieval stage1/lfs_e1/ (checkpoints are git-ignored).

    1  repository: HEAD, remote, approved baseline 974e932, working tree
    2  E1 archive: since the archive commit 4b33c86 only AUDIT_LOG.md changed
       under experiments/gate_e outside e2c/, only by the approved commit
       b27ea20, and only by inserted lines (0 deleted or modified lines; the
       addendum sits after line 235, not at the end of the file); the
       E1 integrity checks of verify_formal_run.py (frozen code files,
       local checkpoints with both hashes, 280 results against the ledger
       and the launcher's validation, 10 judgments, events reproduced,
       budget, no checkpoint on the research branch) called as functions,
       so validation/formal_integrity.json is not rewritten; the set files
       against sets/manifest.json
    3  environment record
    4  LFS: every E1 checkpoint that R2 and R3 need (10 runs x 17 steps)
       retrieved from leotree2020/openmythos-artifacts into a fresh
       directory, file sha256 and parameter hash checked against the
       manifest; the directory is kept as the reference for R2 / R3
Exit 0 only if everything passes; 5 otherwise (F1).
--reuse-lfs PATH: take part 4 from an earlier precheck record (the fresh
retrieval directory exists then and must not be re-cloned); parts 1-3 are
re-run. Used once, after run 1 applied a stricter part-2 criterion
("old file is a prefix of the new one") than the approved addendum meets;
run 1 is kept as stage1/precheck_run1.json.
"""

import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
GE = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(GE, "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, GE)

from s1_budget import STAGE1, Ledger  # noqa: E402

APPROVED_BASELINE = "974e9322233d3e84fda67b8866cd453122d13b3f"
E1_ARCHIVE = "4b33c86"
R23_STEPS = (0, 25, 50, 75, 100, 150, 200, 300, 400, 500, 750, 1000, 1500, 2000, 3000, 6000, 12000)
LFS_DIR = os.path.join(STAGE1, "lfs_e1")


def sh(args, cwd=ROOT):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True)


def repo_check():
    head = sh(["git", "rev-parse", "HEAD"]).stdout.strip()
    sh(["git", "fetch", "-q", "origin", "claude/openmythos-research"])
    remote = sh(["git", "rev-parse", "origin/claude/openmythos-research"]).stdout.strip()
    anc = sh(["git", "merge-base", "--is-ancestor", APPROVED_BASELINE, "HEAD"]).returncode == 0
    status = sh(["git", "status", "--porcelain"]).stdout.splitlines()
    tracked_dirty = [s for s in status if not s.startswith("??")]
    untracked = [s[3:] for s in status if s.startswith("??")]
    ok_untracked = all(u.startswith("experiments/gate_e/e2c/") for u in untracked)
    return {"head": head, "remote": remote, "head_equals_remote": head == remote,
            "approved_baseline": APPROVED_BASELINE, "baseline_is_ancestor_or_head": anc,
            "head_equals_baseline": head == APPROVED_BASELINE, "tracked_changes": tracked_dirty,
            "untracked_outside_e2c": [u for u in untracked if not u.startswith("experiments/gate_e/e2c/")],
            "pass": head == remote and anc and not tracked_dirty and ok_untracked}


def archive_check():
    changed = sh(["git", "diff", "--name-only", E1_ARCHIVE, "HEAD", "--", "experiments/gate_e"]).stdout.split()
    outside = [f for f in changed if not f.startswith("experiments/gate_e/e2c/")]
    num = sh(["git", "diff", "--numstat", E1_ARCHIVE, "HEAD", "--", "experiments/gate_e/AUDIT_LOG.md"]).stdout.split()
    commits = sh(["git", "log", "--format=%H", f"{E1_ARCHIVE}..HEAD", "--", "experiments/gate_e/AUDIT_LOG.md"]).stdout.split()
    unstaged = sh(["git", "diff", "--name-only", "HEAD", "--", "experiments/gate_e/AUDIT_LOG.md"]).stdout.split()
    append_only = (not num or num[1] == "0") and all(c.startswith("b27ea20") for c in commits) and not unstaged
    # E1 integrity checks as functions (no file of E1 is written)
    import verify_formal_run as v
    m = v.load("checkpoints_manifest.json")
    scratch = tempfile.mkdtemp(prefix="e2c_s1_precheck_")
    out = {"freeze": v.check_freeze(), "checkpoints": v.check_checkpoints(m), "results": v.check_results(m),
           "judgments": v.check_judgments(), "events": v.check_events(scratch), "budget": v.check_budget(),
           "research_branch": v.check_branch()}
    shutil.rmtree(scratch, ignore_errors=True)
    out["judgments"].pop("judgments", None)  # per-run rows are in validation/formal_integrity.json already
    man = json.load(open(os.path.join(GE, "sets", "manifest.json")))
    sets = {}
    for name, e in man.items():
        p = os.path.join(GE, "sets", f"{name}.jsonl")
        sets[name] = os.path.exists(p) and hashlib.sha256(open(p, "rb").read()).hexdigest() == e["sha256"]
    files = {f: os.path.exists(os.path.join(GE, f)) for f in
             ("E1_REPORT.md", "PREREGISTRATION.md", "AUDIT_LOG.md", "checkpoints_manifest.json", "results_ledger.json",
              "judgments_ledger.json", "budget_ledger.json", "events.json", "run_freeze.json", "workload_freeze_v2.json")}
    ok = (outside == ["experiments/gate_e/AUDIT_LOG.md"] or not outside) and append_only and all(sets.values()) \
        and all(files.values()) and all(x.get("pass", True) for x in out.values())
    return {"changed_since_archive_outside_e2c": outside, "audit_log_insert_only_by_b27ea20": append_only,
            "audit_log_numstat": num[:2], "audit_log_commits": commits,
            "e1_integrity": out, "sets_match_manifest": sets, "files_present": files, "pass": ok}


def environment():
    import numpy
    import torch
    env = {"python": sys.version, "platform": platform.platform(), "machine": platform.machine(),
           "torch": torch.__version__, "numpy": numpy.__version__, "cuda_available": torch.cuda.is_available(),
           "torch_cuda_build": torch.version.cuda, "cpu_count": os.cpu_count(),
           "torch_default_threads": torch.get_num_threads(), "threads_used_per_job": 1,
           "deterministic_algorithms_enabled": torch.are_deterministic_algorithms_enabled(),
           "mkldnn_enabled": torch.backends.mkldnn.enabled, "PYTHONHASHSEED_for_jobs": "0",
           "git": sh(["git", "--version"]).stdout.strip(), "git_lfs": sh(["git", "lfs", "version"]).stdout.strip(),
           "rng": {"init": "torch.manual_seed(seed); build(arm, 2)", "train_stream": "random.Random(60000 + seed)",
                   "aux_heads": "torch.Generator().manual_seed(90000 + seed)", "digit_code": "random.Random(80000 + seed)"}}
    cpu = sh(["lscpu"]).stdout
    env["cpu_model"] = next((ln.split(":", 1)[1].strip() for ln in cpu.splitlines() if ln.startswith("Model name")), None)
    mem = open("/proc/meminfo").read().split("\n")[0]
    env["memory"] = mem
    freeze = sh([sys.executable, "-m", "pip", "freeze"]).stdout
    env["pip_freeze_sha256"] = hashlib.sha256(freeze.encode()).hexdigest()
    env["pip_freeze"] = freeze.splitlines()
    return env


def lfs_check():
    from e_storage import ARTIFACTS_URL, retrieve_and_verify
    m = json.load(open(os.path.join(GE, "checkpoints_manifest.json")))["states"]
    want = [f"K2_{a}_s{s}_step{t}" for a in ("openmythos", "transformer") for s in range(1, 6) for t in R23_STEPS]
    missing = [w for w in want if not m.get(w, {}).get("published")]
    if missing:
        return {"pass": False, "not_published": missing}
    if os.path.exists(LFS_DIR):
        return {"pass": False, "reason": f"{LFS_DIR} exists; the retrieval must use a fresh directory"}
    ver = retrieve_and_verify([m[w] for w in want], ARTIFACTS_URL, LFS_DIR)
    bad = [k for k, x in ver.items() if not (x["file_sha256"] and x["param_sha256"])]
    return {"url": ARTIFACTS_URL, "dir": os.path.relpath(LFS_DIR, ROOT), "requested": len(want), "verified": len(ver) - len(bad),
            "failures": bad, "pass": not bad and len(ver) == len(want)}


def main():
    led = Ledger()
    with led.job("precheck") as job:
        out = {"repository": repo_check()}
        out["e1_archive"] = archive_check()
        env = environment()
        out["environment"] = {k: env[k] for k in env if k != "pip_freeze"}
        if "--reuse-lfs" in sys.argv:
            prev = json.load(open(sys.argv[sys.argv.index("--reuse-lfs") + 1]))
            out["lfs"] = dict(prev["lfs"], reused_from=os.path.basename(sys.argv[sys.argv.index("--reuse-lfs") + 1]))
        else:
            out["lfs"] = lfs_check()
    out["pass"] = all(v.get("pass") for k, v in out.items() if isinstance(v, dict) and "pass" in v)
    with open(os.path.join(STAGE1, "environment.json"), "w") as f:
        json.dump(env, f, indent=1)
    with open(os.path.join(STAGE1, "precheck.json"), "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(json.dumps({k: (v.get("pass") if isinstance(v, dict) else v) for k, v in out.items()}, indent=1))
    print(f"stage-1 ledger: {led.total():.0f} s")
    sys.exit(0 if out["pass"] else 5)


if __name__ == "__main__":
    main()
