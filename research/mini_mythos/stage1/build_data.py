#!/usr/bin/env python3
"""Stage 1 data builder: training corpus, dev/test evaluation sets, 13-gram contamination report.

Needs huggingface_hub, pyarrow, numpy and tokenizers==0.23.2 (same as the frozen environment).
Files are streamed from the Hugging Face Hub (only the parts actually read are fetched); every
source is pinned to a commit in data_lock.json together with the files' LFS sha256 and size.

Outputs in --out:
  train_tokens.u16        ~50M training token ids (uint16, no BOS/EOS, documents concatenated)
  train_doc_lengths.i32   length of each training document (int32), sums to the token count
  eval_sets.jsonl         one row per window: domain, split, doc_id, text_sha256, tokens (257 ids)
  contamination.json      per-domain overlap statistics of every examined candidate window
  data_lock.json          sources (repo, commit, files, sha256, size) and selection parameters
  manifest.json           sha256 of every output above (rerun twice: manifests must be identical)

  python build_data.py --out /workspaces/mythos-evidence/stage1/data
"""
import argparse
import gzip
import hashlib
import json
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ngrams  # noqa: E402

WINDOW_TOKENS = 257
MIN_CHARS = 2000
HEADING = re.compile(r"^ = [^=](.*[^=])? = \s*$")   # one top-level " = Title = " line
TOKENIZER_DEFAULT = "/workspaces/mythos-evidence/base_v01/b1/b1-20261101T021657Z/downloads/tokenizer/tokenizer.json"
TOKENIZER_SHA256 = "e0021e26057088d68047dbe6e77e2ba1c9fe9ae45bae3df9d67d48c82405ea77"

# Each source lists candidate (repo, revision, file regex or file list); the first that resolves is used.
SOURCES = {
    "train": {"fmt": "parquet", "column": "text", "candidates": [
        ("SandyResearch/fineweb-edu-shuffled", "main", r"(^|/)sample-100BT/.*\.parquet$")]},
    "fineweb": {"fmt": "parquet", "column": "text", "candidates": [
        ("SandyResearch/fineweb-edu-shuffled", "main", r"(^|/)val/.*\.parquet$")]},
    "c4": {"fmt": "jsonl.gz", "column": "text", "candidates": [
        ("allenai/c4", "main", ["en/c4-validation.00000-of-00008.json.gz"])]},
    "wikitext_dev": {"fmt": "wikitext", "column": "text", "candidates": [
        ("Salesforce/wikitext", "6231e49f19a707241d6b84d9cff60a3a86b85a85",
         ["wikitext-2-raw-v1/test-00000-of-00001.parquet", "wikitext-2-raw-v1/validation-00000-of-00001.parquet"])]},
    "wikitext_test": {"fmt": "wikitext", "column": "text", "candidates": [
        ("Salesforce/wikitext", "6231e49f19a707241d6b84d9cff60a3a86b85a85", r"^wikitext-103-raw-v1/train-.*\.parquet$")]},
    # Books (revised 2026-11-09): dev AND test both from PG-19 train (one stream, disjoint books),
    # so they share one distribution; windows skip the Gutenberg front matter (see book_start).
    "books": {"fmt": "parquet", "column": "text", "candidates": [
        ("emozilla/pg19", "main", r"(^|/)train(/|-)[^/]*\.parquet$"),
        ("deepmind/pg19", "refs/convert/parquet", r"(^|/)(partial-)?train(/|-)[^/]*\.parquet$")]},
}
# Per domain: (dev source, test source); None means "continue the dev stream".
DOMAINS = {"fineweb": ("fineweb", None), "c4": ("c4", None),
           "wikitext": ("wikitext_dev", "wikitext_test"), "books": ("books", None)}
BOOK_START_FRACTION = 0.10   # books: window starts at the first paragraph after 10% of the text
BOOK_SLICE_CHARS = 12000     # tokenize only this much text from the window start (>> 257 tokens)


