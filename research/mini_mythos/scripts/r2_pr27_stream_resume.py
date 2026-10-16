#!/usr/bin/env python3
"""R2 Gate F: single-worker, PR27-shaped streaming cursor+RNG CPU proof.

Mirrors PR27 data.py packing: tokenize each document, append EOS, emit
(seq_len+1) windows, retain one overlapping byte/token between windows.
No HF streaming fetch, no multiprocessing/prefetch, no upstream changes,
no 118M weights, no GPU. Uses a deterministic local FineWeb-shaped fixture
and the already frozen GPT2 tokenizer identity. Tests uninterrupted vs a
checkpoint interruption/resumption with real tiny AdamW optimizer states.

This does NOT claim that the upstream num_workers=2 HF Streaming DataLoader
has a restorable cursor; that production problem remains open.
"""
import argparse
import hashlib
import json
import random
from pathlib import Path

import torch
import torch.nn.functional as F

from common import atomic_json, get_repo
from r2_pr27_guarded_checkpoint import (
    identity_metadata, read_frozen_contract, require_real_tokenizer_identity,
    safe_load_bound_checkpoint, save_bound_checkpoint,
)
from r2_pr27_tokenizer_contract import canonical_bytes, load_tokenizer


SEED = 20261016
PROTOCOL = "R2_PR27_SINGLE_WORKER_STREAM_V1"
CHUNK_LEN = 16
TOTAL_STEPS = 12
SPLIT_AFTER_STEPS = 5
FIXTURE_DOCS = 64
LOOP_CHOICES = (1, 2, 3)


