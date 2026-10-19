#!/usr/bin/env python3
"""
Gate E training (PREREGISTRATION 2.1, 9.6). The training loop is that of the
archived gen_gate_a/train_level.py with --schedule extended (AdamW lr from
budget_a/schedule.extended_lr, weight decay 0.1, batch 64, clip 1.0, loss on
the answer position only), statement for statement in the same order; only
the task, the checkpoint list and the logging differ:

    --task k2         K=2 direct lookup, training stream Random(60_000 + seed)
                      with held-out bodies redrawn, build(arm, 2)
    --task k4-equiv   level A exactly as train_level.py (train_rng("A", seed),
                      make_sample("A", rng, "train"), build(arm, 4)); used only
                      by the equivalence test against train_level.py

Checkpoints: step 0 (before the first update) and every step in --save-at,
as <ckpt-dir>/K<K>_<arm>_s<seed>_step<N>.pt. Logging (read-only, under
no_grad, never changes the trajectory): the loss of every step; every 10 steps
up to step 1000 and every 100 after: L_roots, L_within, P(roots) of the
training batch and the pre-clip gradient norm; every 25 steps up to 1000 and
every 250 after: dev metrics (k2: dev_heldout accuracy, P(roots), query
insensitivity, query-swap both-correct).

    python experiments/gate_e/train_k.py --task k2 --arm openmythos --seed 1 \\
        --steps 12000 --save-at 25,50,...,12000 --out experiments/gate_e/runs/K2_openmythos_s1.json
"""

import argparse
import hashlib
import json
import os
import sys
import time

import torch
import torch.nn.functional as F

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from e_common import RUNS, Geom, atomic_torch_save, atomic_write_json, family_tensors, load_set  # noqa: E402
from e_task import train_rng_k2, train_sample_k2  # noqa: E402
from data import encode_rows, load_set as load_level_set, roots_of  # noqa: E402  gen_gate_a
from levels import make_sample  # noqa: E402  gen_gate_a
from models import build  # noqa: E402  basic_learn
from schedule import extended_lr  # noqa: E402  budget_a
from splits import train_rng  # noqa: E402  gen_gate_a


def log_due(step1, dense_until, dense_every, sparse_every):
    return step1 % (dense_every if step1 <= dense_until else sparse_every) == 0


@torch.no_grad()
def batch_terms(logits, rows):
    """L_roots = -log P(roots), L_within = -log p(answer | roots), P(roots)."""
    logP = torch.log_softmax(logits.double(), -1)
    out = {"L_roots": 0.0, "L_within": 0.0, "p_roots": 0.0}
    for i, (p, a) in enumerate(rows):
        r = torch.tensor(sorted(roots_of(p)))
        lpr = torch.logsumexp(logP[i, r], 0)
        out["L_roots"] += float(-lpr)
        out["L_within"] += float(-(logP[i, ord(a)] - lpr))
        out["p_roots"] += float(lpr.exp())
    return {k: v / len(rows) for k, v in out.items()}


@torch.no_grad()
def dev_probe_k2(model, dev):
    x, y, slot, bid, roots = dev
    model.eval()
    L = model(x)[:, -1]
    model.train()
    pred = L.argmax(-1)
    N = len(roots)
    ok = (pred == y).view(N, 2)
    P = torch.softmax(L.double(), -1)
    proots = P.gather(1, roots.repeat_interleave(2, 0)).sum(1)
    return {"acc": float(ok.double().mean()), "p_roots": float(proots.mean()),
            "query_insensitivity": float((pred.view(N, 2)[:, 0] == pred.view(N, 2)[:, 1]).double().mean()),
            "query_swap_both": float(ok.all(1).double().mean())}


@torch.no_grad()
def dev_probe_level(model, ds):
    model.eval()
    pred = model(ds["x"][:, :-1])[:, -1].argmax(-1)
    model.train()
    return {"acc": float((pred == ds["y"]).double().mean()),
            "pred_in_roots": sum(int(a) in c for a, c in zip(pred, ds["roots"])) / len(pred)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True, choices=["k2", "k4-equiv"])
    ap.add_argument("--arm", required=True, choices=["openmythos", "transformer"])
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--steps", type=int, default=12000)
    ap.add_argument("--batch-size", type=int, default=64)
    ap.add_argument("--save-at", default="", help="comma-separated steps (step 0 is always saved)")
    ap.add_argument("--ckpt-dir", default=RUNS)
    ap.add_argument("--dev", default="dev_heldout", help="k2 only: name of the dev set")
    ap.add_argument("--threads", type=int, default=1)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    K = 2 if args.task == "k2" else 4
    torch.set_num_threads(args.threads)
    torch.manual_seed(args.seed)
    if args.task == "k2":
        rng = train_rng_k2(args.seed)
        draw = lambda: train_sample_k2(rng)  # noqa: E731
        dev = family_tensors(load_set(args.dev), Geom(2))
        probe = lambda m: dev_probe_k2(m, dev)  # noqa: E731
    else:
        rng = train_rng("A", args.seed)
        draw = lambda: make_sample("A", rng, "train")  # noqa: E731
        dev = load_level_set("A", "dev")
        probe = lambda m: dev_probe_level(m, dev)  # noqa: E731
    model = build(args.arm, K)
    opt = torch.optim.AdamW(model.parameters(), lr=2e-3, weight_decay=0.1)
    save_at = {int(s) for s in args.save_at.split(",") if s}
    os.makedirs(args.ckpt_dir, exist_ok=True)

    def save(step):
        path = os.path.join(args.ckpt_dir, f"K{K}_{args.arm}_s{args.seed}_step{step}.pt")
        atomic_torch_save({"K": K, "task": args.task, "arm": args.arm, "seed": args.seed, "step": step,
                           "model": model.state_dict()}, path)

    save(0)
    losses, light, devlog = [], [], []
    first_batch_sha = None
    t0 = time.perf_counter()
    model.train()
    for step in range(args.steps):
        for g in opt.param_groups:
            g["lr"] = extended_lr(step)
        rows = [draw() for _ in range(args.batch_size)]
        x, y = encode_rows(rows)
        if step == 0:
            first_batch_sha = hashlib.sha256(x.numpy().tobytes()).hexdigest()
        logits = model(x[:, :-1])[:, -1]
        loss = F.cross_entropy(logits, y)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        gnorm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        step1 = step + 1
        losses.append(loss.item())
        if log_due(step1, 1000, 10, 100):
            light.append({"step": step1, "loss": losses[-1], "grad_norm_preclip": float(gnorm),
                          **batch_terms(logits.detach(), rows)})
        if step1 in save_at:
            save(step1)
        if log_due(step1, 1000, 25, 250):
            devlog.append({"step": step1, **probe(model)})
    result = {"task": args.task, "K": K, "arm": args.arm, "seed": args.seed, "steps": args.steps,
              "batch_size": args.batch_size, "schedule": "budget_a/schedule.extended_lr",
              "save_at": sorted(save_at | {0}), "first_batch_sha256": first_batch_sha,
              "wall_seconds": time.perf_counter() - t0, "loss_every_step": losses,
              "light_log": light, "dev_log": devlog}
    atomic_write_json(args.out, result)
    print(f"saved {args.out} ({result['wall_seconds']:.0f}s)")


if __name__ == "__main__":
    main()