def book_start(text):
    """Character offset of the first paragraph that begins after BOOK_START_FRACTION of the book,
    i.e. just after a blank line; None if there is no such paragraph. Skips front matter."""
    i = text.find("\n\n", int(len(text) * BOOK_START_FRACTION))
    if i < 0:
        return None
    j = i
    while j < len(text) and text[j] in "\r\n \t":
        j += 1
    return j if j < len(text) else None


WINDOW_START = {"books": book_start}   # other domains: the document start, unchanged


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def wikitext_bodies(lines):
    """Stream article bodies from WikiText raw lines (top-level ' = Title = ' headings)."""
    body, started = [], False
    for line in lines:
        if HEADING.match(line):
            if started:
                yield "".join(body).strip()
            body, started = [], True
        elif started:
            body.append(line)
    if started:
        yield "".join(body).strip()


# ---------------------------------------------------------------- Hugging Face access

def _lfs_sha(entry):
    lfs = getattr(entry, "lfs", None)
    if lfs is None:
        return None
    return lfs.get("sha256") if isinstance(lfs, dict) else getattr(lfs, "sha256", None)


def resolve(api, name, spec, locked=None):
    """Return {repo, revision, commit, files:[{path,size,sha256}]} for a source."""
    tried = []
    candidates = [(locked["repo"], locked["commit"], [f["path"] for f in locked["files"]])] if locked else spec["candidates"]
    for repo, revision, files in candidates:
        try:
            commit = api.dataset_info(repo, revision=revision).sha
            if isinstance(files, str):
                regex = files
                files = sorted(f for f in api.list_repo_files(repo, repo_type="dataset", revision=commit)
                               if re.search(regex, f))
            if not files:
                raise FileNotFoundError("no matching files")
            info = {}
            for k in range(0, len(files), 100):   # one request for ~1800 paths returns 413
                info.update({i.path: i for i in api.get_paths_info(repo, files[k:k + 100], repo_type="dataset",
                                                                    revision=commit)})
            entries = [{"path": f, "size": info[f].size, "sha256": _lfs_sha(info[f])} for f in files]
            result = {"repo": repo, "revision": revision, "commit": commit, "files": entries}
            if locked and [(e["path"], e["size"], e["sha256"]) for e in entries] != \
                    [(e["path"], e["size"], e["sha256"]) for e in locked["files"]]:
                raise SystemExit("%s: remote files differ from data_lock.json" % name)
            return result
        except SystemExit:
            raise
        except Exception as exc:   # try the next candidate, but remember why
            tried.append("%s@%s: %s" % (repo, revision, exc))
    raise SystemExit("%s: no source candidate could be resolved:\n  %s" % (name, "\n  ".join(tried)))


def hub_texts(fs, source, fmt, column):
    """Stream the text column of a resolved source, file by file, row by row."""
    def rows():
        for f in source["files"]:
            path = "datasets/%s@%s/%s" % (source["repo"], source["commit"], f["path"])
            with fs.open(path, "rb") as handle:
                if fmt == "jsonl.gz":
                    with gzip.open(handle, "rt", encoding="utf-8") as lines:
                        for line in lines:
                            yield json.loads(line)[column]
                else:
                    import pyarrow.parquet as pq
                    for batch in pq.ParquetFile(handle).iter_batches(columns=[column], batch_size=64):
                        for value in batch.column(0).to_pylist():
                            if isinstance(value, str):
                                yield value
    return wikitext_bodies(rows()) if fmt == "wikitext" else rows()


# ---------------------------------------------------------------- building blocks

