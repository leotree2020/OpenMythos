#!/usr/bin/env python3
"""Assemble the Stage 2 data directory from Stage 1 revision 1, verified by sha256.

- eval_sets.jsonl: copied from the committed Stage 1 results (it holds the token ids), so the
  slow evaluation-candidate streaming does not have to be repeated on the GPU machine.
- train_tokens.u16 / train_doc_lengths.i32: kept if already built and identical to the Stage 1
  manifest; otherwise rebuilt from the locked training source only (no eval selection).

  python assemble_data.py --results STAGE1/results/r1 --out DATA --tokenizer TOK
Exit 0 only if every file matches the Stage 1 manifest.
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "stage1"))
import build_data as B  # noqa: E402

TRAIN = ("train_tokens.u16", "train_doc_lengths.i32")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--results", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--tokenizer", required=True)
    args = p.parse_args()
    res, out = Path(args.results), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((res / "manifest.json").read_text())
    lock = json.loads((res / "data_lock.json").read_text())

    def ok(name):
        f = out / name
        return f.exists() and B.sha256_file(f) == manifest[name]

    if not all(ok(n) for n in TRAIN):
        print("rebuilding the training corpus from the locked source", flush=True)
        from huggingface_hub import HfApi, HfFileSystem
        from tokenizers import Tokenizer
        if B.sha256_file(args.tokenizer) != B.TOKENIZER_SHA256:
            raise SystemExit("tokenizer differs from the pinned Parcae tokenizer")
        tok = Tokenizer.from_file(args.tokenizer)
        src = B.resolve(HfApi(), "train", B.SOURCES["train"], lock["sources"]["train"])
        texts = B.hub_texts(HfFileSystem(), src, B.SOURCES["train"]["fmt"], B.SOURCES["train"]["column"])
        tokens, lengths = B.build_train(
            texts, lambda ts: [e.ids for e in tok.encode_batch(ts, add_special_tokens=False)],
            lock["params"]["train_tokens"])
        (out / TRAIN[0]).write_bytes(tokens.astype("<u2").tobytes())
        (out / TRAIN[1]).write_bytes(lengths.astype("<i4").tobytes())
    shutil.copyfile(res / "eval_sets.jsonl", out / "eval_sets.jsonl")
    shutil.copyfile(res / "data_lock.json", out / "data_lock.json")
    bad = [n for n in TRAIN + ("eval_sets.jsonl",) if not ok(n)]
    if bad:
        raise SystemExit("files differ from the Stage 1 manifest: %s" % bad)
    (out / "manifest.json").write_text(json.dumps({n: manifest[n] for n in TRAIN + ("eval_sets.jsonl",)},
                                                  indent=1, sort_keys=True) + "\n")
    print("DATA IDENTICAL TO STAGE 1 (train corpus + eval sets verified by sha256)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
