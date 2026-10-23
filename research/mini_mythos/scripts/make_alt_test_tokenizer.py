"""
Generate a small self-authored parquet and train an ALTERNATIVE TEST TOKENIZER
using upstream Parcae scripts/tok_train.py, then write standard config files
so Parcae Tokenizer loads bos/eos/pad correctly.

Does not modify upstream source.
"""

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

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

TOKENIZER_CONFIG = {
    "add_bos_token": False,
    "add_eos_token": False,
    "bos_token": "<|bos|>",
    "eos_token": "<|eos|>",
    "pad_token": "<|pad|>",
    "unk_token": None,
    "model_max_length": 2048,
    "tokenizer_class": "PreTrainedTokenizerFast",
}

SPECIAL_TOKENS_MAP = {
    "bos_token": "<|bos|>",
    "eos_token": "<|eos|>",
    "pad_token": "<|pad|>",
}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--parcae-root", required=True)
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
    subprocess.check_call(cmd, cwd=args.parcae_root)

    (tok_dir / "tokenizer_config.json").write_text(json.dumps(TOKENIZER_CONFIG, indent=2))
    (tok_dir / "special_tokens_map.json").write_text(json.dumps(SPECIAL_TOKENS_MAP, indent=2))

    for name in ["tokenizer.json", "tokenizer_config.json", "special_tokens_map.json"]:
        h = hashlib.sha256((tok_dir / name).read_bytes()).hexdigest()
        print(f"{name} sha256: {h}")

    print("ALTERNATIVE TEST TOKENIZER — not official Parcae.")
    print("Actual vocab size is determined by corpus; do not assume", args.vocab_size)


if __name__ == "__main__":
    main()