def build_train(texts, encode_batch, target_tokens):
    """Concatenate whole documents (no special tokens) until at least target_tokens."""
    pieces, lengths, total, batch = [], [], 0, []

    def flush():
        nonlocal total
        for ids in encode_batch(batch):
            if not ids:
                continue
            pieces.append(np.asarray(ids, dtype=np.uint16))
            lengths.append(len(ids))
            total += len(ids)
            if total >= target_tokens:
                return True
        return False

    for text in texts:
        batch.append(text)
        if len(batch) == 256:
            if flush():
                break
            batch = []
    else:
        if batch:
            flush()
    if total < target_tokens:
        raise SystemExit("training source exhausted at %d tokens (< %d)" % (total, target_tokens))
    if max(int(p.max()) for p in pieces) >= 2 ** 16:
        raise SystemExit("token id does not fit uint16")
    return np.concatenate(pieces), np.asarray(lengths, dtype=np.int32)


def take_windows(texts, encode, split, target, blocked, seen, domain, examined):
    """Take the first `target` eligible, unseen, clean windows from `texts` (document start, or the
    WINDOW_START rule for that domain).

    `blocked` is a list of sorted hash sets; a window with any 13-gram in any of them is skipped
    (and recorded in `examined` as contaminated)."""
    chosen = []
    for text in texts:
        if len(text) < MIN_CHARS:
            continue
        digest = sha256_bytes(text.encode("utf-8"))
        if digest in seen:
            continue
        start = WINDOW_START.get(domain)
        offset = start(text) if start else 0
        if offset is None:
            continue
        ids = encode(text[offset:offset + BOOK_SLICE_CHARS]) if start else encode(text)
        if len(ids) < WINDOW_TOKENS:
            continue
        seen.add(digest)
        window = ids[:WINDOW_TOKENS]
        stats = [ngrams.overlap(window, s) for s in blocked]
        hits = sum(s[0] for s in stats)
        examined.append({"domain": domain, "split": split, "text_sha256": digest,
                         "train_hits": stats[0][0], "train_coverage": stats[0][2],
                         "other_hits": hits - stats[0][0], "accepted": hits == 0})
        if hits == 0:
            row = {"domain": domain, "split": split, "doc_id": "%s-%s-%03d" % (domain, split, len(chosen)),
                   "text_sha256": digest, "tokens": [int(t) for t in window]}
            if start:
                row["char_offset"] = offset
            chosen.append(row)
            if len(chosen) >= target:
                break
    return chosen


