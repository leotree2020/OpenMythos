#!/usr/bin/env python3
"""
Tiny CPU-scale OpenMythos run for the depth-extrapolation study.

Byte-level (vocab 256) language model on tinyshakespeare, trained at a fixed
loop depth like training/3b_fine_web_edu.py (plain next-token CE, AdamW,
warmup + cosine). The last 10% of the corpus is held out and written to
data/test.txt for training/eval_ppl.py; the checkpoint uses the same layout
as the main training script so eval_ppl.py loads it unchanged.

    python experiments/toy_depth/train_toy.py --seed 1 --out ckpts/seed1.pt
"""

import argparse
import math
import os
import time

import torch
import torch.nn.functional as F
from loguru import logger

from open_mythos.main import MythosConfig, OpenMythos

HERE = os.path.dirname(os.path.abspath(__file__))


def toy_cfg(max_loop_iters: int, seq_len: int) -> MythosConfig:
    return MythosConfig(
        vocab_size=256,
        dim=128,
        n_heads=4,
        n_kv_heads=2,
        max_seq_len=seq_len,
        max_loop_iters=max_loop_iters,
        prelude_layers=1,
        coda_layers=1,
        attn_type="gqa",
        n_experts=4,
        n_shared_experts=1,
        n_experts_per_tok=2,
        expert_dim=128,
        lora_rank=8,
        act_threshold=0.99,
        rope_theta=10000.0,
    )


def split_corpus(path: str) -> torch.Tensor:
    """Return train bytes; write the held-out tail to data/test.txt."""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    cut = int(len(text) * 0.9)
    cut = text.rfind("\n\n", 0, cut) + 2  # split on a paragraph boundary
    test_path = os.path.join(os.path.dirname(path), "test.txt")
    with open(test_path, "w", encoding="utf-8") as f:
        f.write(text[cut:])
    return torch.tensor(list(text[:cut].encode("utf-8")), dtype=torch.long)


def get_lr(step: int, warmup: int, total: int, max_lr: float) -> float:
    if step < warmup:
        return max_lr * (step + 1) / warmup
    progress = (step - warmup) / max(1, total - warmup)
    return 0.1 * max_lr + 0.9 * max_lr * 0.5 * (1 + math.cos(math.pi * progress))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--out", required=True)
    ap.add_argument("--data", default=os.path.join(HERE, "data", "input.txt"))
    ap.add_argument("--loops", type=int, default=4, help="training loop depth")
    ap.add_argument("--seq-len", type=int, default=128)
    ap.add_argument("--batch-size", type=int, default=32)
    ap.add_argument("--steps", type=int, default=3000)
    ap.add_argument("--lr", type=float, default=2e-3)
    ap.add_argument("--warmup", type=int, default=100)
    ap.add_argument("--threads", type=int, default=1)
    ap.add_argument("--log-every", type=int, default=100)
    args = ap.parse_args()

    torch.set_num_threads(args.threads)
    torch.manual_seed(args.seed)
    train = split_corpus(args.data)

    cfg = toy_cfg(args.loops, args.seq_len)
    model = OpenMythos(cfg)
    n_params = sum(p.numel() for p in model.parameters())
    logger.info(f"seed {args.seed} | params {n_params / 1e6:.2f}M | loops {args.loops}")
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.1)

    gen = torch.Generator().manual_seed(args.seed)
    model.train()
    t0 = time.perf_counter()
    for step in range(args.steps):
        for g in opt.param_groups:
            g["lr"] = get_lr(step, args.warmup, args.steps, args.lr)
        idx = torch.randint(
            0, len(train) - args.seq_len - 1, (args.batch_size,), generator=gen
        )
        batch = torch.stack([train[i : i + args.seq_len + 1] for i in idx])
        x, y = batch[:, :-1], batch[:, 1:]
        logits = model(x)
        loss = F.cross_entropy(logits.reshape(-1, 256), y.reshape(-1))
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        if (step + 1) % args.log_every == 0:
            dt = time.perf_counter() - t0
            logger.info(
                f"seed {args.seed} | step {step + 1}/{args.steps} | loss {loss.item():.4f}"
                f" | loops_run {model.recurrent.__dict__.get('last_loops_run', '-')}"
                f" | {dt:.0f}s"
            )

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    torch.save(
        {
            "step": args.steps,
            "model": model.state_dict(),
            "optimizer": {},
            "cfg": cfg,
            "vocab_size": 256,
        },
        args.out,
    )
    logger.success(f"saved {args.out}")


if __name__ == "__main__":
    main()
