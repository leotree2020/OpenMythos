#!/usr/bin/env python3
"""Books to read: PG-19 from the Stage 1 locked source, disjoint from every evaluation window.

The Stage 1 book windows (dev and test) were taken from the start of the first PG-19 train shard, so
by default the books here come from the LAST shard. In addition every book is checked: its sha256
must not be an evaluation book, and its tokens must share no 13-gram with any of the 1200 evaluation
windows. Each book starts at the first paragraph after 10% of the text (Stage 1 book_start, skips
the Gutenberg front matter). Per book we keep `--book-tokens` tokens to read, then two 257-token
windows right after them that are never read (the book's own held-out tail).

PG-19 texts are hard-wrapped (a newline every ~70 characters): read raw, a model mostly learns to put
newlines everywhere, which then hurts every other kind of text. By default (--unwrap) line breaks
inside a paragraph become spaces; blank lines between paragraphs stay. `--heldout` more books, chosen
the same way and prepared the same way, are never read: two windows from each measure "unseen books"
in the same format.

  python books.py --results STAGE1/results/r1 --tokenizer TOK --out DATA [--books 20 --book-tokens 16384]

Writes DATA/books_tokens.u16 (the read parts, book after book), DATA/books.jsonl (one row per book:
offset in the token file, length, sha256, tail windows), DATA/heldout.jsonl and DATA/manifest.json.
If the manifest matches, nothing is rebuilt.
"""
import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "stage1"))
import build_data as B  # noqa: E402
import ngrams  # noqa: E402

TAIL = 2                      # held-out windows per book
WINDOW = B.WINDOW_TOKENS      # 257


def unwrap(text):
    """Line breaks inside a paragraph -> one space; paragraphs stay separated by one blank line."""
    paras = re.split(r"\n[ \t]*\n+", text)
    return "\n\n".join(re.sub(r"[ \t]*\n[ \t]*", " ", q).strip() for q in paras if q.strip())


def select_books(texts, encode, eval_shas, eval_set, n_books, book_tokens, chars_per_token=8, prepare=None):
    """Pure pipeline: the first n_books eligible books of `texts`. Returns (books, report)."""
    need = book_tokens + TAIL * WINDOW
    books, rep = [], {"examined": 0, "too_short": 0, "eval_book": 0, "eval_overlap": 0, "no_start": 0}
    for text in texts:
        if len(books) >= n_books:
            break
        rep["examined"] += 1
        if len(text) < B.MIN_CHARS:
            rep["too_short"] += 1
            continue
        sha = B.sha256_bytes(text.encode("utf-8"))
        if sha in eval_shas:
            rep["eval_book"] += 1
            continue
        start = B.book_start(text)
        if start is None:
            rep["no_start"] += 1
            continue
        body = text[start:start + need * chars_per_token]
        ids = encode(prepare(body) if prepare else body)
        if len(ids) < need:
            rep["too_short"] += 1
            continue
        ids = np.asarray(ids[:need], dtype=np.uint32)
        if ids.max() >= 2 ** 16:
            raise SystemExit("token id does not fit uint16")
        if eval_set.size and ngrams.member(ngrams.hashes(ids), eval_set).any():
            rep["eval_overlap"] += 1
            continue
        books.append({"sha256": sha, "char_offset": int(start), "read": ids[:book_tokens].astype(np.uint16),
                      "tail": [ids[book_tokens + k * WINDOW: book_tokens + (k + 1) * WINDOW].tolist()
                               for k in range(TAIL)]})
    rep["accepted"] = len(books)
    return books, rep


def write(out, books, rep, meta, heldout=()):
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "heldout.jsonl", "w", encoding="utf-8") as f:
        for i, b in enumerate(heldout):
            f.write(json.dumps({"book": i, "sha256": b["sha256"], "char_offset": b["char_offset"],
                                "windows": [b["read"][:WINDOW].tolist(), b["read"][WINDOW:2 * WINDOW].tolist()]}) + "\n")
    offset = 0
    with open(out / "books.jsonl", "w", encoding="utf-8") as f:
        for i, b in enumerate(books):
            f.write(json.dumps({"book": i, "sha256": b["sha256"], "char_offset": b["char_offset"],
                                "offset": offset, "tokens": int(len(b["read"])), "tail": b["tail"]}) + "\n")
            offset += len(b["read"])
    np.concatenate([b["read"] for b in books]).astype("<u2").tofile(out / "books_tokens.u16")
    man = {n: B.sha256_file(out / n) for n in ("books_tokens.u16", "books.jsonl", "heldout.jsonl")}
    man.update(report=rep, **meta)
    (out / "manifest.json").write_text(json.dumps(man, indent=1, sort_keys=True) + "\n")


