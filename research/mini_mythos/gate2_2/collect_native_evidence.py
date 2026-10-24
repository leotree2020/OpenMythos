"""
External evidence collector. Does not modify Parcae training math.

Produces CPU_PARCAE evidence from real objects.
GPU_RUNTIME is refused unless a real run directory with command/config/checkpoint
is supplied. native_entry_artifact is a hash of those files, not a hand-filled flag.
"""
import hashlib
import json
import platform
import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract_evidence import from_objects, collect_rng


def file_sha(path):
    p = Path(path)
    if not p.is_file():
        return None
    return hashlib.sha256(p.read_bytes()).hexdigest()


def collect(model, optimizer, scheduler, batch, checkpoint_path, counts, blob_dir, run_meta):
    """run_meta must include command, config_path, openmythos_commit, parcae_commit."""
    for k in ("command", "config_path", "openmythos_commit", "parcae_commit"):
        if not run_meta.get(k):
            raise ValueError(f"missing run_meta.{k}")
    cfg_sha = file_sha(run_meta["config_path"])
    ckpt_sha = file_sha(checkpoint_path)
    if cfg_sha is None or ckpt_sha is None:
        raise FileNotFoundError("config or checkpoint missing")
    artifact = hashlib.sha256(
        json.dumps({
            "command": run_meta["command"],
            "config_sha": cfg_sha,
            "ckpt_sha": ckpt_sha,
            "openmythos": run_meta["openmythos_commit"],
            "parcae": run_meta["parcae_commit"],
        }, sort_keys=True).encode()
    ).hexdigest()
    ev = from_objects(
        model, optimizer, scheduler, batch, checkpoint_path,
        source=run_meta.get("source", "CPU_PARCAE"),
        counts=counts, blob_dir=blob_dir,
        rng_stages={"before_save": collect_rng("before_save"), "after_load": collect_rng("after_load")},
    )
    ev["native_entry_artifact"] = artifact
    ev["provenance"] = {
        "command": run_meta["command"],
        "config_sha256": cfg_sha,
        "checkpoint_sha256": ckpt_sha,
        "openmythos_commit": run_meta["openmythos_commit"],
        "parcae_commit": run_meta["parcae_commit"],
        "python": platform.python_version(),
        "torch": torch.__version__,
        "cuda": torch.version.cuda,
    }
    if ev["source"] == "GPU_RUNTIME" and not run_meta.get("gpu_confirmed"):
        raise ValueError("GPU_RUNTIME requires gpu_confirmed from a real run")
    return ev