def build(out, open_source, encode, encode_batch, train_tokens, n_dev, n_test, lock_info):
    """Pure pipeline used by main() and the tests. `open_source(name)` returns an iterator of texts."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    tokens, lengths = build_train(open_source("train"), encode_batch, train_tokens)
    (out / "train_tokens.u16").write_bytes(tokens.astype("<u2").tobytes())
    (out / "train_doc_lengths.i32").write_bytes(lengths.astype("<i4").tobytes())
    train_set = ngrams.corpus_set(tokens, lengths)
    del tokens

    rows, examined, seen, streams, shortfall = [], [], set(), {}, {}
    for domain, (dev_src, test_src) in DOMAINS.items():          # phase 1: all dev sets
        streams[domain] = open_source(dev_src)
        dev = take_windows(streams[domain], encode, "dev", n_dev, [train_set], seen, domain, examined)
        rows += dev
        if len(dev) < n_dev:
            shortfall["%s/dev" % domain] = n_dev - len(dev)
    dev_set = np.unique(np.concatenate([ngrams.hashes(r["tokens"]) for r in rows])) if rows else np.zeros(0, np.uint64)
    for domain, (dev_src, test_src) in DOMAINS.items():          # phase 2: tests, clean against train AND all dev
        texts = streams[domain] if test_src is None else open_source(test_src)
        test = take_windows(texts, encode, "test", n_test, [train_set, dev_set], seen, domain, examined)
        rows += test
        if len(test) < n_test:
            shortfall["%s/test" % domain] = n_test - len(test)

    report = {"ngram": ngrams.N, "train_tokens": int(lengths.sum()), "train_docs": len(lengths),
              "train_unique_ngrams": int(len(train_set)), "shortfall": shortfall, "domains": {}}
    for domain in DOMAINS:
        ex = [e for e in examined if e["domain"] == domain]
        hit = [e for e in ex if e["train_hits"] > 0]
        report["domains"][domain] = {
            "examined": len(ex), "with_train_overlap": len(hit),
            "fraction_with_train_overlap": len(hit) / len(ex) if ex else None,
            "mean_train_token_coverage": float(np.mean([e["train_coverage"] for e in ex])) if ex else None,
            "rejected_for_dev_overlap": sum(1 for e in ex if e["other_hits"] > 0 and e["train_hits"] == 0),
            "accepted": {s: sum(1 for r in rows if r["domain"] == domain and r["split"] == s) for s in ("dev", "test")}}
    with open(out / "eval_sets.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    with open(out / "examined.jsonl", "w", encoding="utf-8") as f:
        for e in examined:
            f.write(json.dumps(e) + "\n")
    (out / "contamination.json").write_text(json.dumps(report, indent=1) + "\n")
    lock_path = out / "data_lock.json"
    if lock_info is not None and not lock_path.exists():
        lock_path.write_text(json.dumps(lock_info, indent=1) + "\n")
    names = ["train_tokens.u16", "train_doc_lengths.i32", "eval_sets.jsonl", "examined.jsonl", "contamination.json"]
    manifest = {n: sha256_file(out / n) for n in names}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")
    return report, manifest


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", required=True)
    p.add_argument("--tokenizer", default=TOKENIZER_DEFAULT)
    p.add_argument("--lock", default=None, help="existing data_lock.json to rebuild from (default: OUT/data_lock.json if present)")
    p.add_argument("--train-tokens", type=int, default=50_000_000)
    p.add_argument("--n-dev", type=int, default=100)
    p.add_argument("--n-test", type=int, default=200)
    args = p.parse_args()
    from huggingface_hub import HfApi, HfFileSystem
    from tokenizers import Tokenizer
    import tokenizers

    if tokenizers.__version__ != "0.23.2":
        raise SystemExit("tokenizers %s; need 0.23.2 to match the frozen environment" % tokenizers.__version__)
    if sha256_file(args.tokenizer) != TOKENIZER_SHA256:
        raise SystemExit("tokenizer file differs from the pinned Parcae tokenizer")
    tok = Tokenizer.from_file(args.tokenizer)
    lock_path = Path(args.lock) if args.lock else Path(args.out) / "data_lock.json"
    locked = json.loads(lock_path.read_text()) if lock_path.exists() else None
    if locked and (locked["params"]["train_tokens"], locked["params"]["n_dev"], locked["params"]["n_test"]) != \
            (args.train_tokens, args.n_dev, args.n_test):
        raise SystemExit("parameters differ from data_lock.json")
    api, fs = HfApi(), HfFileSystem()
    resolved = {name: resolve(api, name, spec, locked["sources"][name] if locked else None)
                for name, spec in SOURCES.items()}
    for name, src in resolved.items():
        print("%-14s %s@%s (%d files)" % (name, src["repo"], src["commit"][:12], len(src["files"])), flush=True)
    lock_info = {"sources": resolved, "tokenizer_sha256": TOKENIZER_SHA256, "tokenizers": tokenizers.__version__,
                 "params": {"train_tokens": args.train_tokens, "n_dev": args.n_dev, "n_test": args.n_test,
                            "window_tokens": WINDOW_TOKENS, "min_chars": MIN_CHARS, "ngram": ngrams.N}}

    def open_source(name):
        return hub_texts(fs, resolved[name], SOURCES[name]["fmt"], SOURCES[name]["column"])

    def encode(text):
        return tok.encode(text, add_special_tokens=False).ids

    def encode_batch(texts):
        return [e.ids for e in tok.encode_batch(texts, add_special_tokens=False)]

    report, manifest = build(args.out, open_source, encode, encode_batch, args.train_tokens,
                             args.n_dev, args.n_test, lock_info)
    print(json.dumps(report, indent=1))
    print(json.dumps(manifest, indent=1))
    return 1 if report["shortfall"] else 0


if __name__ == "__main__":
    sys.exit(main())
