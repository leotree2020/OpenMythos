#!/usr/bin/env python3
"""
Train one arm of the basic-learnability experiment.

Controls versus experiments/loop_mech:
    - data RNG (random.Random(10_000 + seed)) is separate from parameter init
      (torch.manual_seed(seed)), so both arms with the same seed see the
      identical training sample sequence
    - actual loops executed per training step are counted (OpenMythos may
      exit early once all positions halt), giving the real cumulative
      training compute in block applications × tokens
    - a fixed held-out probe set (1 and 2 hops, separate seed) is scored
      every --probe-every steps for learning curves; it is never used to
      choose anything

    python experiments/basic_learn/train.py --arm openmythos --seed 1 \\
        --out experiments/basic_learn/ckpts/openmythos_s1.pt
"""

import argparse
import json
import math
import os
import random
import sys
import time

import torch
import torch.nn.functional as F
from loguru import logger

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "loop_mech"))

from eval_task import counterfactual  # noqa: E402
from models import block_applications, build  # noqa: E402
from task_v2 import make_batch  # noqa: E402

PROBE_SEED = 777


def get_lr(step, warmup, total, max_lr):
    if step < warmup:
        return max_lr * (step + 1) / warmup
    progress = (step - warmup) / max(1, total - warmup)
    return 0.1 * max_lr + 0.9 * max_lr * 0.5 * (1 + math.cos(math.pi * progress))


@torch.no_grad()
def probe(model, sets):
    model.eval()
    out = {}
    for hops, (x, y, xc, yc) in sets.items():
        p = model(x[:, :-1])[:, -1].argmax(-1)
        pc = model(xc[:, :-1])[:, -1].argmax(-1)
        out[hops] = {
            "acc": (p == y).float().mean().item(),
            "cf_both": ((p == y) & (pc == yc)).float().mean().item(),
        }
    model.train()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True, choices=["openmythos", "transformer"])
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--out", required=True)
    ap.add_argument("--train-hops", default="1,2")
    ap.add_argument("--n-statements", type=int, default=8)
    ap.add_argument("--batch-size", type=int, default=64)
    ap.add_argument("--steps", type=int, default=3000)
    ap.add_argument("--lr", type=float, default=2e-3)
    ap.add_argument("--warmup", type=int, default=100)
    ap.add_argument("--probe-every", type=int, default=250)
    ap.add_argument("--threads", type=int, default=1)
    args = ap.parse_args()

    torch.set_num_threads(args.threads)
    torch.manual_seed(args.seed)
    data_rng = random.Random(10_000 + args.seed)
    hops = [int(h) for h in args.train_hops.split(",")]

    model = build(args.arm, args.n_statements)
    n_params = sum(p.numel() for p in model.parameters())
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.1)
    calls = [0]
    if args.arm == "openmythos":
        model.recurrent.injection.register_forward_hook(
            lambda m, i, o: calls.__setitem__(0, calls[0] + 1)
        )

    probe_sets = {}
    for h in (1, 2):
        x, y = make_batch(random.Random(PROBE_SEED + h), 200, [h], args.n_statements)
        probe_sets[h] = (x, y, *counterfactual(x, PROBE_SEED + 100 + h))

    logger.info(f"{args.arm} s{args.seed} | params {n_params}")
    tokens = args.batch_size * (x.shape[1] - 1)
    block_token_steps = 0
    curve = []
    loss_sum = acc_sum = 0.0
    t0 = time.perf_counter()
    model.train()
    for step in range(args.steps):
        for g in opt.param_groups:
            g["lr"] = get_lr(step, args.warmup, args.steps, args.lr)
        x, y = make_batch(data_rng, args.batch_size, hops, args.n_statements)
        calls[0] = 0
        logits = model(x[:, :-1])[:, -1]
        block_token_steps += block_applications(model, calls[0]) * tokens
        loss = F.cross_entropy(logits, y)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        gnorm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0).item()
        opt.step()
        loss_sum += loss.item()
        acc_sum += (logits.argmax(-1) == y).float().mean().item()
        if (step + 1) % args.probe_every == 0:
            pr = probe(model, probe_sets)
            n = args.probe_every
            curve.append(
                {
                    "step": step + 1,
                    "train_loss": loss_sum / n,
                    "train_acc": acc_sum / n,
                    "grad_norm_last": gnorm,
                    "block_token_steps": block_token_steps,
                    "probe": pr,
                }
            )
            logger.info(
                f"{args.arm} s{args.seed} | step {step + 1}/{args.steps} | "
                f"loss {loss_sum / n:.4f} | train_acc {acc_sum / n:.3f} | "
                f"probe 1h {pr[1]['acc']:.3f} cf {pr[1]['cf_both']:.3f} | "
                f"2h {pr[2]['acc']:.3f} | {time.perf_counter() - t0:.0f}s"
            )
            loss_sum = acc_sum = 0.0

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    torch.save(
        {
            "arm": args.arm,
            "seed": args.seed,
            "model": model.state_dict(),
            "n_statements": args.n_statements,
            "train_hops": hops,
            "steps": args.steps,
            "params": n_params,
            "block_token_steps": block_token_steps,
            "curve": curve,
        },
        args.out,
    )
    with open(args.out.replace(".pt", "_curve.json"), "w") as f:
        json.dump(curve, f)
    logger.success(f"saved {args.out}")


if __name__ == "__main__":
    main()
