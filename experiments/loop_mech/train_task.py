#!/usr/bin/env python3
"""
Train a tiny OpenMythos on multi-hop variable tracking with one loop mechanism.

    python experiments/loop_mech/train_task.py --mech rand_final --seed 1 \\
        --out experiments/loop_mech/ckpts/rand_final_s1.pt

Trained on hops 1..4; eval_task.py then tests hops 1..12 at many loop depths.
"""

import argparse
import math
import os
import random
import sys
import time

import torch
import torch.nn.functional as F
from loguru import logger

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mechanisms import MECHS, apply_readout  # noqa: E402
from task import make_batch, seq_len  # noqa: E402

from open_mythos.main import MythosConfig, OpenMythos  # noqa: E402


def task_cfg(max_loop_iters: int, n_statements: int) -> MythosConfig:
    return MythosConfig(
        vocab_size=256,
        dim=128,
        n_heads=4,
        n_kv_heads=2,
        max_seq_len=seq_len(n_statements),
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


def get_lr(step: int, warmup: int, total: int, max_lr: float) -> float:
    if step < warmup:
        return max_lr * (step + 1) / warmup
    progress = (step - warmup) / max(1, total - warmup)
    return 0.1 * max_lr + 0.9 * max_lr * 0.5 * (1 + math.cos(math.pi * progress))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mech", required=True, choices=list(MECHS))
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--out", required=True)
    ap.add_argument("--loops", type=int, default=4, help="fixed training depth")
    ap.add_argument("--rand-max", type=int, default=8, help="rand: T ~ U{1..max}")
    ap.add_argument("--train-hops", default="1,2,3,4")
    ap.add_argument("--n-statements", type=int, default=24)
    ap.add_argument("--batch-size", type=int, default=64)
    ap.add_argument("--steps", type=int, default=3000)
    ap.add_argument("--lr", type=float, default=2e-3)
    ap.add_argument("--warmup", type=int, default=100)
    ap.add_argument("--threads", type=int, default=1)
    ap.add_argument("--log-every", type=int, default=100)
    args = ap.parse_args()

    torch.set_num_threads(args.threads)
    torch.manual_seed(args.seed)
    rng = random.Random(args.seed)
    depth_mode, readout = MECHS[args.mech]
    max_loops = args.loops if depth_mode == "fixed" else args.rand_max
    hops = [int(h) for h in args.train_hops.split(",")]

    cfg = task_cfg(max_loops, args.n_statements)
    model = apply_readout(OpenMythos(cfg), readout)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.1)
    logger.info(f"{args.mech} seed {args.seed} | max_loop_iters {max_loops}")

    model.train()
    t0 = time.perf_counter()
    acc_sum = loss_sum = 0.0
    for step in range(args.steps):
        for g in opt.param_groups:
            g["lr"] = get_lr(step, args.warmup, args.steps, args.lr)
        n_loops = args.loops if depth_mode == "fixed" else rng.randint(1, args.rand_max)
        x, y = make_batch(rng, args.batch_size, hops, args.n_statements)
        logits = model(x[:, :-1], n_loops=n_loops)[:, -1]  # predict answer byte
        loss = F.cross_entropy(logits, y)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        loss_sum += loss.item()
        acc_sum += (logits.argmax(-1) == y).float().mean().item()
        if (step + 1) % args.log_every == 0:
            logger.info(
                f"{args.mech} s{args.seed} | step {step + 1}/{args.steps} | "
                f"loss {loss_sum / args.log_every:.4f} | "
                f"train_acc {acc_sum / args.log_every:.3f} | "
                f"{time.perf_counter() - t0:.0f}s"
            )
            acc_sum = loss_sum = 0.0

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    torch.save(
        {
            "step": args.steps,
            "model": model.state_dict(),
            "cfg": cfg,
            "mech": args.mech,
            "seed": args.seed,
            "train_hops": hops,
            "n_statements": args.n_statements,
        },
        args.out,
    )
    logger.success(f"saved {args.out}")


if __name__ == "__main__":
    main()
