#!/usr/bin/env python3
"""
Byte-level perplexity eval for OpenMythos checkpoints across loop depths and
depth-extrapolation switches.

For every (checkpoint, n_loops, ablation) cell this reports byte-level PPL,
token-level PPL, the mean number of loops ACT actually ran, and forward time.

Byte-level PPL = exp(total NLL in nats / total UTF-8 bytes of the eval text),
so it is comparable across tokenizers. Documents are encoded separately and
concatenated without separators (same packing as training), then scored in
non-overlapping windows of `--seq-len` predicted tokens. Every token except
the very first one of the stream is scored.

Ablations (switches from training/depth_ablation.py, patched onto the loaded
model so open_mythos is unchanged; neither adds parameters, so they apply to
any existing checkpoint):
    base       -- checkpoint as trained
    remainder  -- act_final_remainder=True
    clamp      -- clamp_loop_emb=True
    both       -- both switches on

Examples:
    python training/eval_ppl.py --ckpt ckpts/seed1/step_0100000.pt \\
        --data test.jsonl --n-loops 4,8,16
    python training/eval_ppl.py --ckpt a.pt b.pt c.pt --data test.jsonl \\
        --ablations base,both --out results.jsonl
"""

import argparse
import json
import math
import time

import torch
import torch.nn.functional as F
from depth_ablation import apply_depth_ablation, check_matches_original
from loguru import logger

from open_mythos import OpenMythos
from open_mythos.tokenizer import MythosTokenizer

ABLATIONS = {
    "base": {"act_final_remainder": False, "clamp_loop_emb": False},
    "remainder": {"act_final_remainder": True, "clamp_loop_emb": False},
    "clamp": {"act_final_remainder": False, "clamp_loop_emb": True},
    "both": {"act_final_remainder": True, "clamp_loop_emb": True},
}


def load_docs(path: str, text_field: str, max_docs: int) -> list[str]:
    """
    Read eval documents: `.jsonl` → one doc per line (`text_field`),
    anything else → the whole file is one doc.
    """
    if path.endswith(".jsonl"):
        docs = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    docs.append(json.loads(line)[text_field])
                if max_docs and len(docs) >= max_docs:
                    break
        return docs
    with open(path, encoding="utf-8") as f:
        return [f.read()]


class ByteTokenizer:
    """UTF-8 bytes as token ids (vocab 256); for small local experiments."""

    vocab_size = 256

    def encode(self, text: str) -> list[int]:
        return list(text.encode("utf-8"))


def build_stream(docs: list[str], tokenizer) -> tuple[torch.Tensor, int]:
    """Concatenate per-doc token ids; return (ids, total UTF-8 bytes)."""
    ids = []
    n_bytes = 0
    for doc in docs:
        ids.extend(tokenizer.encode(doc))
        n_bytes += len(doc.encode("utf-8"))
    return torch.tensor(ids, dtype=torch.long), n_bytes


def make_windows(ids: torch.Tensor, seq_len: int) -> list[torch.Tensor]:
    """
    Split into windows of up to seq_len + 1 tokens that overlap by one token,
    so each window predicts seq_len targets and no target is scored twice.
    """
    return [
        ids[i : i + seq_len + 1]
        for i in range(0, len(ids) - 1, seq_len)
        if len(ids[i : i + seq_len + 1]) >= 2
    ]


def load_model(path: str, device: str, flags: dict) -> OpenMythos:
    """Rebuild the model from the cfg pickled in the checkpoint and patch it."""
    ckpt = torch.load(path, map_location="cpu", weights_only=False)
    model = OpenMythos(ckpt["cfg"])
    model.load_state_dict(ckpt["model"])
    return apply_depth_ablation(model.to(device).eval(), **flags)


@torch.no_grad()
def verify_patch(model: OpenMythos, window: torch.Tensor, n_loops: int, device):
    """Check the patched loop matches the library's on one real input."""
    captured = {}
    hook = model.recurrent.register_forward_pre_hook(
        lambda m, args: captured.setdefault("args", args)
    )
    model(window[None, :-1].to(device), n_loops=n_loops)
    hook.remove()
    h, e, freqs_cis, mask = captured["args"][:4]
    check_matches_original(model.recurrent, h, e, freqs_cis, mask, n_loops)


