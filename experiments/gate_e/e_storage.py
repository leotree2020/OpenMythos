"""
Checkpoint storage (PREREGISTRATION 9.7). The research branch keeps only the
hash manifest; the checkpoint files go through Git LFS to a separate
repository, handled in its own clone directory so the research checkout is
never touched. A file counts as archived only after it was pushed, retrieved
again into a fresh directory and both hashes (file sha256, parameter hash)
match.
  first plan    branch artifacts/gate-e-checkpoints of leotree2020/OpenMythos:
                refused by GitHub (no new LFS objects on a public fork;
                validation/storage_test.json)
  owner's choice (after that failure): the private, non-fork repository
                leotree2020/openmythos-artifacts, branch main
"""

import hashlib
import json
import os
import shutil
import subprocess

import torch

from e_common import param_hash
from models import build

BRANCH = "main"
ARTIFACTS_URL = "https://github.com/leotree2020/openmythos-artifacts"
FIRST_PLAN_BRANCH = "artifacts/gate-e-checkpoints"  # on the public fork; refused
LFS_HEADER = b"version https://git-lfs.github.com/spec/v1"


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ckpt_param_hash(path, arm, K):
    ck = torch.load(path, map_location="cpu", weights_only=False)
    m = build(arm, K)
    m.load_state_dict(ck["model"])
    return param_hash(m)


def entry(path, published, arm, K, seed, step, code_commit, train_args):
    return {"published": published, "sha256": sha256_file(path), "bytes": os.path.getsize(path),
            "param_sha256": ckpt_param_hash(path, arm, K), "arm": arm, "K": K, "seed": seed, "step": step,
            "code_commit": code_commit, "train_args": train_args}


def git(args, cwd, check=True):
    p = subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True)
    if check and p.returncode:
        raise RuntimeError(f"git {' '.join(args)} failed ({p.returncode}): {p.stderr[-1500:]}")
    return p


def remote_url(repo):
    return git(["remote", "get-url", "origin"], repo).stdout.strip()


def push_files(files, workdir, url, message, retries=4, branch=BRANCH):
    """files: list of (local path, published path inside the branch). Pushes
    them as LFS objects to `branch` from a separate clone directory. Returns
    the pushed commit."""
    BRANCH = branch  # noqa: N806
    if not os.path.isdir(os.path.join(workdir, ".git")):
        os.makedirs(workdir, exist_ok=True)
        git(["init", "-q"], workdir)
        git(["remote", "add", "origin", url], workdir)
    exists = git(["ls-remote", "--exit-code", "--heads", "origin", BRANCH], workdir, check=False).returncode == 0
    if exists:
        git(["fetch", "-q", "origin", BRANCH], workdir)
        git(["checkout", "-q", "-B", BRANCH, f"origin/{BRANCH}"], workdir)
    elif git(["rev-parse", "--verify", "-q", "HEAD"], workdir, check=False).returncode:
        git(["checkout", "-q", "--orphan", BRANCH], workdir)
    git(["lfs", "install", "--local"], workdir)
    git(["lfs", "track", "*.pt"], workdir)
    for src, pub in files:
        dst = os.path.join(workdir, pub)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(src, dst)
    git(["add", ".gitattributes"] + [pub for _, pub in files], workdir)
    for _, pub in files:  # staged blob must be an LFS pointer, never the binary
        blob = git(["cat-file", "-p", f":{pub}"], workdir).stdout.encode()
        if not blob.startswith(LFS_HEADER):
            raise RuntimeError(f"{pub} is not staged as an LFS pointer")
    git(["commit", "-q", "-m", message], workdir)
    import time

    for i in range(retries + 1):
        p = git(["push", "-u", "origin", BRANCH], workdir, check=False)
        if p.returncode == 0:
            break
        if i == retries:
            raise RuntimeError(f"push failed: {p.stderr[-1500:]}")
        time.sleep(2 ** (i + 1))
    return git(["rev-parse", "HEAD"], workdir).stdout.strip()


def retrieve_and_verify(entries, url, fresh_dir, branch=BRANCH):
    """Clone `branch` into a new empty directory, fetch the LFS objects and
    check file sha256 and parameter hash of every entry. Returns
    {published: ok}."""
    BRANCH = branch  # noqa: N806
    if os.path.exists(fresh_dir):
        raise RuntimeError(f"{fresh_dir} exists; retrieval must use a fresh directory")
    subprocess.run(["git", "clone", "-q", "--single-branch", "--branch", BRANCH, url, fresh_dir],
                   check=True, capture_output=True, env=dict(os.environ, GIT_LFS_SKIP_SMUDGE="1"))
    git(["lfs", "install", "--local"], fresh_dir)
    git(["lfs", "pull", "--include", ",".join(e["published"] for e in entries)], fresh_dir)
    out = {}
    for e in entries:
        path = os.path.join(fresh_dir, e["published"])
        ok_file = os.path.exists(path) and sha256_file(path) == e["sha256"]
        ok_param = ok_file and ckpt_param_hash(path, e["arm"], e["K"]) == e["param_sha256"]
        out[e["published"]] = {"file_sha256": ok_file, "param_sha256": ok_param}
    return out


def research_branch_has_no_checkpoints(repo):
    """No .pt file of Gate E tracked or ever committed on the research branch."""
    tracked = git(["ls-files", "experiments/gate_e"], repo).stdout.split()
    hist = git(["log", "--format=%H", "--", "experiments/gate_e/*.pt", "experiments/gate_e/**/*.pt"], repo).stdout.split()
    return {"tracked_pt": [f for f in tracked if f.endswith(".pt")], "commits_touching_pt": hist,
            "pass": not [f for f in tracked if f.endswith(".pt")] and not hist}


def write_json(path, obj):
    with open(path, "w") as f:
        json.dump(obj, f, indent=1)