def digest(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def local_documents(n=FIXTURE_DOCS):
    if n < 12:
        raise ValueError("At least twelve documents needed")
    return [{
        "id": f"gate-f-fixture-{i:04d}",
        "text": (
            f"A synthetic research passage number {i}. "
            f"The algorithm packs adjacent sentences from document {i}. "
            f"Version {i % 5} contains arithmetic {i} and words. "
        ) * 2,
    } for i in range(n)]


def split_documents(records):
    """Deterministic ID-hash split; preserve stream order, reject duplicate IDs."""
    if not isinstance(records, list) or not records:
        raise ValueError("No records")
    seen = set()
    train, heldout = [], []
    for item in records:
        if (not isinstance(item, dict) or not isinstance(item.get("id"), str)
                or not item["id"] or not isinstance(item.get("text"), str)):
            raise ValueError("Malformed record")
        if item["id"] in seen:
            raise ValueError("Duplicate document id; split integrity compromised")
        seen.add(item["id"])
        key = int(hashlib.sha256(
            ("gate-f-fixed-split:" + item["id"]).encode("utf-8")
        ).hexdigest(), 16)
        (heldout if key % 5 == 0 else train).append(item)
    if not train or not heldout:
        raise ValueError("Train and heldout must both contain documents")
    if set(d["id"] for d in train) & set(d["id"] for d in heldout):
        raise AssertionError("Train/heldout document-id overlap")
    return train, heldout


class PackedCursor:
    """Checkpointable ONE-WORKER source; no queued DataLoader items."""

    def __init__(self, records, tokenizer, *, seq_len, contract_sha, eos_id):
        if (not isinstance(seq_len, int) or seq_len < 2 or
                not isinstance(eos_id, int) or eos_id < 0 or
                not isinstance(contract_sha, str) or len(contract_sha) != 64):
            raise ValueError("Invalid stream configuration")
        ids = [r["id"] for r in records]
        if len(set(ids)) != len(ids):
            raise ValueError("Repeated document id")
        self.records = records
        self.tokenizer = tokenizer
        self.seq_len = seq_len
        self.eos_id = eos_id
        self.contract_sha = contract_sha
        self.source_sha = digest(records)
        self.next_doc = 0
        self.buffer = []
        self.emitted = 0

    def next_chunk(self):
        need = self.seq_len + 1
        while len(self.buffer) < need:
            if self.next_doc >= len(self.records):
                raise StopIteration("No more full packed windows")
            record = self.records[self.next_doc]
            self.next_doc += 1
            text = record["text"]
            if not text:
                continue
            ids = self.tokenizer.encode(text, add_special_tokens=False)
            if not all(isinstance(i, int) and i >= 0 for i in ids):
                raise ValueError("Tokenizer returned invalid token IDs")
            self.buffer.extend(ids)
            self.buffer.append(self.eos_id)
        chunk = self.buffer[:need]
        self.buffer = self.buffer[self.seq_len:]  # PR27 retains last input/first target
        self.emitted += 1
        return (torch.tensor(chunk[:-1], dtype=torch.long),
                torch.tensor(chunk[1:], dtype=torch.long))

    def state_dict(self):
        core = {
            "protocol": PROTOCOL,
            "source_sha": self.source_sha,
            "tokenizer_contract_sha256": self.contract_sha,
            "sequence_length": self.seq_len,
            "eos_id": self.eos_id,
            "next_doc": self.next_doc,
            "buffer_ids": list(self.buffer),
            "emitted_chunks": self.emitted,
            "workers": 0,
            "prefetched_batches": 0,
        }
        return dict(core, state_sha256=digest(core))

    def load_state_dict(self, state, *, strict_replay=True):
        if not isinstance(state, dict):
            raise ValueError("Stream state is not a dictionary")
        actual = dict(state)
        observed_sha = actual.pop("state_sha256", None)
        if observed_sha != digest(actual):
            raise ValueError("Stream cursor state checksum mismatch")
        checks = {
            "protocol": PROTOCOL,
            "source_sha": self.source_sha,
            "tokenizer_contract_sha256": self.contract_sha,
            "sequence_length": self.seq_len,
            "eos_id": self.eos_id,
            "workers": 0,
            "prefetched_batches": 0,
        }
        for key, expected in checks.items():
            if actual.get(key) != expected:
                raise ValueError("Stream source/tokenizer/worker metadata drift: " + key)
        index, emitted, buffer = (
            actual.get("next_doc"), actual.get("emitted_chunks"),
            actual.get("buffer_ids")
        )
        if (not isinstance(index, int) or not 0 <= index <= len(self.records)
                or not isinstance(emitted, int) or emitted < 0
                or not isinstance(buffer, list)
                or any(not isinstance(v, int) or v < 0 for v in buffer)):
            raise ValueError("Invalid stream cursor values")
        if strict_replay:
            replay = PackedCursor(
                self.records, self.tokenizer, seq_len=self.seq_len,
                contract_sha=self.contract_sha, eos_id=self.eos_id
            )
            try:
                for _ in range(emitted):
                    replay.next_chunk()
            except StopIteration as exc:
                raise ValueError("Cursor counts exceed available source") from exc
            if (replay.next_doc != index or replay.buffer != buffer):
                raise ValueError("Restored stream cursor differs from source replay")
        self.next_doc, self.emitted, self.buffer = index, emitted, list(buffer)


class MicroLM(torch.nn.Module):
    """Minimal CPU wiring only; not the upstream OpenMythos architecture."""
    def __init__(self, vocab, hidden=4):
        super().__init__()
        self.embedding = torch.nn.Embedding(vocab, hidden)
        self.head = torch.nn.Linear(hidden, vocab, bias=False)

    def forward(self, x, loops, noise):
        h = self.embedding(x)
        h = h * (noise > 0.15).to(h.dtype) / 0.85
        for _ in range(loops):
            h = torch.tanh(h)
        return self.head(h)


def new_training(vocab, seed=SEED):
    # Preserve global RNG while initializing both model copies identically.
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(seed)
        model = MicroLM(vocab)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)
    py_rng = random.Random(seed + 1)
    gen = torch.Generator(device="cpu").manual_seed(seed + 2)
    return model, optimizer, py_rng, gen


def step_training(model, optimizer, stream, py_rng, gen):
    x, y = stream.next_chunk()
    loops = py_rng.choice(LOOP_CHOICES)
    noise = torch.rand(x.numel(), model.embedding.embedding_dim, generator=gen)
    model.train()
    optimizer.zero_grad(set_to_none=True)
    logits = model(x, loops=loops, noise=noise)
    loss = F.cross_entropy(logits, y)
    if not torch.isfinite(loss):
        raise RuntimeError("Nonfinite tiny training loss")
    loss.backward()
    optimizer.step()
    return {
        "chunk_sha256": digest({"x": x.tolist(), "y": y.tolist()}),
        "loops": loops,
        "noise_mask_sha256": digest((noise > 0.15).to(torch.uint8).tolist()),
        "loss": float(loss.detach()),
    }


def train_steps(model, optimizer, stream, py_rng, gen, count):
    return [
        step_training(model, optimizer, stream, py_rng, gen)
        for _ in range(count)
    ]


