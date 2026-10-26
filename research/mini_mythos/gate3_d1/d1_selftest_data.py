#!/usr/bin/env python3
"""SYNTHETIC inputs for the D1 code self-tests. Not WikiText, not D1 evidence.

Writes rows.jsonl (physical rows, some blank), toy_tokenizer.txt (marker file for
the stdlib byte encoder used in mode=selftest) and manifest.json. Deterministic.
Variant 'no_p2_row' makes every eligible row with ordinal in [600, 900) shorter
than 3 tokens so that the P2 rule finds nothing (expected: BLOCKED(schedule)).
"""
import hashlib
import json
import os
import random
import sys

WORDS = ["alpha", "beta", "gamma", "delta", "epsilon", "zeta", "eta", "theta", "iota", "kappa",
         "lambda", "mu", "nu", "xi", "omicron", "pi", "rho", "sigma", "tau", "upsilon", "phi", "chi",
         "psi", "omega", "café", "café", "naïve", "日本語", "@-@", "1,234"]


def eligible_texts(variant="normal", n=2048, seed=20261026):
    rng = random.Random(seed)
    out = []
    for i in range(n):
        if i % 50 == 0:
            out.append(" = Title %d = \n" % i)                      # level-1 heading
        elif i % 50 == 7:
            out.append(" = = Section %d = = \n" % i)                # level-2: not an article start
        else:
            k = rng.randint(4, 24)
            out.append(" " + " ".join(rng.choice(WORDS) for _ in range(k)) + " \n")
        if variant == "no_p2_row" and 600 <= i < 900:
            out[-1] = rng.choice(["a", "bc"])                       # 1-2 tokens, not a heading
    return out


def build(dirpath, variant="normal"):
    os.makedirs(dirpath, exist_ok=True)
    rng = random.Random(7)
    rows = []
    for t in eligible_texts(variant):
        while rng.random() < 0.12:                                  # interleave ineligible rows
            rows.append(rng.choice(["", "\n", " \n", "   "]))
        rows.append(t)
    rows += ["", " tail row after the window, never read \n"]
    src = os.path.join(dirpath, "rows.jsonl")
    with open(src, "w", encoding="utf-8", newline="\n") as f:
        for t in rows:
            f.write(json.dumps({"text": t}, ensure_ascii=True) + "\n")
    tok = os.path.join(dirpath, "toy_tokenizer.txt")
    with open(tok, "wb") as f:
        f.write(b"TOY-BYTE-ENCODER-V1\n")
    def h(p):
        with open(p, "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()

    man = os.path.join(dirpath, "manifest.json")
    with open(man, "w", encoding="utf-8") as f:
        json.dump({"parquet_sha256": h(src), "tokenizer_sha256": h(tok), "actual_vocab_size": 259,
                   "synthetic": True}, f, sort_keys=True)
    return src, tok, man


if __name__ == "__main__":
    print(build(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "normal"))
