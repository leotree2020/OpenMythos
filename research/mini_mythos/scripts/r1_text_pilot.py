#!/usr/bin/env python3
"""R1: smallest real-text OpenMythos language-model training pilot.

Train the unchanged upstream OpenMythos model on explicit train/validation
UTF-8 files using a deliberately simple byte-level tokenizer. The byte
tokenizer is only for an engineering pilot, NOT the target model tokenizer.
Checkpoints are tensor/primitive-only and load with weights_only=True.
"""
import argparse
from dataclasses import asdict
import hashlib
import math
import os
from pathlib import Path
import time

import torch
import torch.nn.functional as F

from common import atomic_json, commit_id, get_repo, load_upstream, tiny_config


VOCAB_SIZE = 257
EOS = 256
TOKENIZER_ID = "utf8_bytes_0_255_plus_eos_256_v1"


def text_tokens(path, max_bytes, seq_len):
    """Deterministically take file prefix, use EOS at blank-line boundaries."""
    if max_bytes < seq_len + 1:
        raise ValueError("max_bytes must exceed the training sequence length")
    raw = Path(path).read_bytes()[:max_bytes]
    if not raw:
        raise ValueError("Empty corpus file")
    pieces = [part for part in raw.split(b"\n\n") if part.strip()]
    ids = []
    for part in pieces:
        ids.extend(part)
        ids.append(EOS)
    if len(ids) < seq_len + 1:
        raise ValueError(f"Corpus too short for seq_len={seq_len}")
    return torch.tensor(ids, dtype=torch.long), {
        "source_path": str(Path(path).resolve()),
        "file_sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest(),
        "selected_bytes_sha256": hashlib.sha256(raw).hexdigest(),
        "selected_bytes": len(raw),
        "selected_tokens_including_eos": len(ids),
        "document_pieces": len(pieces),
    }


def ensure_different_splits(training_meta, validation_meta):
    if (training_meta["source_path"] == validation_meta["source_path"]
            or training_meta["file_sha256"] == validation_meta["file_sha256"]
            or training_meta["selected_bytes_sha256"]
               == validation_meta["selected_bytes_sha256"]):
        raise ValueError("Training and validation corpora must be different")


def draw_batch(tokens, *, seq_len, batch_size, generator, device):
    if len(tokens) <= seq_len:
        raise ValueError("Too few tokens")
    offsets = torch.randint(
        low=0, high=len(tokens) - seq_len, size=(batch_size,), generator=generator
    ).tolist()
    x = torch.stack([tokens[p:p + seq_len] for p in offsets]).to(device)
    y = torch.stack([tokens[p + 1:p + seq_len + 1] for p in offsets]).to(device)
    return x, y


def validation_offsets(token_count, seq_len, n_windows):
    """Select nonoverlapping windows evenly across *validation* only."""
    if n_windows < 1 or token_count < seq_len + 1:
        raise ValueError("Insufficient heldout tokens or invalid windows")
    starts = list(range(0, token_count - seq_len, seq_len))
    count = min(n_windows, len(starts))
    if count == 1:
        return [starts[0]]
    return [starts[round(i * (len(starts) - 1) / (count - 1))]
            for i in range(count)]


