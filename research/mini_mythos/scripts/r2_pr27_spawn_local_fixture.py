"""Gate Q+ local-only, spawn-safe fixture for testing PR27 native-once.

This module is imported by real PyTorch spawn workers. All classes and
functions needed by worker_init_fn / IterableDataset are at module scope
and therefore pickle-importable. Every source row is synthetic and
constructed in the child subprocess. No Hugging Face Hub or Parquet I/O.
This fixture is NEVER used by a production data loader.
"""
import os

from torch.utils.data import IterableDataset, get_worker_info

import r2_pr27_native_once_data_candidate as candidate

TEXTS = tuple(f"ID:{i}" for i in range(14))


class ToyTokenizer:
    eos_token_id = 1

    def encode(self, text, add_special_tokens=False):
        if add_special_tokens:
            raise AssertionError("Unexpected add_special_tokens")
        return [500 + int(text.split(":")[1])]


def load_local_hf_dataset(dataset_name, *, name, split, streaming, revision):
    """The only data factory spawn-worker tests are allowed to use."""
    if (dataset_name, name, split, streaming, revision) != (
        candidate.FROZEN_DATASET_ID,
        candidate.FROZEN_DATASET_CONFIG,
        candidate.FROZEN_DATASET_SPLIT,
        True,
        candidate.FROZEN_DATASET_REVISION,
    ):
        raise AssertionError("Unexpected source identity in offline spawn fixture")
    from datasets import Dataset

    source = Dataset.from_dict({"text": list(TEXTS)}).to_iterable_dataset(
        num_shards=len(TEXTS)
    )
    if source.num_shards != len(TEXTS):
        raise AssertionError("Local fake HF shard count mismatch")
    return source


def install_local_source_in_spawn_worker(worker_id):
    """Install an IN-PROCESS fake only within the freshly spawned child."""
    info = get_worker_info()
    if info is None or info.id != worker_id or info.num_workers != 2:
        raise AssertionError("Expected real two-worker process identity")
    candidate.load_dataset = load_local_hf_dataset


class WorkerPathProbe(IterableDataset):
    """Record synthetic identity and real OS worker PID after loader packing."""

    def __init__(self, source_stream):
        super().__init__()
        self.stream = source_stream

    def __iter__(self):
        info = get_worker_info()
        if info is None or info.num_workers != 2 or info.id not in (0, 1):
            raise AssertionError("Expected real two-worker DataLoader context")
        for x, y in self.stream:
            token = int(x[0].item())
            if token != ToyTokenizer.eos_token_id:
                yield {
                    "source_token": token,
                    "worker_id": info.id,
                    "worker_pid": os.getpid(),
                    "target": int(y[0].item()),
                }
