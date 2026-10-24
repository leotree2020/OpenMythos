"""Attempt the patched frozen entry. CPU host is expected to fail import."""
import json
import subprocess
import sys
from pathlib import Path

cmd = [
    "/usr/bin/python3.11", "-c", "import scripts.train",
]
env = {"PYTHONPATH": "/tmp/py311-pkgs:/tmp/parcae-n1/src"}
p = subprocess.run(cmd, cwd="/tmp/parcae-n1/src", capture_output=True, text=True, env={**dict(**{k: v for k, v in __import__('os').environ.items()}), **env})
blocked = "Device manager init failed" in (p.stderr + p.stdout)
print(json.dumps({
    "status": "BLOCKED" if blocked else "UNEXPECTED",
    "exit": p.returncode,
    "reason": "train.py raises before any step because CUDA device manager init fails",
    "native_train_py": "NOT TESTED",
    "hooks": "patch present, not executed",
}, indent=2))
sys.exit(2 if blocked else 1)
