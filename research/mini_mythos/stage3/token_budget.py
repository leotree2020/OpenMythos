#!/usr/bin/env python3
"""Largest training-token budget the Stage 1 corpus supports in one pass for every seed:
min over seeds of (packable rows // global batch) * global batch * seq_len. Prints the number.

  python token_budget.py --data DATA [--seeds 0 1 --seq-len 1024 --global-batch 32]
"""
import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "stage2"))
import gpu_common as G  # noqa: E402


def budget(data, seeds, seq_len, global_batch):
    tokens, lengths = G.load_train_corpus(data)
    steps = min(len(G.pack_rows(tokens, lengths, seq_len + 1, seed=s)) // global_batch for s in seeds)
    return steps * global_batch * seq_len, int(lengths.sum())


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--data", required=True)
    p.add_argument("--seeds", type=int, nargs="+", default=[0, 1])
    p.add_argument("--seq-len", type=int, default=1024)
    p.add_argument("--global-batch", type=int, default=32)
    args = p.parse_args()
    n, total = budget(args.data, args.seeds, args.seq_len, args.global_batch)
    print("corpus %d tokens; one-pass budget %d tokens (%.1f%%)" % (total, n, 100.0 * n / total), file=sys.stderr)
    print(n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
