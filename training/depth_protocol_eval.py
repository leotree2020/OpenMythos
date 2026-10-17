#!/usr/bin/env python3
"""
Recursive-depth ablation eval under the shared test protocol.

Rules (training/depth_ablation.py RULES): BASE, B1, B2, C, B1+C, B2+C.
Core depths T = 4, 8, 16; extended T = 1, 2, 3, 4, 6, 8, 12, 16.

Per (checkpoint, rule, T) one JSONL row with:
    - NLL / PPL. Scored positions: every token of the concatenated eval
      stream except the first, in non-overlapping windows of --seq-len
      targets. byte_ppl = exp(nll_sum / n_bytes) with n_bytes = UTF-8 bytes
      of all eval documents (fixed for every rule and T); token_ppl =
      exp(nll_sum / n_scored_tokens). The two are reported separately and
      never mixed.
    - Three distinct depth/compute measures:
        act_halt_*            per-token first loop where cumulative halting
                              probability reached act_threshold (ACT
                              effective halting depth; 0 = never halted
                              within the loops executed)
        loops_per_call        loops the recurrent block executed per forward
                              call (forward-level early exit needs every
                              position in the batch to halt)
        loop_tokens / fwd_s   recurrent loop executions × tokens, and wall time
    - mean ACT output weight sum (before any B2 normalization), fraction
      below 0.99, fraction of positions that never reached the threshold
    - per-loop hidden-state RMS and relative change
      ||h_t - h_{t-1}|| / ||h_{t-1}|| (aggregated over calls that ran loop t)
A leading "meta" row records model config, source commit, checkpoint id,
dataset fingerprint, batch size and that the all-off patch reproduced the
library forward exactly (checked per checkpoint before any cell runs).

    PYTHONPATH=. python training/depth_protocol_eval.py --ckpt s1.pt s2.pt s3.pt \\
        --data test.jsonl --rules BASE,B1,B2,C --n-loops 4,8,16 --out proto.jsonl
"""

import argparse
import dataclasses
import hashlib
import json
import math
import os
import subprocess
import time

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

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def git_commit() -> dict:
    def run(*cmd):
        return subprocess.run(
            cmd, cwd=REPO, capture_output=True, text=True, check=False
        ).stdout.strip()

    return {
        "commit": run("git", "rev-parse", "HEAD"),
        "dirty": bool(run("git", "status", "--porcelain", "--untracked-files=no")),
    }


def file_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 24), b""):
            h.update(chunk)
    return h.hexdigest()


def cfg_dict(cfg) -> dict:
    if dataclasses.is_dataclass(cfg):
        return {f.name: getattr(cfg, f.name) for f in dataclasses.fields(cfg)}
    return dict(vars(cfg))


