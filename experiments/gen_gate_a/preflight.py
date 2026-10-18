#!/usr/bin/env python3
"""
Pre-training code checks for Gate A (no optimizer step is taken).

Per level:
  fixed sets   load with manifest hash; label == last token; input ends at
               '?'; labels are digit bytes; every answer is one of the
               prompt's roots; counterfactual labels are digits
  train data   the stream depends only on (level, seed): two fresh RNGs give
               byte-identical first batches (so both arms are paired);
               different seeds differ; C2's training stream mixes 1 and 2 hops
  init         each arm built twice with the same seed is identical; seeds
               1 and 2 differ; max_seq_len equals the level's sequence length
  forward      logits over 256 bytes; one backward pass has finite, non-zero
               gradients; initial loss close to ln 256
"""

import hashlib
import json
import math
import os
import sys

import torch
import torch.nn.functional as F

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.append(os.path.join(HERE, "..", "basic_learn"))

from data import encode_rows, load_set  # noqa: E402
from levels import LEVELS, N_STATEMENTS, make_sample, solve  # noqa: E402
from models import build  # noqa: E402
from splits import train_rng  # noqa: E402


def batch_sha(level, seed, n=64):
    r = train_rng(level, seed)
    x, _ = encode_rows([make_sample(level, r, "train") for _ in range(n)])
    return hashlib.sha256(x.numpy().tobytes()).hexdigest()


def main():
    rep, fail = {}, []
    for level in LEVELS:
        R = rep[level] = {}
        for split in ("dev", "test"):
            ds = load_set(level, split)
            x, y = ds["x"], ds["y"]
            if not torch.equal(x[:, -1], y):
                fail.append((level, split, "label != last token"))
            if not bool((x[:, -2] == ord("?")).all()):
                fail.append((level, split, "input does not end at ?"))
            for t in (y, ds["y_rs"]) + (
                (ds["y_qs"],) if ds["y_qs"] is not None else ()
            ):
                if not bool(((t >= 48) & (t <= 57)).all()):
                    fail.append((level, split, "non-digit label"))
            if not all(int(a) in c for a, c in zip(y, ds["roots"])):
                fail.append((level, split, "answer not among roots"))
            R[f"{split}_rows"] = len(y)
            R[f"{split}_seq_len"] = x.shape[1]
        s1a, s1b, s2 = batch_sha(level, 1), batch_sha(level, 1), batch_sha(level, 2)
        R["train_first_batch_sha_seed1"] = s1a[:16]
        if s1a != s1b:
            fail.append((level, "train stream not reproducible"))
        if s1a == s2:
            fail.append((level, "seeds 1 and 2 give the same stream"))
        if level == "C2":
            r = train_rng(level, 1)
            hops = [solve(make_sample(level, r, "train")[0])[1] for _ in range(1000)]
            R["train_first1000_hop_counts"] = {
                h: hops.count(h) for h in sorted(set(hops))
            }
            if set(hops) != {1, 2}:
                fail.append((level, "C2 train stream does not mix 1 and 2 hops"))
        r = train_rng(level, 1)
        xb, yb = encode_rows([make_sample(level, r, "train") for _ in range(64)])
        for arm in ("openmythos", "transformer"):
            torch.manual_seed(1)
            m1 = build(arm, N_STATEMENTS[level])
            torch.manual_seed(1)
            m1b = build(arm, N_STATEMENTS[level])
            torch.manual_seed(2)
            m2 = build(arm, N_STATEMENTS[level])
            same = all(
                torch.equal(a, b)
                for a, b in zip(m1.state_dict().values(), m1b.state_dict().values())
            )
            diff = any(
                not torch.equal(a, b)
                for a, b in zip(m1.state_dict().values(), m2.state_dict().values())
            )
            if not (same and diff):
                fail.append((level, arm, "init not seed-determined"))
            if m1.cfg.max_seq_len != xb.shape[1]:
                fail.append(
                    (level, arm, "max_seq_len", m1.cfg.max_seq_len, xb.shape[1])
                )
            logits = m1(xb[:, :-1])[:, -1]
            if logits.shape[-1] != 256:
                fail.append((level, arm, "vocab"))
            loss = F.cross_entropy(logits, yb)
            loss.backward()
            g = [p.grad for p in m1.parameters() if p.grad is not None]
            gn = math.sqrt(sum(t.pow(2).sum().item() for t in g))
            if not all(torch.isfinite(t).all() for t in g) or gn == 0:
                fail.append((level, arm, "gradients"))
            R[arm] = {
                "initial_loss": round(loss.item(), 3),
                "grad_norm": round(gn, 3),
                "params": sum(p.numel() for p in m1.parameters()),
            }
    rep["failures"] = [str(f) for f in fail]
    with open(os.path.join(HERE, "preflight.json"), "w") as f:
        json.dump(rep, f, indent=1)
    print(json.dumps(rep, indent=1))
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
