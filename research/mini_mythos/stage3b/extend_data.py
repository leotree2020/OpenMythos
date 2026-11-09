#!/usr/bin/env python3
"""Stage 3b: extend the Stage 1 training corpus to ~220M tokens. The evaluation sets do not change.

The locked Stage 1 training stream (FineWeb-Edu sample-100BT, data_lock.json) is replayed document
by document. The first part must reproduce the Stage 1 corpus byte for byte (sha256 against the
Stage 1 manifest); this proves the stream position. Reading then continues with the next documents.
Every new document is checked against all 1200 evaluation windows (13-grams); a document with any
overlap is dropped (the evaluation windows are never touched).

  python extend_data.py --results STAGE1/results/r1 --out DATA --tokenizer TOK [--total-tokens 220000000]

Writes DATA/train_tokens.u16, DATA/train_doc_lengths.i32 (Stage 1 documents first), DATA/eval_sets.jsonl
(copied, sha256-checked), DATA/extension.json (counts) and DATA/manifest.json. If DATA/manifest.json
exists and every file matches it, nothing is rebuilt. Exit 0 only when everything checks out.
"""
import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "stage1"))
import build_data as B  # noqa: E402
import ngrams  # noqa: E402

FILES = ("train_tokens.u16", "train_doc_lengths.i32", "eval_sets.jsonl")


def eval_ngram_set(eval_rows):
    h = [ngrams.hashes(r["tokens"]) for r in eval_rows]
    return np.unique(np.concatenate(h)) if h else np.zeros(0, np.uint64)


def extend(texts, encode_batch, stage1_tokens, stage1_sha, eval_set, total_tokens, batch_size=256):
    """Pure pipeline. Returns (tokens uint16, lengths int32, report).
    stage1_tokens: the Stage 1 target (its build stopped at the first document reaching it);
    stage1_sha: {"train_tokens.u16": sha, "train_doc_lengths.i32": sha} of the Stage 1 corpus."""
    pieces, lengths, total = [], [], 0
    n1 = None                                    # number of Stage 1 documents, once reached
    rep = {"new_docs_examined": 0, "new_docs_dropped_eval_overlap": 0, "new_docs_kept": 0,
           "new_tokens_dropped": 0, "empty_docs_skipped": 0}
    done = False
    batch = []

    def flush():
        nonlocal total, n1, done
        for ids in encode_batch(batch):
            if not ids:
                rep["empty_docs_skipped"] += 1
                continue
            arr = np.asarray(ids, dtype=np.uint32)
            if arr.max() >= 2 ** 16:
                raise SystemExit("token id does not fit uint16")
            if n1 is not None:                   # extension document: drop on any eval overlap
                rep["new_docs_examined"] += 1
                if ngrams.member(ngrams.hashes(arr), eval_set).any():
                    rep["new_docs_dropped_eval_overlap"] += 1
                    rep["new_tokens_dropped"] += len(arr)
                    continue
                rep["new_docs_kept"] += 1
            pieces.append(arr.astype(np.uint16))
            lengths.append(len(arr))
            total += len(arr)
            if n1 is None and total >= stage1_tokens:
                n1 = len(lengths)
                check_stage1()
            if n1 is not None and total >= total_tokens:
                done = True
                return

    def check_stage1():
        tok = np.concatenate(pieces).astype("<u2").tobytes()
        lens = np.asarray(lengths, dtype="<i4").tobytes()
        got = {"train_tokens.u16": hashlib.sha256(tok).hexdigest(),
               "train_doc_lengths.i32": hashlib.sha256(lens).hexdigest()}
        if got != {k: stage1_sha[k] for k in got}:
            raise SystemExit("replayed stream does not reproduce the Stage 1 corpus: %s" % got)
        rep["stage1_docs"], rep["stage1_tokens"] = len(lengths), int(total)
        print("Stage 1 corpus reproduced (%d docs, %d tokens); extending" % (len(lengths), total), flush=True)

    for text in texts:
        batch.append(text)
        if len(batch) == batch_size:
            flush()
            batch = []
            if done:
                break
    else:
        if batch:
            flush()
    if n1 is None:
        raise SystemExit("stream ended before the Stage 1 corpus was reproduced")
    if total < total_tokens:
        raise SystemExit("training source exhausted at %d tokens (< %d)" % (total, total_tokens))
    rep.update(total_docs=len(lengths), total_tokens=int(total), target_tokens=int(total_tokens),
               ngram=ngrams.N, eval_windows_checked=None)
    return np.concatenate(pieces), np.asarray(lengths, dtype=np.int32), rep


def files_match(out):
    m = out / "manifest.json"
    if not m.exists():
        return False
    man = json.loads(m.read_text())
    return all((out / n).exists() and B.sha256_file(out / n) == man.get(n) for n in FILES)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--results", required=True, help="Stage 1 results/r1")
    p.add_argument("--out", required=True)
    p.add_argument("--tokenizer", required=True)
    p.add_argument("--total-tokens", type=int, default=220_000_000)
    args = p.parse_args()
    res, out = Path(args.results), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if files_match(out):
        print("EXTENDED DATA PRESENT AND MATCHES ITS MANIFEST", flush=True)
        return 0
    s1 = json.loads((res / "manifest.json").read_text())
    lock = json.loads((res / "data_lock.json").read_text())
    if B.sha256_file(res / "eval_sets.jsonl") != s1["eval_sets.jsonl"]:
        raise SystemExit("Stage 1 eval_sets.jsonl differs from its manifest")
    if B.sha256_file(args.tokenizer) != B.TOKENIZER_SHA256:
        raise SystemExit("tokenizer differs from the pinned Parcae tokenizer")
    rows = [json.loads(x) for x in open(res / "eval_sets.jsonl", encoding="utf-8")]
    eval_set = eval_ngram_set(rows)
    from huggingface_hub import HfApi, HfFileSystem
    from tokenizers import Tokenizer
    tok = Tokenizer.from_file(args.tokenizer)
    src = B.resolve(HfApi(), "train", B.SOURCES["train"], lock["sources"]["train"])
    texts = B.hub_texts(HfFileSystem(), src, B.SOURCES["train"]["fmt"], B.SOURCES["train"]["column"])
    tokens, lengths, rep = extend(
        texts, lambda ts: [e.ids for e in tok.encode_batch(ts, add_special_tokens=False)],
        lock["params"]["train_tokens"], s1, eval_set, args.total_tokens)
    rep["eval_windows_checked"] = len(rows)
    (out / FILES[0]).write_bytes(tokens.astype("<u2").tobytes())
    (out / FILES[1]).write_bytes(lengths.astype("<i4").tobytes())
    shutil.copyfile(res / "eval_sets.jsonl", out / "eval_sets.jsonl")
    (out / "extension.json").write_text(json.dumps(rep, indent=1) + "\n")
    man = {n: B.sha256_file(out / n) for n in FILES}
    man["extension.json"] = B.sha256_file(out / "extension.json")
    (out / "manifest.json").write_text(json.dumps(man, indent=1, sort_keys=True) + "\n")
    print(json.dumps(rep, indent=1))
    print("EXTENDED DATA BUILT (Stage 1 part reproduced; extension checked against all eval windows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