@torch.no_grad()
def run_cell(model, windows, n_loops, batch_size, device, amp_ctx) -> dict:
    block = model.recurrent
    block.stats = new_stats(n_loops)
    nll_sum, n_tok, fwd_s = 0.0, 0, 0.0
    cuda = device.startswith("cuda")
    for start in range(0, len(windows), batch_size):
        group = windows[start : start + batch_size]
        by_len = {}
        for w in group:
            by_len.setdefault(len(w), []).append(w)
        for chunk in by_len.values():
            batch = torch.stack(chunk).to(device)
            x, y = batch[:, :-1], batch[:, 1:]
            if cuda:
                torch.cuda.synchronize()
            t0 = time.perf_counter()
            with amp_ctx:
                logits = model(x, n_loops=n_loops)
            if cuda:
                torch.cuda.synchronize()
            fwd_s += time.perf_counter() - t0
            nll_sum += F.cross_entropy(
                logits.float().reshape(-1, logits.size(-1)),
                y.reshape(-1),
                reduction="sum",
            ).item()
            n_tok += y.numel()
    s = block.stats
    block.stats = None

    hist = s["halt_step_hist"].tolist()
    halted = sum(hist[1:])
    ran = s["loop_calls"] > 0
    h_rms = torch.where(ran, (s["h_sq"] / s["loop_elems"].clamp(min=1)).sqrt(), 0)
    rel = torch.where(ran, (s["dh_sq"] / s["prev_sq"].clamp(min=1e-30)).sqrt(), 0)
    return {
        "nll_sum": nll_sum,
        "n_scored_tokens": n_tok,
        "forward_calls": s["forward_calls"],
        "loops_per_call": s["loops_executed_sum"] / s["forward_calls"],
        "loop_tokens": s["token_loops_executed_sum"],
        "fwd_seconds": fwd_s,
        "act_halt_hist": hist,  # index k: halted on loop k; 0: never
        "act_frac_unhalted": hist[0] / s["tokens"],
        "act_mean_halt_step": (
            sum(k * c for k, c in enumerate(hist)) / halted if halted else None
        ),
        "act_mean_weight_sum": s["weight_sum_sum"] / s["tokens"],
        "act_frac_weight_sum_below_0_99": s["weight_sum_below_0_99"] / s["tokens"],
        "loop_calls": s["loop_calls"].tolist(),
        "h_rms_per_loop": [round(v, 6) for v in h_rms.tolist()],
        "rel_change_per_loop": [round(v, 6) for v in rel.tolist()],
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--ckpt", nargs="+", required=True)
    ap.add_argument("--data", required=True, help=".jsonl or plain-text eval file")
    ap.add_argument("--text-field", default="text")
    ap.add_argument("--max-docs", type=int, default=0)
    ap.add_argument("--seq-len", type=int, default=1024)
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--rules", default="BASE,B1,B2,C", help=",".join(RULES))
    ap.add_argument("--n-loops", default="4,8,16")
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    ap.add_argument("--dtype", default="bf16", choices=["bf16", "fp16", "fp32"])
    ap.add_argument("--tokenizer", default=None, help='HF id/path, or "bytes"')
    ap.add_argument("--no-ckpt-hash", action="store_true", help="skip sha256 of ckpt")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    rules = args.rules.split(",")
    for r in rules:
        if r not in RULES:
            ap.error(f"unknown rule {r!r}; choose from {list(RULES)}")
    loops = [int(n) for n in args.n_loops.split(",")]

    if args.tokenizer == "bytes":
        tok = ByteTokenizer()
    else:
        tok = MythosTokenizer(args.tokenizer) if args.tokenizer else MythosTokenizer()
    docs = load_docs(args.data, args.text_field, args.max_docs)
    ids, n_bytes = build_stream(docs, tok)
    windows = make_windows(ids, args.seq_len)
    data_fp = hashlib.sha256(ids.numpy().tobytes()).hexdigest()
    logger.info(f"{len(ids)} tokens | {n_bytes} bytes | data sha256 {data_fp[:16]}")

    if args.device.startswith("cuda") and args.dtype != "fp32":
        dt = torch.bfloat16 if args.dtype == "bf16" else torch.float16
        amp_ctx = torch.autocast("cuda", dtype=dt)
    else:
        amp_ctx = torch.autocast("cpu", enabled=False)

    src = git_commit()
    with open(args.out, "a", encoding="utf-8") as out:
        for path in args.ckpt:
            ckpt_id = None if args.no_ckpt_hash else file_sha256(path)
            base = load_model(path, args.device, RULES["BASE"])
            for n in sorted({4, max(loops)} & set(loops) or {max(loops)}):
                verify_patch(base, windows[0], n, args.device)
            meta = {
                "type": "meta",
                "ckpt": path,
                "ckpt_sha256": ckpt_id,
                "ckpt_step": torch.load(
                    path, map_location="cpu", weights_only=False
                ).get("step"),
                "cfg": cfg_dict(base.cfg),
                "source": src,
                "torch": torch.__version__,
                "device": args.device,
                "dtype": args.dtype,
                "data": args.data,
                "data_token_sha256": data_fp,
                "n_docs": len(docs),
                "n_tokens": len(ids),
                "n_bytes": n_bytes,
                "seq_len": args.seq_len,
                "batch_size": args.batch_size,
                "byte_ppl_definition": "exp(nll over all tokens but the stream's "
                "first / UTF-8 bytes of all eval documents)",
                "equivalence_verified": True,
            }
            out.write(json.dumps(meta, default=str) + "\n")
            del base

            for rule in rules:
                model = load_model(path, args.device, RULES[rule])
                for n_loops in loops:
                    r = run_cell(
                        model, windows, n_loops, args.batch_size, args.device, amp_ctx
                    )
                    row = {
                        "type": "cell",
                        "ckpt": path,
                        "ckpt_sha256": ckpt_id,
                        "rule": rule,
                        "n_loops": n_loops,
                        "trained_loops": model.cfg.max_loop_iters,
                        "n_bytes": n_bytes,
                        "nll_per_byte": r["nll_sum"] / n_bytes,
                        "byte_ppl": math.exp(r["nll_sum"] / n_bytes),
                        "nll_per_token": r["nll_sum"] / r["n_scored_tokens"],
                        "token_ppl": math.exp(r["nll_sum"] / r["n_scored_tokens"]),
                        **r,
                    }
                    out.write(json.dumps(row) + "\n")
                    out.flush()
                    logger.info(
                        f"{os.path.basename(path)} | {rule:5s} | T={n_loops:<3d} | "
                        f"byte_ppl {row['byte_ppl']:.4f} | "
                        f"loops/call {r['loops_per_call']:.2f} | "
                        f"halt mean {r['act_mean_halt_step'] or 0:.2f} "
                        f"unhalted {r['act_frac_unhalted']:.3f} | "
                        f"w_sum {r['act_mean_weight_sum']:.3f} | {r['fwd_seconds']:.1f}s"
                    )
                del model
                if args.device.startswith("cuda"):
                    torch.cuda.empty_cache()


if __name__ == "__main__":
    main()
