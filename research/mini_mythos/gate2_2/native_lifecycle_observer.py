"""Read-only lifecycle observer. Does not decide optimizer.step()."""
import hashlib
import json
import os
from pathlib import Path

import torch

from collect_native_evidence import collect_rng


def enabled():
    return os.environ.get("MINI_MYTHOS_EVIDENCE") == "1"


def _sha(batch):
    b = batch.detach().contiguous().cpu()
    return hashlib.sha256(b.view(torch.uint8).numpy().tobytes()).hexdigest()


def hash_checkpoint(path):
    p = Path(path)
    if p.is_file():
        return hashlib.sha256(p.read_bytes()).hexdigest(), [p.name]
    if p.is_dir():
        files = sorted(x for x in p.rglob("*") if x.is_file())
        h = hashlib.sha256()
        names = []
        for x in files:
            rel = x.relative_to(p).as_posix()
            names.append(rel)
            h.update(rel.encode())
            h.update(hashlib.sha256(x.read_bytes()).digest())
        return h.hexdigest(), names
    return None, []


class LifecycleLog:
    def __init__(self):
        self.events = []
        self.update_count = 0
        self.kind = "OBSERVER"

    def on_microbatch(self, input_ids, loss, microbatch_step):
        self.events.append({
            "type": "microbatch",
            "microbatch_step": microbatch_step,
            "batch_sha256": _sha(input_ids),
            "loss": float(loss.detach()),
        })

    def on_optimizer_boundary(self, optimizer_step, stepped):
        if stepped:
            self.update_count += 1
        self.events.append({
            "type": "optimizer_boundary",
            "optimizer_step": optimizer_step,
            "stepped": bool(stepped),
            "update_count": self.update_count,
        })

    def restore_update_count(self, value):
        if value is None:
            return
        self.update_count = int(value)

    def on_before_save(self, path, step):
        self.events.append({
            "type": "before_save",
            "path": str(path),
            "step": step,
            "rng": collect_rng("before_save"),
            "rng_verified": False,
        })

    def on_after_save(self, path, step):
        digest, files = hash_checkpoint(path)
        self.events.append({
            "type": "after_save",
            "path": str(path),
            "step": step,
            "checkpoint_sha256": digest,
            "files": files,
            "exists": Path(path).exists(),
        })

    def on_after_load(self, step):
        self.events.append({
            "type": "after_load",
            "step": step,
            "rng": collect_rng("after_load"),
            "rng_verified": False,
        })

    def export(self, path, run_meta):
        micros = [e for e in self.events if e["type"] == "microbatch"]
        obj = {
            "schema_version": "2.2-c",
            "source": "OBSERVER_FIXTURE",
            "kind": self.kind,
            "batch_hashes": [e["batch_sha256"] for e in micros],
            "losses": [e["loss"] for e in micros],
            "microbatch_step": micros[-1]["microbatch_step"] if micros else None,
            "optimizer_step": next((e["optimizer_step"] for e in reversed(self.events) if e["type"] == "optimizer_boundary"), None),
            "update_count": self.update_count,
            "events": self.events,
            "model_index": "MISSING",
            "optimizer_index": "MISSING",
            "optimizer_param_groups": "MISSING",
            "scheduler": "MISSING",
            "checkpoint_sha256": next((e.get("checkpoint_sha256") for e in reversed(self.events) if e["type"] == "after_save"), None),
            "rng_stages": {
                "before_save": next((e.get("rng") for e in reversed(self.events) if e["type"] == "before_save"), None),
                "after_load": next((e.get("rng") for e in reversed(self.events) if e["type"] == "after_load"), None),
            },
            "optimizer_class": "NOT TESTED",
            "native_entry_artifact": None,
            "provenance": run_meta,
            "gpu_runtime": "NOT TESTED",
        }
        Path(path).write_text(json.dumps(obj, indent=2, default=str))
        return obj


LOG = LifecycleLog()
