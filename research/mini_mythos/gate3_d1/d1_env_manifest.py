#!/usr/bin/env python3
"""Record the execution environment in-process and check it against the frozen pins.

Status: FROZEN CANDIDATE. CPU only: this script (and the D1 code) never imports
torch, and sets nothing on a GPU. Exit 4 = BLOCKED (pin or policy mismatch).
"""
import argparse
import json
import os
import platform
import subprocess
import sys


def ver(mod):
    try:
        import importlib.metadata as md
        return md.version(mod)
    except Exception:  # noqa: BLE001
        return None


def git(*args):
    try:
        return subprocess.run(["git"] + list(args), capture_output=True, text=True, timeout=20,
                              cwd=os.path.dirname(os.path.abspath(__file__))).stdout.strip()
    except Exception:  # noqa: BLE001
        return None


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=("real", "selftest"), required=True)
    ap.add_argument("--config", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    with open(a.config, encoding="utf-8") as f:
        cfg = json.load(f)
    env = cfg["environment"]
    problems = []
    py = "%d.%d" % sys.version_info[:2]
    full = "%d.%d.%d" % sys.version_info[:3]
    if a.mode == "real":
        if full != env["python_full_version"]:
            problems.append("python %s != pinned %s" % (full, env["python_full_version"]))
    elif py not in env["python_minor_allowed"]:
        problems.append("python %s not in %s" % (py, env["python_minor_allowed"]))
    versions = {m: ver(m) for m in ("tokenizers", "pyarrow", "huggingface_hub")}
    if a.mode == "real":
        for m in ("tokenizers", "pyarrow"):
            if versions[m] != env["pins"][m]:
                problems.append("%s %s != pinned %s" % (m, versions[m], env["pins"][m]))
    for k, v in env["env_vars"].items():
        if k == "CUDA_VISIBLE_DEVICES" and os.environ.get(k, "") != "":
            problems.append("CUDA_VISIBLE_DEVICES must be empty (CPU only)")
    if "torch" in sys.modules:
        problems.append("torch imported")
    meta = {"mode": a.mode, "python": sys.version, "executable": sys.executable, "platform": platform.platform(),
            "machine": platform.machine(), "cpu_count": os.cpu_count(), "versions": versions,
            "env": {k: os.environ.get(k) for k in env["env_vars"]},
            "git_head": git("rev-parse", "HEAD"), "git_status_porcelain_v1": git("status", "--porcelain=v1"),
            "problems": problems}
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "x", encoding="utf-8") as f:
        json.dump(meta, f, sort_keys=True, indent=1)
    print("env problems:", problems or "none")
    return 4 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
