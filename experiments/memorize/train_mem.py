#!/usr/bin/env python3
"""
Memorization diagnostic: train one arm on a fixed set of 1-hop problems.

Model, optimizer and learning-rate schedule are exactly those of
experiments/basic_learn (AdamW, lr 2e-3, wd 0.1, warmup 100 + cosine to 10%,
clip 1.0). Only the data changes: the same fixed problems are reused every
step instead of fresh ones.
    Gate 1: 32 problems, full batch (all 32 every step)
    Gate 2: 512 problems, batch 64, reshuffled each epoch with a per-seed RNG
            that is identical for both arms (paired order)

Every --log-every steps, on the whole fixed set in eval mode: loss, accuracy,
fraction of predictions that are one of the prompt's root digits; plus the
total and per-part gradient norm of the last step, the number of parameter
tensors that received no gradient (e.g. MoE experts not routed), actual
training block compute, and a hash check that the fixed data is unchanged.
At the end, accuracy on a fresh held-out 1-hop set (information only).

    python experiments/memorize/train_mem.py --arm openmythos --seed 1 --n 32 \\
        --out experiments/memorize/runs/g1_openmythos_s1.json
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
sys.path.insert(0, os.path.join(HERE, "..", "basic_learn"))

from fixed_sets import digest, fixed_set, heldout_set, root_candidates  # noqa: E402
from models import block_applications, build  # noqa: E402

PARTS = {  # parameter-name prefix -> reported part
    "openmythos": [
        ("embed", "embed/head"),
        ("prelude", "first block"),
        ("recurrent.block", "middle block"),
        ("recurrent.", "loop-only (injection/ACT/LoRA/norm)"),
        ("coda", "last block"),
        ("norm", "final norm"),
    ],
    "transformer": [
        ("embed", "embed/head"),
        ("layers.0", "first block"),
        ("layers.1", "middle block"),
        ("layers.2", "last block"),
        ("norm", "final norm"),
    ],
}


def get_lr(step, warmup, total, max_lr):
    if step < warmup:
        return max_lr * (step + 1) / warmup
    progress = (step - warmup) / max(1, total - warmup)
    return 0.1 * max_lr + 0.9 * max_lr * 0.5 * (1 + math.cos(math.pi * progress))


@torch.no_grad()
def score(model, x, y, cands):
    model.eval()
    logits = model(x[:, :-1])[:, -1]
    model.train()
    pred = logits.argmax(-1)
    return {
        "loss": F.cross_entropy(logits, y).item(),
        "acc": (pred == y).float().mean().item(),
        "n_correct": int((pred == y).sum()),
        "pred_in_roots": sum(int(p) in c for p, c in zip(pred, cands)) / len(y),
    }


def grad_report(model, arm):
    parts, missing, sq = {}, 0, 0.0
    for name, p in model.named_parameters():
        if p.grad is None:
            missing += 1
            continue
        g = p.grad.pow(2).sum().item()
        sq += g
        part = next(lab for pre, lab in PARTS[arm] if name.startswith(pre))
        parts[part] = parts.get(part, 0.0) + g
    return math.sqrt(sq), {k: math.sqrt(v) for k, v in parts.items()}, missing


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True, choices=["openmythos", "transformer"])
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--n", type=int, required=True, choices=[32, 512])
    ap.add_argument("--steps", type=int, required=True)
    ap.add_argument("--batch-size", type=int, required=True)
    ap.add_argument("--lr", type=float, default=2e-3)
    ap.add_argument("--warmup", type=int, default=100)
    ap.add_argument("--log-every", type=int, default=50)
    ap.add_argument("--threads", type=int, default=1)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    torch.set_num_threads(args.threads)
    torch.manual_seed(args.seed)
    order_rng = random.Random(20_000 + args.seed)  # batch order; same for both arms
    x, y = fixed_set(args.n)
    ref_hash = digest(x, y)
    cands = root_candidates(x)
    xh, yh = heldout_set()

    model = build(args.arm, 8)
    n_params = sum(p.numel() for p in model.parameters())
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.1)
    calls = [0]
    if args.arm == "openmythos":
        model.recurrent.injection.register_forward_hook(
            lambda m, i, o: calls.__setitem__(0, calls[0] + 1)
        )

    tok_per_row = x.shape[1] - 1
    block_token_steps = 0
    order, pos = [], 0
    log = []
    first_full = None
    t0 = time.perf_counter()
    model.train()
    logger.info(
        f"{args.arm} s{args.seed} n={args.n} | params {n_params} | data {ref_hash[:12]}"
    )
    for step in range(args.steps):
        for g in opt.param_groups:
            g["lr"] = get_lr(step, args.warmup, args.steps, args.lr)
        if args.batch_size >= args.n:
            idx = list(range(args.n))
        else:
            if pos + args.batch_size > len(order):
                order, pos = list(range(args.n)), 0
                order_rng.shuffle(order)
            idx = order[pos : pos + args.batch_size]
            pos += args.batch_size
        xb, yb = x[idx], y[idx]
        calls[0] = 0
        logits = model(xb[:, :-1])[:, -1]
        block_token_steps += (
            block_applications(model, calls[0]) * len(idx) * tok_per_row
        )
        loss = F.cross_entropy(logits, yb)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        gnorm, parts, missing = grad_report(model, args.arm)
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()

        if (step + 1) % args.log_every == 0 or step == 0:
            s = score(model, x, y, cands)
            if s["n_correct"] == args.n and first_full is None:
                first_full = step + 1
            rec = {
                "step": step + 1,
                "batch_loss": loss.item(),
                **{f"set_{k}": v for k, v in s.items()},
                "grad_norm": gnorm,
                "grad_norm_parts": parts,
                "params_without_grad": missing,
                "block_token_steps": block_token_steps,
                "data_unchanged": digest(x, y) == ref_hash,
            }
            log.append(rec)
            logger.info(
                f"{args.arm} s{args.seed} n={args.n} | step {step + 1}/{args.steps} | "
                f"set loss {s['loss']:.4f} acc {s['acc']:.3f} ({s['n_correct']}/{args.n}) "
                f"in-roots {s['pred_in_roots']:.3f} | grad {gnorm:.3f} | no-grad {missing} | "
                f"{time.perf_counter() - t0:.0f}s"
            )

    final = score(model, x, y, cands)
    held = score(model, xh, yh, root_candidates(xh))
    result = {
        "arm": args.arm,
        "seed": args.seed,
        "n": args.n,
        "steps": args.steps,
        "batch_size": args.batch_size,
        "params": n_params,
        "data_sha256": ref_hash,
        "data_unchanged_all": all(r["data_unchanged"] for r in log),
        "final": final,
        "first_step_all_correct": first_full,
        "heldout_info_only": held,
        "block_token_steps": block_token_steps,
        "wall_seconds": time.perf_counter() - t0,
        "log": log,
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(result, f)
    logger.success(
        f"{args.arm} s{args.seed} n={args.n} final acc {final['acc']:.3f} loss {final['loss']:.4f}"
    )


if __name__ == "__main__":
    main()
