"""
Evidence extractor.

- synthetic(): labeled SYNTHETIC. Not GPU acceptance evidence.
- from_objects(): reads a real model/optimizer/scheduler. source is caller-supplied
  and must not be SYNTHETIC for acceptance.
MuonAdamW step on CPU is not claimed here.
"""
import hashlib
import json
import random
import sys
from pathlib import Path

import numpy as np
import torch


def _tensor_record(t):
    v = t.detach().cpu().float().reshape(-1)
    return {
        "shape": list(t.shape),
        "dtype": str(t.dtype).replace("torch.", ""),
        "numel": int(t.numel()),
        "values": [float(x) for x in v.tolist()],
    }


def from_objects(model, optimizer, scheduler, batch, checkpoint_path, source, counts, rng_extra=None):
    if source == "SYNTHETIC":
        raise ValueError("from_objects refuses source=SYNTHETIC")
    model_state = {k: _tensor_record(v) for k, v in model.state_dict().items()}
    opt_sd = optimizer.state_dict()
    # numeric tensors in optimizer state
    state = {}
    for k, st in opt_sd.get("state", {}).items():
        state[str(k)] = {}
        for fk, fv in st.items():
            if torch.is_tensor(fv):
                state[str(k)][fk] = [float(x) for x in fv.detach().cpu().float().reshape(-1).tolist()]
            else:
                state[str(k)][fk] = fv if not isinstance(fv, (bytes,)) else str(fv)
    opt_out = {"param_groups": opt_sd.get("param_groups", []), "state": state, "optimizer_class": type(optimizer).__name__}
    sched_out = scheduler.state_dict() if scheduler is not None else {}
    rng = {
        "cpu": hashlib.sha256(torch.get_rng_state().numpy().tobytes()).hexdigest(),
        "cuda": "NOT_APPLICABLE" if not torch.cuda.is_available() else "PRESENT",
        "python": hashlib.sha256(repr(random.getstate()).encode()).hexdigest(),
        "numpy": hashlib.sha256(repr(np.random.get_state()).encode()).hexdigest(),
    }
    if rng_extra:
        rng.update(rng_extra)
    b = batch.detach().contiguous().view(torch.uint8).cpu().numpy().tobytes()
    ckpt = Path(checkpoint_path)
    ckpt_sha = hashlib.sha256(ckpt.read_bytes()).hexdigest() if ckpt.is_file() else None
    return {
        "source": source,
        "batch_hashes": [hashlib.sha256(b).hexdigest()],
        "losses": counts.get("losses", []),
        "model_state": model_state,
        "optimizer_state": opt_out,
        "scheduler": sched_out,
        "microbatch_step": counts.get("microbatch_step"),
        "optimizer_step": counts.get("optimizer_step"),
        "update_count": counts.get("update_count"),
        "rng": rng,
        "checkpoint_sha256": ckpt_sha,
        "optimizer_class": type(optimizer).__name__,
    }


def synthetic():
    return {"source": "SYNTHETIC", "note": "not GPU acceptance evidence"}


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--synthetic":
        print(json.dumps(synthetic()))
        return 0
    print(json.dumps({"status": "use from_objects() or --synthetic"}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
