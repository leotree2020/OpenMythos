"""
Generate a small self-authored parquet and train an ALTERNATIVE TEST TOKENIZER
using the upstream Parcae scripts/tok_train.py logic.

This is NOT the official Parcae tokenizer. License of the official HF tokenizer
remains unconfirmed; do not download it.

Usage (from a checkout of pinned Parcae):
  python research/mini_mythos/scripts/make_alt_test_tokenizer.py \
      --parcae-root /path/to/parcae \
      --out-dir /tmp/alt_tok
"""

import argparse
import hashlib
import subprocess
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

# Self-authored, clearly licensed synthetic corpus
CORPUS = [
    "The quick brown fox jumps over the lazy dog. " * 20,
    "Hello world. This is a test sentence for tokenizer training. " * 15,
    "Numbers: 123 4567 89. Contractions: I'm you're it's. " * 10,
    "Special chars: @#$%^&*() and unicode: 你好世界. " * 8,
    "Machine learning models process sequences of tokens. " * 12,
    "Recurrent transformers reuse parameters across steps. " * 10,
    "Prelude core coda architecture for looped models. " * 10,
    "Begin of sequence end of sequence pad token handling. " * 8,
] * 5


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--parcae-root", required=True, help="Path to pinned Parcae checkout")
    p.add_argument("--out-dir", required=True)
    p.add_argument("--vocab-size", type=int, default=32768)
    args = p.parse_args()

    out = Path(args.out_dir)
    data_dir = out / "data"
    tok_dir = out / "tokenizer"
    data_dir.mkdir(parents=True, exist_ok=True)
    tok_dir.mkdir(parents=True, exist_ok=True)

    pq.write_table(pa.table({"text": CORPUS}), data_dir / "sample.parquet")

    cmd = [
        sys.executable,
        str(Path(args.parcae_root) / "scripts" / "tok_train.py"),
        "--data-dir", str(data_dir),
        "--output-dir", str(tok_dir),
        "--vocab-size", str(args.vocab_size),
        "--max-chars", "500000",
        "--doc-cap", "2000",
    ]
    print("running:", " ".join(cmd))
    subprocess.check_call(cmd, cwd=args.parcae_root)

    tok_json = tok_dir / "tokenizer.json"
    h = hashlib.sha256(tok_json.read_bytes()).hexdigest()
    print("tokenizer.json sha256:", h)
    print("NOTE: actual vocab size is determined by corpus size;")
    print("      do not assume it equals the requested", args.vocab_size)
    print("ALTERNATIVE TEST TOKENIZER — not official Parcae.")


if __name__ == "__main__":
    main()