def training_bundle(contract, model, optimizer, stream, py_rng, gen):
    return {
        "format": "PR27_GUARDED_CHECKPOINT_RESEARCH_V1",
        "step": stream.emitted,
        "tokens_seen": stream.emitted * stream.seq_len,
        "model": model.state_dict(),
        "opt": optimizer.state_dict(),
        "cfg": {"tokenizer": "gpt2", "scope": "Gate F synthetic CPU stream only"},
        "mcfg": {"vocab_size": model.embedding.num_embeddings,
                 "architecture": "Gate-F-MicroLM"},
        "tokenizer_metadata": identity_metadata(
            contract, model.embedding.num_embeddings
        ),
        "embedding_key": "embedding.weight",
        "stream_state": stream.state_dict(),
        "python_loop_rng_state": py_rng.getstate(),
        "torch_augmentation_rng_state": gen.get_state().clone(),
    }


def restore_bundle(bundle, model, optimizer, stream, py_rng, gen):
    if (bundle.get("step") != bundle["stream_state"]["emitted_chunks"] or
            bundle.get("tokens_seen") != bundle["step"] * stream.seq_len):
        raise ValueError("Checkpoint step/tokens do not match stream cursor")
    # Validate data provenance and exact saved buffer BEFORE restoring model/opt.
    stream.load_state_dict(bundle["stream_state"], strict_replay=True)
    python_state, tensor_state = (
        bundle.get("python_loop_rng_state"),
        bundle.get("torch_augmentation_rng_state")
    )
    if not isinstance(python_state, tuple) or not isinstance(tensor_state, torch.Tensor):
        raise ValueError("Python/Torch RNG states are missing")
    model.load_state_dict(bundle["model"], strict=True)
    optimizer.load_state_dict(bundle["opt"])
    py_rng.setstate(python_state)
    gen.set_state(tensor_state)


def exact_optimizer_state_equal(a, b):
    if type(a) is not type(b):
        return False
    if isinstance(a, torch.Tensor):
        return torch.equal(a, b)
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(
            exact_optimizer_state_equal(a[k], b[k]) for k in a
        )
    if isinstance(a, (tuple, list)):
        return len(a) == len(b) and all(
            exact_optimizer_state_equal(x, y) for x, y in zip(a, b)
        )
    return a == b


