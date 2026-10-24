"""External Native Evidence adapter. Does not modify Parcae math."""
import hashlib
import json
from pathlib import Path

import torch

from collect_native_evidence import collect, collect_rng


def batch_sha(batch):
    b = batch.detach().contiguous().cpu()
    return hashlib.sha256(b.view(torch.uint8).numpy().tobytes()).hexdigest()


class StepLog:
    """Tracks counters the same way train.py does: step counter vs real step()."""

    def __init__(self):
        self.microbatch_step = 0
        self.optimizer_step = 0
        self.update_count = 0
        self.hashes = []
        self.losses = []

    def observe(self, batch, loss):
        self.microbatch_step += 1
        self.hashes.append(batch_sha(batch))
        self.losses.append(float(loss.detach()))

    def maybe_step(self, optimizer):
        """Mirror first optimizer_step==0 skip, then count a real step()."""
        self.optimizer_step += 1
        if self.optimizer_step == 1:
            return False
        optimizer.step()
        self.update_count += 1
        return True

    def counts(self):
        return {
            "hashes": list(self.hashes),
            "losses": list(self.losses),
            "microbatch_step": self.microbatch_step,
            "optimizer_step": self.optimizer_step,
            "update_count": self.update_count,
        }


def capture_before_save():
    """Call at the train.py point just before fabric.save."""
    return collect_rng("before_save")


def capture_after_load():
    """Call after resume applies rng_state_* and before the next forward."""
    return collect_rng("after_load")


def write_evidence(model, optimizer, scheduler, batch, checkpoint_path, log, blob_dir, run_meta, rng_stages):
    ev = collect(model, optimizer, scheduler, batch, checkpoint_path, log.counts(), blob_dir, run_meta)
    ev["rng_stages"] = rng_stages
    if ev.get("source") == "GPU_RUNTIME" and not run_meta.get("gpu_confirmed"):
        raise ValueError("refusing GPU_RUNTIME without a real run")
    return ev
