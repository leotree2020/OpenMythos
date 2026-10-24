"""
Evidence extractor.

Tensors go to a sidecar .pt. JSON holds index, metadata, SHA-256 only.
source must be one of:
  SYNTHETIC     self-test only; rejected for GPU acceptance
  CPU_PARCAE    real Parcae objects on CPU; not GPU numerical evidence
  GPU_RUNTIME   produced by an actual GPU training run
"""
import hashlib
import json
import random
import sys
from pathlib import Path

import numpy as np
import torch


def _sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _tensor_meta(name, t, blob_dir: Path):
    cpu = t.detach().cpu().contiguous()
    raw = cpu.numpy().tobytes() if cpu.dtype != torch.bfloat16 else cpu.view(torch.uint8).numpy().tobytes()
    sha = _sha_bytes(raw)
    bin_path = blob_dir / f"{sha}.bin"
    if not bin_path.exists():
        bin_path.write_bytes(raw)
    return {
        "name": name,
        "shape": list(cpu.shape),
        "dtype": str(cpu.dtype).replace("torch.", ""),
        "numel": int(cpu.numel()),
        "sha256": sha,
        "blob": bin_path.name,
    }


def collect_rng(stage: str):
    out = {
        "stage": stage,
        "cpu": _sha_bytes(torch.get_rng_state().numpy().tobytes()),
        "python": _sha_bytes(repr(random.getstate()).encode()),
        "numpy": _sha_bytes(repr(np.random.get_state()).encode()),
    }
    if torch.cuda.is_available():
        try:
            out["cuda"] = _sha_bytes(torch.cuda.get_rng_state().cpu().numpy().tobytes())
            out["cuda_status"] = "COLLECTED"
        except Exception as e:
            out["cuda"] = None
            out["cuda_status"] = f"BLOCKED {type(e).__name__}: {e}"
    else:
        out["cuda"] = None
        out["cuda_status"] = "NOT TESTED"
    return out


def from_objects(model, optimizer, scheduler, batch, checkpoint_path, source, counts, blob_dir, rng_stages=None):
    if source == "SYNTHETIC":
        raise ValueError("from_objects refuses SYNTHETIC")
    blob_dir = Path(blob_dir)
    blob_dir.mkdir(parents=True, exist_ok=True)
    model_index = [_tensor_meta(k, v, blob_dir) for k, v in model.state_dict().items()]
    opt_sd = optimizer.state_dict()
    opt_index = []
    for k, st in opt_sd.get("state", {}).items():
        for fk, fv in st.items():
            if torch.is_tensor(fv):
                opt_index.append(_tensor_meta(f"opt.{k}.{fk}", fv, blob_dir))
            else:
                opt_index.append({"name": f"opt.{k}.{fk}", "discrete": fv if not isinstance(fv, bytes) else str(fv)})
    ckpt = Path(checkpoint_path)
    ckpt_sha = _sha_bytes(ckpt.read_bytes()) if ckpt.is_file() else None
    b = batch.detach().contiguous().cpu()
    batch_sha = _sha_bytes(b.view(torch.uint8).numpy().tobytes()) if b.numel() else None
    return {
        "source": source,
        "optimizer_class": type(optimizer).__name__,
        "model_index": model_index,
        "optimizer_index": opt_index,
        "optimizer_param_groups": opt_sd.get("param_groups", []),
        "scheduler": scheduler.state_dict() if scheduler is not None else {},
        "batch_sha256": batch_sha,
        "batch_hashes": counts.get("hashes"),
        "losses": counts.get("losses"),
        "microbatch_step": counts.get("microbatch_step"),
        "optimizer_step": counts.get("optimizer_step"),
        "update_count": counts.get("update_count"),
        "checkpoint_sha256": ckpt_sha,
        "rng_stages": rng_stages or {"at_extract": collect_rng("at_extract")},
        "evidence_note": "hashes/losses are real only if the caller measured them; this function does not invent them",
    }


def read_checkpoint(path, blob_dir):
    """Read a torch checkpoint. Does not invent training metrics."""
    p = Path(path)
    if not p.is_file():
        return {"status": "MISSING", "path": str(p)}
    obj = torch.load(p, map_location="cpu", weights_only=False)
    blob_dir = Path(blob_dir)
    blob_dir.mkdir(parents=True, exist_ok=True)
    index = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if torch.is_tensor(v):
                index.append(_tensor_meta(k, v, blob_dir))
            elif isinstance(v, dict):
                for kk, vv in v.items():
                    if torch.is_tensor(vv):
                        index.append(_tensor_meta(f"{k}.{kk}", vv, blob_dir))
    return {
        "source": "CHECKPOINT_FILE",
        "path": str(p),
        "sha256": _sha_bytes(p.read_bytes()),
        "top_keys": list(obj.keys()) if isinstance(obj, dict) else [],
        "index": index,
        "muonadamw": "NOT TESTED" if "optimizer" not in (obj if isinstance(obj, dict) else {}) else "PRESENT_UNVERIFIED",
    }


def main():
    print(json.dumps({"status": "library", "cuda_rng": "NOT TESTED on this host" if not torch.cuda.is_available() else "available"}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