def compare_uninterrupted_with_resume(
    tokenizer, contract, *, ckpt_path, sidecar_path,
    total=TOTAL_STEPS, cutoff=SPLIT_AFTER_STEPS, records=None
):
    """Train tiny CPU model twice and prove a real checkpoint can restart."""
    if not 0 < cutoff < total:
        raise ValueError("Cutoff must be within training steps")
    rows = records if records is not None else local_documents()
    train, heldout = split_documents(rows)
    source_sha = digest(rows)
    train_sha = digest(train)
    val_sha = digest(heldout)
    if train_sha == val_sha:
        raise ValueError("Train and heldout content unexpectedly match")
    eos = int(contract["fingerprint"]["special_tokens"]["eos_token_id"])
    fingerprint = require_real_tokenizer_identity(tokenizer, contract)
    vocab = int(contract["fingerprint"]["len_tokenizer"])
    torch.set_num_threads(min(4, torch.get_num_threads()))

    def cursor():
        return PackedCursor(
            train, tokenizer, seq_len=CHUNK_LEN,
            contract_sha=contract["fingerprint_sha256"], eos_id=eos
        )

    full_model, full_opt, full_py, full_gen = new_training(vocab)
    continuous = train_steps(
        full_model, full_opt, cursor_full := cursor(),
        full_py, full_gen, total
    )

    old_model, old_opt, old_py, old_gen = new_training(vocab)
    start_stream = cursor()
    prior = train_steps(
        old_model, old_opt, start_stream, old_py, old_gen, cutoff
    )
    payload = training_bundle(
        contract, old_model, old_opt, start_stream, old_py, old_gen
    )
    save_bound_checkpoint(
        ckpt_path, sidecar_path, payload, contract, fingerprint
    )

    fresh_model, fresh_opt, fresh_py, fresh_gen = new_training(vocab)
    fresh_stream = cursor()
    restored = safe_load_bound_checkpoint(
        ckpt_path, sidecar_path, contract, fingerprint
    )
    restore_bundle(
        restored, fresh_model, fresh_opt, fresh_stream, fresh_py, fresh_gen
    )
    suffix = train_steps(
        fresh_model, fresh_opt, fresh_stream, fresh_py, fresh_gen,
        total - cutoff
    )
    resumed = prior + suffix

    loss_delta = max(
        abs(x["loss"] - y["loss"]) for x, y in zip(continuous, resumed)
    )
    trace_equal = continuous == resumed
    parameter_equal = exact_optimizer_state_equal(
        full_model.state_dict(), fresh_model.state_dict()
    )
    optimizer_equal = exact_optimizer_state_equal(
        full_opt.state_dict(), fresh_opt.state_dict()
    )
    cursor_equal = cursor_full.state_dict() == fresh_stream.state_dict()
    rng_equal = (
        full_py.getstate() == fresh_py.getstate()
        and torch.equal(full_gen.get_state(), fresh_gen.get_state())
    )
    if not (trace_equal and parameter_equal and optimizer_equal
            and cursor_equal and rng_equal):
        raise AssertionError(
            "Uninterrupted vs real-file resumed CPU training diverged"
        )
    return {
        "protocol": PROTOCOL,
        "dataset_source": "locally generated PR27-shaped synthetic documents; NOT FineWeb-Edu",
        "source_document_count": len(rows),
        "source_sha256": source_sha,
        "training_documents": len(train),
        "heldout_documents": len(heldout),
        "train_document_sha256": train_sha,
        "heldout_document_sha256": val_sha,
        "train_heldout_document_ids_disjoint": True,
        "single_worker_no_prefetch": True,
        "tokenizer_contract_sha256": contract["fingerprint_sha256"],
        "total_steps": total,
        "interrupted_after_step": cutoff,
        "total_training_target_positions": total * CHUNK_LEN,
        "chunk_length": CHUNK_LEN,
        "trace_sha256": digest(resumed),
        "traces_exactly_equal": trace_equal,
        "max_abs_loss_difference": loss_delta,
        "model_parameters_bitwise_equal": parameter_equal,
        "optimizer_state_bitwise_equal": optimizer_equal,
        "stream_cursor_exactly_equal": cursor_equal,
        "python_and_torch_rng_exactly_equal": rng_equal,
        "heldout_not_scored": True,
        "checkpoint": str(ckpt_path),
        "manifest": str(sidecar_path),
        "limitations": "A self-contained CPU synthetic proof. Not real HF streaming "
                       "resume; not num_workers=2, not exactly-once source "
                       "partitioning across shards, not production PR27 training.",
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", default=".")
    p.add_argument("--contract",
                   default="research/mini_mythos/results/r2/pr27_gpt2_tokenizer_contract.json")
    p.add_argument("--checkpoint",
                   default="research/mini_mythos/results/r2/pr27_gate_f_stream_cpu.pt")
    p.add_argument("--manifest",
                   default="research/mini_mythos/results/r2/pr27_gate_f_stream_cpu.manifest.json")
    p.add_argument("--out",
                   default="research/mini_mythos/results/r2/pr27_gate_f_stream_comparison.json")
    a = p.parse_args()
    root = get_repo(a.repo)
    results_dir = (root / "research/mini_mythos/results").resolve()
    paths = [Path(x).resolve() for x in (
        a.contract, a.checkpoint, a.manifest, a.out
    )]
    if any(not path.is_relative_to(results_dir) for path in paths):
        p.error("All file paths must remain inside research/mini_mythos/results")
    if any(path.exists() for path in paths[1:]):
        p.error("Checkpoint/manifest/result already exists; refusing overwrite")
    contract = read_frozen_contract(paths[0], strict_gate=True)
    fp = contract["fingerprint"]
    tokenizer = load_tokenizer(
        fp["identifier"], fp["pinned_revision"], offline=True
    )
    result = compare_uninterrupted_with_resume(
        tokenizer, contract, ckpt_path=paths[1], sidecar_path=paths[2]
    )
    atomic_json(paths[3], result)
    print("Source:", result["dataset_source"])
    print("Train/heldout docs:", result["training_documents"],
          result["heldout_documents"])
    print("Real GPT2 contract sha:", result["tokenizer_contract_sha256"])
    print("Trace same across restart:", result["traces_exactly_equal"])
    print("Maximum abs loss difference:", result["max_abs_loss_difference"])
    print("Model parameters bitwise identical:",
          result["model_parameters_bitwise_equal"])
    print("Optimizer state bitwise identical:",
          result["optimizer_state_bitwise_equal"])
    print("Data cursor bitwise identical:", result["stream_cursor_exactly_equal"])
    print("Python/Torch RNG state identical:",
          result["python_and_torch_rng_exactly_equal"])
    print("Original PR27 multi-worker Streaming loader modified: False")
    print("Real FineWeb-Edu consumed: False")
    print("118M GPU training performed: False")
    print("Saved:", paths[3])


if __name__ == "__main__":
    main()