def matches(out, params):
    m = out / "manifest.json"
    if not m.exists():
        return False
    man = json.loads(m.read_text())
    return man.get("params") == params and all(
        (out / n).exists() and B.sha256_file(out / n) == man.get(n) for n in ("books_tokens.u16", "books.jsonl",
                                                                              "heldout.jsonl"))


def load(data):
    """(tokens uint16, list of book rows)"""
    data = Path(data)
    tokens = np.fromfile(data / "books_tokens.u16", dtype="<u2")
    with open(data / "books.jsonl", encoding="utf-8") as f:
        rows = [json.loads(x) for x in f]
    if sum(r["tokens"] for r in rows) != len(tokens):
        raise SystemExit("book token file does not match books.jsonl")
    return tokens, rows


def load_heldout(data):
    p = Path(data) / "heldout.jsonl"
    if not p.exists():
        return []
    with open(p, encoding="utf-8") as f:
        return [json.loads(x) for x in f if x.strip()]


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--results", required=True, help="Stage 1 results/r1 (data_lock.json, eval_sets.jsonl)")
    p.add_argument("--tokenizer", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--books", type=int, default=20)
    p.add_argument("--book-tokens", type=int, default=16384)
    p.add_argument("--shard", type=int, default=-1, help="index into the locked PG-19 train files (-1 = last)")
    p.add_argument("--heldout", type=int, default=10, help="further books never read (unseen books, same format)")
    p.add_argument("--no-unwrap", action="store_true", help="keep PG-19's hard line breaks")
    args = p.parse_args()
    out, res = Path(args.out), Path(args.results)
    params = {"books": args.books, "book_tokens": args.book_tokens, "shard": args.shard, "tail_windows": TAIL,
              "heldout": args.heldout, "unwrap": not args.no_unwrap}
    if matches(out, params):
        print("BOOKS PRESENT AND MATCH THEIR MANIFEST")
        return 0
    if B.sha256_file(args.tokenizer) != B.TOKENIZER_SHA256:
        raise SystemExit("tokenizer differs from the pinned Parcae tokenizer")
    lock = json.loads((res / "data_lock.json").read_text())
    rows = [json.loads(x) for x in open(res / "eval_sets.jsonl", encoding="utf-8")]
    eval_shas = {r["text_sha256"] for r in rows}
    eval_set = np.unique(np.concatenate([ngrams.hashes(r["tokens"]) for r in rows]))
    from huggingface_hub import HfApi, HfFileSystem
    from tokenizers import Tokenizer
    tok = Tokenizer.from_file(args.tokenizer)
    src = B.resolve(HfApi(), "books", B.SOURCES["books"], lock["sources"]["books"])
    shard = dict(src, files=[src["files"][args.shard]])
    texts = B.hub_texts(HfFileSystem(), shard, B.SOURCES["books"]["fmt"], B.SOURCES["books"]["column"])
    prepare = None if args.no_unwrap else unwrap
    books, rep = select_books(texts, lambda t: tok.encode(t, add_special_tokens=False).ids, eval_shas, eval_set,
                              args.books + args.heldout, args.book_tokens, prepare=prepare)
    if len(books) < args.books + args.heldout:
        raise SystemExit("only %d eligible books in the shard" % len(books))
    meta = {"params": params, "source": {"repo": src["repo"], "commit": src["commit"], "file": shard["files"][0]}}
    write(out, books[:args.books], rep, meta, heldout=books[args.books:])
    print(json.dumps(rep))
    print("BOOKS BUILT: %d books x %d tokens to read (+%d held-out windows each)" % (len(books), args.book_tokens, TAIL))
    return 0


if __name__ == "__main__":
    sys.exit(main())
