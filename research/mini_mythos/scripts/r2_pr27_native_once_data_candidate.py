#!/usr/bin/env python3
"""R2 Gate Q research-only candidate remedy for upstream PR #27 data.py.

Pinned external reference (NOT modified by this module):
  kyegomez/OpenMythos PR #27 head
  2954bc275ffb8ad5c60f74f7299a9ad9e531d3e4
  experiments/data.py

Original PR27 FineWebEduStream.__iter__ called ds.shard(2, worker.id)
AND subsequently iterated the HF IterableDataset in the same PyTorch
worker, allowing HF's own automatic noncontiguous worker split to
divide sources a second time.

REMEDY:
  - NEVER explicitly ds.shard in this adapter. HF IterableDataset
    automatically assigns shards inside PyTorch DataLoader workers.
  - Pin the immutable Gate I/M/N/O/P FineWeb dataset commit for research.
  - Prohibit skip_docs>0 with >1 Worker, since a global skip applied
    inside each separate worker could have a different meaning.
  - Keep original token packing/labels and EOS behavior unchanged.
  - No remote dataset is opened until the adapter is actually iterated.
  - No model, optimizer, checkpoint or GPU code is present.

This is a CANDIDATE separate research adapter, not a modification of
the upstream PR27 experiments/data.py and not proof of remote coverage.
"""
from typing import Iterator

import torch
from torch.utils.data import DataLoader, IterableDataset, get_worker_info
from datasets import load_dataset

FROZEN_DATASET_ID = "HuggingFaceFW/fineweb-edu"
FROZEN_DATASET_CONFIG = "sample-10BT"
FROZEN_DATASET_SPLIT = "train"
FROZEN_DATASET_REVISION = "87f09149ef4734204d70ed1d046ddc9ca3f2b8f9"


class FineWebEduStreamNativeOnce(IterableDataset):
    """PR27-compatible (x, y) stream, one HF-native shard assignment."""

    def __init__(
        self, tokenizer, seq_len: int,
        dataset_name: str = FROZEN_DATASET_ID,
        dataset_config: str = FROZEN_DATASET_CONFIG,
        split: str = FROZEN_DATASET_SPLIT,
        skip_docs: int = 0,
        revision: str = FROZEN_DATASET_REVISION,
    ):
        super().__init__()
        if not isinstance(seq_len, int) or isinstance(seq_len, bool) or seq_len <= 0:
            raise ValueError("Sequence length must be positive integer")
        if not isinstance(skip_docs, int) or isinstance(skip_docs, bool) or skip_docs < 0:
            raise ValueError("skip_docs must be nonnegative integer")
        if ((dataset_name, dataset_config, split, revision) != (
            FROZEN_DATASET_ID, FROZEN_DATASET_CONFIG,
            FROZEN_DATASET_SPLIT, FROZEN_DATASET_REVISION
        )):
            raise ValueError("Research adapter only accepts the frozen FineWeb source")
        if getattr(tokenizer, "eos_token_id", None) is None:
            raise ValueError("Tokenizer must have a specified EOS token ID")
        self.tokenizer = tokenizer
        self.seq_len = seq_len
        self.dataset_name = dataset_name
        self.dataset_config = dataset_config
        self.split = split
        self.skip_docs = skip_docs
        self.revision = revision
        self.eos_id = tokenizer.eos_token_id

    def __iter__(self) -> Iterator[tuple[torch.Tensor, torch.Tensor]]:
        worker = get_worker_info()
        # HF .skip() fixes shard order/affects sharding; never pretend
        # a per-worker skip is a global source-document exclusion.
        if self.skip_docs > 0 and worker and worker.num_workers > 1:
            raise RuntimeError("skip_docs>0 with multiple workers is unsupported; use num_workers=1")

        ds = load_dataset(
            self.dataset_name,
            name=self.dataset_config,
            split=self.split,
            streaming=True,
            revision=self.revision,
        )
        if self.skip_docs > 0:
            ds = ds.skip(self.skip_docs)

        # NO manual ds.shard(...) here: HF IterableDataset.__iter__
        # already sees get_worker_info() inside the SAME worker and
        # partitions native source shards exactly once.
        buffer: list[int] = []
        need = self.seq_len + 1
        for doc in ds:
            if not isinstance(doc, dict):
                raise ValueError("HF streamed record must be a mapping")
            text = doc.get("text", "")
            if not text:
                continue
            ids = self.tokenizer.encode(text, add_special_tokens=False)
            if not isinstance(ids, list) or any(type(t) is not int for t in ids):
                raise ValueError("Tokenizer must return integer token IDs")
            ids.append(self.eos_id)
            buffer.extend(ids)
            while len(buffer) >= need:
                chunk = buffer[:need]
                buffer = buffer[need - 1:]
                yield (
                    torch.tensor(chunk[:-1], dtype=torch.long),
                    torch.tensor(chunk[1:], dtype=torch.long),
                )


def build_loader_native_once(
    tokenizer, seq_len: int, batch_size: int,
    dataset_name: str = FROZEN_DATASET_ID,
    dataset_config: str = FROZEN_DATASET_CONFIG,
    num_workers: int = 2,
    split: str = FROZEN_DATASET_SPLIT,
    skip_docs: int = 0,
    revision: str = FROZEN_DATASET_REVISION,
):
    if type(num_workers) is not int or num_workers < 0:
        raise ValueError("num_workers must be a nonnegative integer")
    if type(batch_size) is not int or batch_size <= 0:
        raise ValueError("batch_size must be a positive integer")
    if skip_docs > 0 and num_workers > 1:
        raise ValueError("skip_docs>0 must use num_workers=1")
    ds = FineWebEduStreamNativeOnce(
        tokenizer=tokenizer, seq_len=seq_len,
        dataset_name=dataset_name,
        dataset_config=dataset_config,
        split=split, skip_docs=skip_docs, revision=revision,
    )
    return DataLoader(
        ds, batch_size=batch_size, num_workers=num_workers,
        pin_memory=True, persistent_workers=(num_workers > 0),
    )
