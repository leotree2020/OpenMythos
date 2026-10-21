#!/usr/bin/env python3
"""
Attribute the NLL change between a reference depth (T_ref, the trained depth)
and deeper T to token groups defined by ACT state at T_ref.

Without a KV cache, a sequence whose positions have all halted by T_ref gets
the same output at any T >= T_ref (halted positions take zero weight on later
loops, and sequences in a batch do not attend to each other). So any change
from T_ref to T must start at positions still running at T_ref; positions that
had halted can only change through the Coda's attention to those. This splits
ΔNLL accordingly:

    halted@ref     -- halted by T_ref (indirect effect only)
    unhalted@ref   -- never reached act_threshold within T_ref loops, further
                      binned by their ACT weight sum at T_ref and by the loop
                      at which they halt at the deeper T

    PYTHONPATH=training:. python training/depth_attribution.py --ckpt s1.pt s2.pt s3.pt \\
        --data test.jsonl --ref-t 4 --n-loops 8,16 --out attribution.jsonl
"""

import argparse
import json
import os

import torch
import torch.nn.functional as F
from loguru import logger

from depth_ablation import RULES, new_stats
from eval_ppl import (
    ByteTokenizer,
    build_stream,
    load_docs,
    load_model,
    make_windows,
    verify_patch,
)
from open_mythos.tokenizer import MythosTokenizer

W_BINS = [0.0, 0.5, 0.9, 0.99, 1.01]


@torch.no_grad()
def per_token(model, windows, n_loops, batch_size, device, amp_ctx):
    """Per-token NLL, halt step and ACT weight sum, flattened in a fixed order."""
    block = model.recurrent
    block.stats = new_stats(n_loops, keep_tokens=True)
    nll = []
    for start in range(0, len(windows), batch_size):
        group = windows[start : start + batch_size]
        by_len = {}
        for w in group:
            by_len.setdefault(len(w), []).append(w)
        for chunk in by_len.values():
            batch = torch.stack(chunk).to(device)
            x, y = batch[:, :-1], batch[:, 1:]
            with amp_ctx:
                logits = model(x, n_loops=n_loops)
            nll.append(
                F.cross_entropy(
                    logits.float().transpose(1, 2), y, reduction="none"
                ).cpu()
            )
    s = block.stats
    block.stats = None
    flat = lambda xs: torch.cat([t.flatten() for t in xs])  # noqa: E731
    return (
        flat(nll).double(),
        flat(s["token_halt_step"]),
        flat(s["token_weight_sum"]).double(),
    )


def summarize(mask, d_nll, total):
    n = int(mask.sum())
    dsum = d_nll[mask].sum().item() if n else 0.0
    return {
        "n_tokens": n,
        "dnll_sum": dsum,
        "dnll_mean": dsum / n if n else None,
        "share_of_total_dnll": dsum / total if total else None,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--ckpt", nargs="+", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--text-field", default="text")
    ap.add_argument("--max-docs", type=int, default=0)
    ap.add_argument("--seq-len", type=int, default=1024)
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--rule", default="BASE", choices=list(RULES))
    ap.add_argument("--ref-t", type=int, default=4)
    ap.add_argument("--n-loops", default="8,16")
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    ap.add_argument("--dtype", default="bf16", choices=["bf16", "fp16", "fp32"])
    ap.add_argument("--tokenizer", default=None, help='HF id/path, or "bytes"')
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    if args.tokenizer == "bytes":
        tok = ByteTokenizer()
    else:
        tok = MythosTokenizer(args.tokenizer) if args.tokenizer else MythosTokenizer()
    ids, n_bytes = build_stream(
        load_docs(args.data, args.text_field, args.max_docs), tok
    )
    windows = make_windows(ids, args.seq_len)
    if args.device.startswith("cuda") and args.dtype != "fp32":
        dt = torch.bfloat16 if args.dtype == "bf16" else torch.float16
        amp_ctx = torch.autocast("cuda", dtype=dt)
    else:
        amp_ctx = torch.autocast("cpu", enabled=False)

    with open(args.out, "a", encoding="utf-8") as out:
        for path in args.ckpt:
            model = load_model(path, args.device, RULES[args.rule])
            verify_patch(model, windows[0], args.ref_t, args.device)
            nll_ref, halt_ref, w_ref = per_token(
                model, windows, args.ref_t, args.batch_size, args.device, amp_ctx
            )
            unhalted = halt_ref == 0
            for T in [int(t) for t in args.n_loops.split(",")]:
                nll_t, halt_t, _ = per_token(
                    model, windows, T, args.batch_size, args.device, amp_ctx
                )
                d = nll_t - nll_ref
                total = d.sum().item()
                row = {
                    "ckpt": path,
                    "rule": args.rule,
                    "ref_t": args.ref_t,
                    "n_loops": T,
                    "n_tokens": len(d),
                    "n_bytes": n_bytes,
                    "dnll_total": total,
                    "dnll_per_byte": total / n_bytes,
                    "frac_unhalted_at_ref": unhalted.float().mean().item(),
                    "halted@ref": summarize(~unhalted, d, total),
                    "unhalted@ref": summarize(unhalted, d, total),
                    "unhalted_by_weight_sum_at_ref": {},
                    "unhalted_by_halt_loop_at_T": {},
                }
                for lo, hi in zip(W_BINS, W_BINS[1:]):
                    m = unhalted & (w_ref >= lo) & (w_ref < hi)
                    row["unhalted_by_weight_sum_at_ref"][f"[{lo},{hi})"] = summarize(
                        m, d, total
                    )
                for k in sorted(set(halt_t[unhalted].tolist())):
                    m = unhalted & (halt_t == k)
                    key = "never" if k == 0 else str(k)
                    row["unhalted_by_halt_loop_at_T"][key] = summarize(m, d, total)
                out.write(json.dumps(row) + "\n")
                out.flush()
                logger.info(
                    f"{os.path.basename(path)} | T={args.ref_t}->{T} | "
                    f"ΔNLL/byte {row['dnll_per_byte']:+.5f} | "
                    f"unhalted@{args.ref_t} {row['frac_unhalted_at_ref']:.3f} "
                    f"carry {row['unhalted@ref']['share_of_total_dnll'] or 0:.2%} "
                    "of ΔNLL"
                )
            del model


if __name__ == "__main__":
    main()