@torch.no_grad()
def evaluate(model, tokens, *, seq_len, n_loops, n_windows, device):
    model.eval()
    total_nll = 0.
    count = 0
    for offset in validation_offsets(len(tokens), seq_len, n_windows):
        x = tokens[offset:offset + seq_len][None, :].to(device)
        y = tokens[offset + 1:offset + seq_len + 1][None, :].to(device)
        logits = model(x, n_loops=n_loops)
        value = F.cross_entropy(
            logits.reshape(-1, VOCAB_SIZE), y.reshape(-1), reduction="sum"
        )
        total_nll += float(value.detach())
        count += y.numel()
    nll = total_nll / count
    if not math.isfinite(nll):
        raise RuntimeError("Nonfinite validation NLL")
    return {"nll": nll, "perplexity": math.exp(min(nll, 60.)),
            "tokens": count, "windows": count // seq_len}


@torch.no_grad()
def greedy_sample(model, prompt, *, n_loops, max_new_tokens, max_seq_len, device):
    if max_new_tokens < 0:
        raise ValueError("max_new_tokens must be nonnegative")
    model.eval()
    original = prompt.encode("utf-8")
    if not original:
        raise ValueError("Prompt cannot be empty")
    ids = list(original)
    created = []
    for _ in range(max_new_tokens):
        context = ids[-max_seq_len:]
        logits = model(torch.tensor([context], dtype=torch.long, device=device),
                       n_loops=n_loops)
        next_token = int(logits[0, -1].argmax())
        if next_token == EOS:
            break
        ids.append(next_token)
        created.append(next_token)
    return {"prompt": prompt, "continuation": bytes(created).decode("utf-8", errors="replace"),
            "token_count": len(created), "decoding": "argmax; full-context forward; no KV cache"}


def atomic_checkpoint(path, bundle):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    torch.save(bundle, tmp)
    os.replace(tmp, path)


def checkpoint_bundle(model, optimizer, random_offsets, *, cfg, hyperparameters,
                      provenance, step):
    return {
        "format_version": 1, "step": step, "cfg": asdict(cfg),
        "hyperparameters": hyperparameters, "provenance": provenance,
        "model": model.state_dict(), "optimizer": optimizer.state_dict(),
        "offset_rng_state": random_offsets.get_state(),
        "torch_rng_state": torch.get_rng_state(),
    }


def resume_checkpoint(path, model, optimizer, random_offsets, *, cfg,
                      hyperparameters, provenance):
    checkpoint = torch.load(path, map_location="cpu", weights_only=True)
    if checkpoint.get("format_version") != 1:
        raise ValueError("Unsupported checkpoint format")
    if checkpoint["cfg"] != asdict(cfg):
        raise ValueError("Checkpoint model configuration mismatch")
    if checkpoint["hyperparameters"] != hyperparameters:
        raise ValueError("Checkpoint training hyperparameters mismatch")
    if checkpoint["provenance"] != provenance:
        raise ValueError("Checkpoint dataset fingerprint mismatch")
    model.load_state_dict(checkpoint["model"])
    optimizer.load_state_dict(checkpoint["optimizer"])
    random_offsets.set_state(checkpoint["offset_rng_state"])
    torch.set_rng_state(checkpoint["torch_rng_state"])
    return int(checkpoint["step"])


def make_config(module, *, attention, seq_len):
    cfg = tiny_config(module, attention)
    cfg.vocab_size = VOCAB_SIZE
    cfg.max_seq_len = seq_len
    return cfg


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", default=".")
    p.add_argument("--train-text", required=True)
    p.add_argument("--validation-text", required=True)
    p.add_argument("--attention", choices=("gqa", "mla"), default="gqa")
    p.add_argument("--depth", type=int, default=2)
    p.add_argument("--seq-len", type=int, default=64)
    p.add_argument("--batch-size", type=int, default=4)
    p.add_argument("--steps", type=int, default=60)
    p.add_argument("--lr", type=float, default=.001)
    p.add_argument("--seed", type=int, default=20261016)
    p.add_argument("--eval-windows", type=int, default=16)
    p.add_argument("--max-train-bytes", type=int, default=250000)
    p.add_argument("--max-validation-bytes", type=int, default=50000)
    p.add_argument("--save-every", type=int, default=30)
    p.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    p.add_argument("--prompt", default="The ")
    p.add_argument("--generate-tokens", type=int, default=24)
    p.add_argument("--resume", action="store_true")
    p.add_argument("--out-dir", default="research/mini_mythos/results/r1/pilot_gqa")
    args = p.parse_args()

    if (args.depth < 1 or args.depth > 8 or args.seq_len < 4 or
            args.seq_len > 512 or args.batch_size < 1 or args.steps < 1 or
            not math.isfinite(args.lr) or args.lr <= 0 or args.eval_windows < 1
            or args.save_every < 1 or args.seed < 0 or args.generate_tokens < 0):
        p.error("Invalid training parameters")
    if args.device == "cuda" and not torch.cuda.is_available():
        p.error("CUDA requested but unavailable")
    root = get_repo(args.repo)
    out = Path(args.out_dir).resolve()
    if not out.is_relative_to(root / "research/mini_mythos/results"):
        p.error("Output must be under research/mini_mythos/results")
    out.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(min(4, torch.get_num_threads()))
    train_ids, train_meta = text_tokens(args.train_text, args.max_train_bytes, args.seq_len)
    validation_ids, validation_meta = text_tokens(
        args.validation_text, args.max_validation_bytes, args.seq_len)
    ensure_different_splits(train_meta, validation_meta)

    provenance = {
        "tokenizer": TOKENIZER_ID,
        "train": train_meta,
        "validation": validation_meta,
    }
    hyperparameters = {
        "attention": args.attention, "depth": args.depth, "seq_len": args.seq_len,
        "batch_size": args.batch_size, "lr": args.lr, "seed": args.seed,
    }
    torch.manual_seed(args.seed)
    module = load_upstream(root)
    cfg = make_config(module, attention=args.attention, seq_len=args.seq_len)
    model = module.OpenMythos(cfg).to(args.device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr)
    generator = torch.Generator(device="cpu").manual_seed(args.seed + 17)

    ckpt_path = out / "latest.pt"
    start_step = 0
    if args.resume:
        if not ckpt_path.is_file():
            raise FileNotFoundError(f"No checkpoint at {ckpt_path}")
        start_step = resume_checkpoint(ckpt_path, model, optimizer, generator,
                                       cfg=cfg, hyperparameters=hyperparameters,
                                       provenance=provenance)
        if args.steps < start_step:
            raise ValueError("Target --steps is lower than checkpoint step")
        print(f"Resumed from step {start_step}", flush=True)
    elif ckpt_path.exists():
        raise FileExistsError(
            f"Existing checkpoint at {ckpt_path}; choose new --out-dir or --resume")

    initial = evaluate(model, validation_ids, seq_len=args.seq_len,
                       n_loops=args.depth, n_windows=args.eval_windows,
                       device=args.device)
    print(f"Start step={start_step} heldout_nll={initial['nll']:.5f} "
          f"ppl={initial['perplexity']:.3f}", flush=True)

    train_loss = None
    t0 = time.perf_counter()
    for step in range(start_step + 1, args.steps + 1):
        model.train()
        x, y = draw_batch(train_ids, seq_len=args.seq_len,
                          batch_size=args.batch_size, generator=generator,
                          device=args.device)
        optimizer.zero_grad(set_to_none=True)
        logits = model(x, n_loops=args.depth)
        loss = F.cross_entropy(logits.reshape(-1, VOCAB_SIZE), y.reshape(-1))
        if not torch.isfinite(loss.detach()):
            raise RuntimeError(f"Nonfinite loss at step {step}")
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        train_loss = float(loss.detach())
        if step % 10 == 0 or step == args.steps:
            print(f"step={step}/{args.steps} train_loss={train_loss:.5f}",
                  flush=True)
        if step % args.save_every == 0 or step == args.steps:
            atomic_checkpoint(
                ckpt_path,
                checkpoint_bundle(
                    model, optimizer, generator, cfg=cfg,
                    hyperparameters=hyperparameters,
                    provenance=provenance, step=step
                )
            )

    final = evaluate(model, validation_ids, seq_len=args.seq_len,
                     n_loops=args.depth, n_windows=args.eval_windows,
                     device=args.device)
    sample = greedy_sample(model, args.prompt, n_loops=args.depth,
                           max_new_tokens=args.generate_tokens,
                           max_seq_len=args.seq_len, device=args.device)

    report = {
        "experiment": "R1 first real-text small OpenMythos training pilot",
        "upstream_commit": commit_id(root),
        "torch_version": torch.__version__, "device": args.device,
        "configuration": asdict(cfg), "hyperparameters": hyperparameters,
        "tokenizer": TOKENIZER_ID, "source_provenance": provenance,
        "start_step": start_step, "target_step": args.steps,
        "train_loss_last_step": train_loss,
        "heldout_before_this_run": initial,
        "heldout_after_this_run": final,
        "training_seconds_this_run": time.perf_counter() - t0,
        "model_parameters": sum(p.numel() for p in model.parameters()),
        "sample_generation": sample,
        "checkpoint": str(ckpt_path),
        "limitations": "Real text, byte tokenizer, tiny randomly initialized model, "
                       "small train/heldout subsets. This is a trainability pilot, "
                       "not an Anthropic Mythos weight or architecture replica, "
                       "not an authoritative benchmark, not equal-compute comparison. "
                       "Checkpoint contains tensor and primitive data only.",
    }
    atomic_json(out / "report.json", report)
    print(f"Final heldout NLL={final['nll']:.5f} "
          f"PPL={final['perplexity']:.3f} tokens={final['tokens']}")
    print("Sample continuation:", repr(sample["continuation"]))
    print("Checkpoint:", ckpt_path)
    print("Report:", out / "report.json")


if __name__ == "__main__":
    main()
