#!/usr/bin/env python3
"""Score the reasoning probes: for every item, the log-probability of each candidate answer after
the prompt (no BOS; prompt and candidate tokenized separately and concatenated), averaged over
CPU-seeded h0 replicas; the prediction is the candidate with the highest total log-probability.
Single-token candidate sets use one forward per item; otherwise one row per candidate.

  python -B score.py --sets reasoning_sets.jsonl --split dev --depths 4,8,16,32 --out DIR [--run RUN]

Writes DIR/items_d{depth}.csv (id, family, level, correct, margin, chosen) and DIR/score.json.
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "stage3"))
sys.path.insert(0, str(HERE.parent / "stage2"))
import gpu_common as G  # noqa: E402

SEED_BASE = 3_000_000


def load_items(path, split, max_per_cell=0):
    with open(path, encoding="utf-8") as f:
        rows = [json.loads(x) for x in f]
    rows = [r for r in rows if split is None or r["split"] == split]
    if max_per_cell:                                   # for quick tests only
        seen = {}
        keep = []
        for r in rows:
            key = (r["family"], r["level"])
            seen[key] = seen.get(key, 0) + 1
            if seen[key] <= max_per_cell:
                keep.append(r)
        rows = keep
    return rows


import contextlib


@contextlib.contextmanager
def item_seeded_h0(model, specs):
    """Per batch row (seed, item_len, row_len): h0 = initialize_state on a (1, item_len, D) CPU tensor
    after torch.manual_seed(seed), cut to row_len and zero-padded to the batch length. All candidates
    of an item therefore share the same h0 on the prompt, independent of batching and padding."""
    import torch
    original = model.initialize_state

    def init(embeds):
        if embeds.shape[0] != len(specs):
            raise RuntimeError("spec count does not match the batch")
        T, D = embeds.shape[1], embeds.shape[2]
        rows = []
        for seed, item_len, row_len in specs:
            torch.manual_seed(seed)
            h = original(torch.zeros((1, item_len, D), dtype=embeds.dtype))[:, :row_len]
            rows.append(torch.cat([h, torch.zeros((1, T - row_len, D), dtype=h.dtype)], 1))
        return torch.cat(rows, 0).to(embeds.device)

    model.initialize_state = init
    try:
        yield
    finally:
        del model.initialize_state


def item_len(e):
    return len(e["prompt"]) + max(len(c) for c in e["cands"])


def encode_items(tok, items):
    enc = []
    for k, it in enumerate(items):
        p = tok.encode(it["prompt"], add_special_tokens=False).ids
        c = [tok.encode(x, add_special_tokens=False).ids for x in it["candidates"]]
        enc.append({"k": k, "prompt": p, "cands": c, "single": all(len(x) == 1 for x in c)})
    return enc


def score_items(torch, model, enc, device, depth, replicas=2, batch_tokens=16384, seed_base=SEED_BASE):
    """Returns an array [n_items, max_cands] of replica-mean total log-probs (nan where no candidate)."""
    n_c = max(len(e["cands"]) for e in enc)
    out = np.full((len(enc), n_c), np.nan)
    rows = []                               # (item index, candidate index or -1 for fast path, tokens)
    for i, e in enumerate(enc):
        if e["single"]:
            rows.append((i, -1, e["prompt"]))
        else:
            for j, c in enumerate(e["cands"]):
                rows.append((i, j, e["prompt"] + c))
    limit = model.config.block_size
    if max(len(r[2]) for r in rows) > limit:
        raise SystemExit("an item is longer than the model context (%d tokens)" % limit)
    order = sorted(range(len(rows)), key=lambda r: len(rows[r][2]))
    steps = torch.tensor([depth, 0], dtype=torch.long)
    acc = np.zeros_like(out)
    for rep in range(replicas):
        k = 0
        while k < len(order):
            L = len(rows[order[k]][2])
            m = k
            while m < len(order) and (m - k + 1) * len(rows[order[m]][2]) <= max(batch_tokens, L):
                m += 1
            chunk = [rows[order[x]] for x in range(k, max(m, k + 1))]
            k = max(m, k + 1)
            T = max(len(r[2]) for r in chunk)
            x = torch.zeros((len(chunk), T), dtype=torch.long)
            for b, r in enumerate(chunk):
                x[b, :len(r[2])] = torch.tensor(r[2])      # right padding: earlier positions unaffected (causal)
            specs = [(seed_base + 10 * enc[r[0]]["k"] + rep, item_len(enc[r[0]]), len(r[2])) for r in chunk]
            with torch.no_grad(), item_seeded_h0(model, specs):
                logits = model(x.to(device), return_logits=True, num_steps_pair=steps)["logits"]
            logp = torch.log_softmax(logits.double(), dim=-1).cpu()
            for b, (i, j, toks) in enumerate(chunk):
                e = enc[i]
                if j < 0:
                    last = logp[b, len(e["prompt"]) - 1]
                    for jj, c in enumerate(e["cands"]):
                        acc[i, jj] += float(last[c[0]])
                else:
                    P = len(e["prompt"])
                    c = e["cands"][j]
                    acc[i, j] += float(sum(logp[b, P - 1 + t, c[t]] for t in range(len(c))))
    for i, e in enumerate(enc):
        out[i, :len(e["cands"])] = acc[i, :len(e["cands"])] / replicas
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--sets", required=True)
    p.add_argument("--split", default="dev")
    p.add_argument("--depths", default="4,8,16,32")
    p.add_argument("--replicas", type=int, default=2)
    p.add_argument("--run", help="trained Stage 3/3b run directory (mechanism + optional trained base)")
    p.add_argument("--out", required=True)
    p.add_argument("--upstream", default=G.s0.DEFAULTS["upstream"])
    p.add_argument("--model-dir", default=G.s0.DEFAULTS["model_dir"])
    p.add_argument("--tokenizer", default=G.s0.DEFAULTS["tokenizer"])
    p.add_argument("--device", default="cuda")
    p.add_argument("--threads", type=int, default=4)
    p.add_argument("--batch-tokens", type=int, default=16384)
    p.add_argument("--max-per-cell", type=int, default=0, help="testing only")
    p.add_argument("--no-pin-check", action="store_true")
    args = p.parse_args()
    torch = G.setup(args.device, args.threads)
    from tokenizers import Tokenizer
    tok = Tokenizer.from_file(args.tokenizer)
    model, _ = G.load_model(torch, args.upstream, args.model_dir, args.tokenizer, args.device,
                            pin_check=not args.no_pin_check)
    for prm in model.parameters():
        prm.requires_grad_(False)
    what = "native"
    if args.run:
        import mechanisms as M
        cfg = json.loads((Path(args.run) / "config.json").read_text())["config"]
        mech = M.attach(torch, model, cfg["mode"], rank=cfg["rank"], alpha=cfg["alpha"], seed=cfg["seed"])
        M.load_params(torch, mech, Path(args.run) / "final_params.pt")
        if cfg.get("unfreeze"):
            model.load_state_dict(torch.load(Path(args.run) / "final_base.pt", map_location="cpu", weights_only=True))
        what = "run " + Path(args.run).name
    items = load_items(args.sets, args.split, args.max_per_cell)
    enc = encode_items(tok, items)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    info = {"what": what, "split": args.split, "items": len(items), "replicas": args.replicas,
            "single_token_items": sum(e["single"] for e in enc), "depths": {}}
    for depth in [int(d) for d in args.depths.split(",")]:
        t = time.time()
        lp = score_items(torch, model, enc, args.device, depth, args.replicas, args.batch_tokens)
        secs = time.time() - t
        with open(out / ("items_d%d.csv" % depth), "w", encoding="utf-8") as f:
            f.write("id,family,level,correct,margin,chosen\n")
            for it, row in zip(items, lp):
                row = row[:len(it["candidates"])]
                a = it["answer"]
                other = np.max(np.delete(row, a))
                f.write("%s,%s,%d,%d,%.6f,%d\n" % (it["id"], it["family"], it["level"],
                                                   int(np.argmax(row) == a), row[a] - other, int(np.argmax(row))))
        acc = float(np.mean([np.argmax(r[:len(it["candidates"])]) == it["answer"] for it, r in zip(items, lp)]))
        info["depths"][depth] = {"seconds": secs, "accuracy_all": acc}
        print("depth %d: accuracy %.4f (%.0f s)" % (depth, acc, secs), flush=True)
    (out / "score.json").write_text(json.dumps(info, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
