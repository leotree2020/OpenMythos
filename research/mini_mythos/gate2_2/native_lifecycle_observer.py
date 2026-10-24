"""Read-only observer. Does not decide when optimizer.step runs."""
import hashlib
import json
from pathlib import Path

import torch

from collect_native_evidence import collect_rng


def _sha(batch):
    b = batch.detach().contiguous().cpu()
    return hashlib.sha256(b.view(torch.uint8).numpy().tobytes()).hexdigest()


class LifecycleLog:
    def __init__(self):
        self.hashes = []
        self.losses = []
        self.microbatch_step = None
        self.optimizer_step = None
        self.update_count = 0
        self.before_save = None
        self.after_load = None
        self.checkpoint_path = None
        self.checkpoint_sha256 = None

    def on_step(self, input_ids, loss, state, stepped):
        self.hashes.append(_sha(input_ids))
        self.losses.append(float(loss.detach()))
        self.microbatch_step = state.get("microbatch_step")
        self.optimizer_step = state.get("optimizer_step")
        if stepped:
            self.update_count += 1

    def on_before_save(self, path):
        self.before_save = collect_rng("before_save")
        self.checkpoint_path = str(path)

    def on_after_save(self, path):
        p = Path(path)
        if p.is_file():
            self.checkpoint_sha256 = hashlib.sha256(p.read_bytes()).hexdigest()
        elif p.is_dir():
            parts = sorted(x for x in p.rglob("*") if x.is_file())
            h = hashlib.sha256()
            for x in parts:
                h.update(x.relative_to(p).as_posix().encode())
                h.update(hashlib.sha256(x.read_bytes()).digest())
            self.checkpoint_sha256 = h.hexdigest()

    def on_after_load(self):
        self.after_load = collect_rng("after_load")

    def dump(self, path):
        Path(path).write_text(json.dumps(self.__dict__, indent=2, default=str))


LOG = LifecycleLog()
