#!/usr/bin/env python3
"""
Train one arm on one Gate A level. Models, optimizer and schedule are those
of experiments/basic_learn (AdamW, lr 2e-3, wd 0.1, warmup 100 + cosine to
10%, batch 64, clip 1.0, loss on the answer position only). Every step draws
fresh problems from splits.train_rng(level, seed) (training split; C2 mixes
1 and 2 hops), identical for both arms with the same seed.

Every --probe-every steps, on the fixed dev set (sets/<level>_dev.jsonl):
accuracy, root-swap and query-swap both-correct rates and prediction-in-roots.
Also logged: training loss, gradient norm (total and per part), MoE expert
gradient status and routing counts (via ../memorize/train_mem.py helpers),
actual block compute. Saves the final checkpoint and a JSON record.

    python experiments/gen_gate_a/train_level.py --level A --arm openmythos --seed 1 \\
        --out experiments/gen_gate_a/runs/A_openmythos_s1.json
"""

import argparse
import json
import math
import os
import sys
import time

import torch
import torch.nn.functional as F
from loguru import logger

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.append(os.path.join(HERE, "..", "memorize"))
sys.path.append(os.path.join(HERE, "..", "basic_learn"))

from data import encode_rows, load_set  # noqa: E402
from levels import N_STATEMENTS, make_sample  # noqa: E402
from models import block_applications, build  # noqa: E402
from splits import train_rng  # noqa: E402
from train_mem import expert_grad_status, get_lr, grad_report  # noqa: E402

from open_mythos.main import MoEFFN  # noqa: E402


@torch.no_grad()
def probe(model, ds):
    model.eval()
    out = {}
    p = model(ds["x"][:, :-1])[:, -1].argmax(-1)
    ok = p == ds["y"]
    out["acc"] = ok.float().mean().item()
    out["pred_in_roots"] = sum(int(a) in c for a, c in zip(p, ds["roots"])) / len(p)
    pr = model(ds["x_rs"][:, :-1])[:, -1].argmax(-1)
    out["root_swap_both"] = (ok & (pr == ds["y_rs"])).float().mean().item()
    if len(ds["qs_idx"]):
        pq = model(ds["x_qs"][:, :-1])[:, -1].argmax(-1)
        out["query_swap_both"] = (
            (ok[ds["qs_idx"]] & (pq == ds["y_qs"])).float().mean().item()
        )
    model.train()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--level", required=True, choices=list(N_STATEMENTS))
    ap.add_argument("--arm", required=True, choices=["openmythos", "transformer"])
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--steps", type=int, default=3000)
    ap.add_argument("--batch-size", type=int, default=64)
    ap.add_argument("--lr", type=float, default=2e-3)
    ap.add_argument("--warmup", type=int, default=100)
    ap.add_argument("--probe-every", type=int, default=250)
    ap.add_argument("--threads", type=int, default=1)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    torch.set_num_threads(args.threads)
    torch.manual_seed(args.seed)
    rng = train_rng(args.level, args.seed)
    dev = load_set(args.level, "dev")

    model = build(args.arm, N_STATEMENTS[args.level])
    n_params = sum(p.numel() for p in model.parameters())
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.1)
    calls = [0]
    if args.arm == "openmythos":
        model.recurrent.injection.register_forward_hook(
            lambda m, i, o: calls.__setitem__(0, calls[0] + 1)
        )
    routing = {"active": False, "interval": {}, "total": {}}

    def router_hook(name, moe):
        def hook(mod, inp, out):
            if not routing["active"]:
                return
            idx = (out + moe.router_bias).topk(moe.topk, dim=-1).indices
            key = f"{name}@loop{calls[0] if name.startswith('recurrent') else 0}"
            c = torch.bincount(idx.flatten(), minlength=moe.n_experts)
            for d in (routing["interval"], routing["total"]):
                d[key] = d.get(key, 0) + c

        return hook

    for name, m in model.named_modules():
        if isinstance(m, MoEFFN):
            m.router.register_forward_hook(router_hook(name, m))

    status_counts, log = {}, []
    block_token_steps, loss_sum, acc_sum, n_since = 0, 0.0, 0.0, 0
    first_batch_sha = None
    t0 = time.perf_counter()
    logger.info(f"{args.level} {args.arm} s{args.seed} | params {n_params}")
    model.train()
    for step in range(args.steps):
        for g in opt.param_groups:
            g["lr"] = get_lr(step, args.warmup, args.steps, args.lr)
        rows = [make_sample(args.level, rng, "train") for _ in range(args.batch_size)]
        x, y = encode_rows(rows)
        if step == 0:
            import hashlib

            first_batch_sha = hashlib.sha256(x.numpy().tobytes()).hexdigest()
        calls[0] = 0
        routing["active"] = True
        logits = model(x[:, :-1])[:, -1]
        routing["active"] = False
        block_token_steps += (
            block_applications(model, calls[0]) * len(rows) * (x.shape[1] - 1)
        )
        loss = F.cross_entropy(logits, y)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        gnorm, parts, missing = grad_report(model, args.arm)
        estat = expert_grad_status(model)
        for k, v in estat.items():
            kind = v if isinstance(v, str) else "nonzero"
            d = status_counts.setdefault(k, {"none": 0, "zero": 0, "nonzero": 0})
            d[kind] += 1
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        loss_sum += loss.item()
        acc_sum += (logits.argmax(-1) == y).float().mean().item()
        n_since += 1

        if (step + 1) % args.probe_every == 0:
            pr = probe(model, dev)
            log.append(
                {
                    "step": step + 1,
                    "train_loss": loss_sum / n_since,
                    "train_acc": acc_sum / n_since,
                    "dev": pr,
                    "grad_norm": gnorm,
                    "grad_norm_parts": parts,
                    "params_without_grad": missing,
                    "expert_grad_last_step": estat,
                    "routing_counts_interval": {
                        k: v.tolist() for k, v in routing["interval"].items()
                    },
                    "block_token_steps": block_token_steps,
                }
            )
            routing["interval"] = {}
            logger.info(
                f"{args.level} {args.arm} s{args.seed} | step {step + 1}/{args.steps} | "
                f"loss {loss_sum / n_since:.4f} | dev acc {pr['acc']:.3f} "
                f"rs {pr['root_swap_both']:.3f} qs {pr.get('query_swap_both', float('nan')):.3f} "
                f"in-roots {pr['pred_in_roots']:.3f} | {time.perf_counter() - t0:.0f}s"
            )
            loss_sum = acc_sum = 0.0
            n_since = 0

    result = {
        "level": args.level,
        "arm": args.arm,
        "seed": args.seed,
        "steps": args.steps,
        "params": n_params,
        "first_batch_sha256": first_batch_sha,
        "block_token_steps": block_token_steps,
        "wall_seconds": time.perf_counter() - t0,
        "expert_grad_status_counts": status_counts,
        "routing_counts_total": {k: v.tolist() for k, v in routing["total"].items()},
        "router_bias_final": {
            n: m.router_bias.tolist()
            for n, m in model.named_modules()
            if isinstance(m, MoEFFN)
        },
        "log": log,
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(result, f)
    torch.save(
        {
            "level": args.level,
            "arm": args.arm,
            "seed": args.seed,
            "model": model.state_dict(),
        },
        args.out.replace(".json", ".pt"),
    )
    logger.success(f"saved {args.out}")


if __name__ == "__main__":
    main()