@torch.no_grad()
def evaluate(
    model: OpenMythos,
    windows: list[torch.Tensor],
    n_loops: int,
    batch_size: int,
    device: str,
    amp_ctx,
) -> dict:
    """Score all windows at a given loop depth."""
    total_nll = 0.0
    total_tok = 0
    loops_weighted = 0.0
    fwd_time = 0.0

    # Group equal-length windows (only the tail one can be shorter)
    for start in range(0, len(windows), batch_size):
        group = windows[start : start + batch_size]
        by_len = {}
        for w in group:
            by_len.setdefault(len(w), []).append(w)
        for chunk in by_len.values():
            batch = torch.stack(chunk).to(device)
            x, y = batch[:, :-1], batch[:, 1:]
            if device.startswith("cuda"):
                torch.cuda.synchronize()
            t0 = time.perf_counter()
            with amp_ctx:
                logits = model(x, n_loops=n_loops)
            if device.startswith("cuda"):
                torch.cuda.synchronize()
            fwd_time += time.perf_counter() - t0
            nll = F.cross_entropy(
                logits.float().reshape(-1, logits.size(-1)),
                y.reshape(-1),
                reduction="sum",
            )
            total_nll += nll.item()
            total_tok += y.numel()
            loops_weighted += model.recurrent.last_loops_run * y.numel()

    return {
        "nll": total_nll,
        "tokens": total_tok,
        "mean_loops_run": loops_weighted / total_tok,
        "fwd_seconds": fwd_time,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--ckpt", nargs="+", required=True, help="checkpoint path(s)")
    ap.add_argument("--data", required=True, help=".jsonl or plain-text eval file")
    ap.add_argument("--text-field", default="text")
    ap.add_argument("--max-docs", type=int, default=0, help="0 = all")
    ap.add_argument("--seq-len", type=int, default=1024)
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--n-loops", default="4,8,16", help="comma-separated depths")
    ap.add_argument(
        "--ablations", default="base,remainder,clamp,both", help=",".join(ABLATIONS)
    )
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    ap.add_argument("--dtype", default="bf16", choices=["bf16", "fp16", "fp32"])
    ap.add_argument(
        "--tokenizer", default=None, help='HF tokenizer id/path, or "bytes"'
    )
    ap.add_argument("--out", default=None, help="append one JSON line per cell")
    args = ap.parse_args()

    n_loops_list = [int(n) for n in args.n_loops.split(",")]
    ablations = args.ablations.split(",")
    for a in ablations:
        if a not in ABLATIONS:
            ap.error(f"unknown ablation {a!r}; choose from {list(ABLATIONS)}")

    if args.tokenizer == "bytes":
        tokenizer = ByteTokenizer()
    elif args.tokenizer:
        tokenizer = MythosTokenizer(args.tokenizer)
    else:
        tokenizer = MythosTokenizer()
    docs = load_docs(args.data, args.text_field, args.max_docs)
    ids, n_bytes = build_stream(docs, tokenizer)
    windows = make_windows(ids, args.seq_len)
    logger.info(
        f"{len(docs)} docs | {len(ids)} tokens | {n_bytes} bytes | "
        f"{len(windows)} windows of ≤{args.seq_len}"
    )

    if args.device.startswith("cuda") and args.dtype != "fp32":
        amp_dtype = torch.bfloat16 if args.dtype == "bf16" else torch.float16
        amp_ctx = torch.autocast("cuda", dtype=amp_dtype)
    else:
        amp_ctx = torch.autocast("cpu", enabled=False)

    out_f = open(args.out, "a", encoding="utf-8") if args.out else None  # noqa: SIM115
    rows = []
    for ckpt_path in args.ckpt:
        for ablation in ablations:
            model = load_model(ckpt_path, args.device, ABLATIONS[ablation])
            if model.cfg.max_seq_len < args.seq_len:
                ap.error(f"--seq-len exceeds cfg.max_seq_len={model.cfg.max_seq_len}")
            verify_patch(model, windows[0], max(n_loops_list), args.device)
            for n_loops in n_loops_list:
                r = evaluate(
                    model, windows, n_loops, args.batch_size, args.device, amp_ctx
                )
                row = {
                    "ckpt": ckpt_path,
                    "ablation": ablation,
                    "n_loops": n_loops,
                    "trained_loops": model.cfg.max_loop_iters,
                    "byte_ppl": math.exp(r["nll"] / n_bytes),
                    "token_ppl": math.exp(r["nll"] / r["tokens"]),
                    "mean_loops_run": r["mean_loops_run"],
                    "fwd_seconds": r["fwd_seconds"],
                    "tokens": r["tokens"],
                    "bytes": n_bytes,
                }
                rows.append(row)
                logger.info(
                    f"{ckpt_path} | {ablation:9s} | T={n_loops:<3d} | "
                    f"byte_ppl {row['byte_ppl']:.4f} | tok_ppl {row['token_ppl']:.3f} | "
                    f"loops_run {row['mean_loops_run']:.2f} | {row['fwd_seconds']:.1f}s"
                )
                if out_f:
                    out_f.write(json.dumps(row) + "\n")
                    out_f.flush()
            del model
            if args.device.startswith("cuda"):
                torch.cuda.empty_cache()
    if out_f:
        out_f.close()

    print(f"\n{'ckpt':40s} {'ablation':10s} {'T':>4s} {'byte_ppl':>9s} {'loops':>6s}")
    for r in rows:
        print(
            f"{r['ckpt'][-40:]:40s} {r['ablation']:10s} {r['n_loops']:>4d} "
            f"{r['byte_ppl']:>9.4f} {r['mean_loops_run']:>6.2f}"
        )


if __name__ == "__main__":
    main()
