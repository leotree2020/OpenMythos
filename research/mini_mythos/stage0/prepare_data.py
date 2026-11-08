#!/usr/bin/env python3
"""Stage 0 data: download two pinned text sources and select document-start texts.

Needs only `huggingface_hub` and `pyarrow` (no torch). Writes into --out:
  data_lock.json   exact repo / commit / file / size / sha256 of every downloaded file
  texts.jsonl      one selected document per line: domain, doc_id, text_sha256, text

Domains (each up to 100 texts)
  fineweb   FineWeb-Edu validation shard used by the Parcae authors (in-distribution reference)
  wikitext  WikiText-2 raw test + validation splits, one text per article body
  c4        C4 English validation shard 0 (web text, other domain)

Re-running with an existing data_lock.json re-downloads the locked commit/file and
fails if any byte differs. Selection is deterministic (file order, length filter, dedupe).

  python prepare_data.py --out /workspaces/mythos-evidence/stage0/data
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

SOURCES = {
    "fineweb": {"repo": "SandyResearch/fineweb-edu-shuffled", "revision": "main",
                "file_regex": r"(^|/)val/.*\.parquet$", "column": "text"},
    "wikitext": {"repo": "Salesforce/wikitext", "revision": "6231e49f19a707241d6b84d9cff60a3a86b85a85",
                 "files": ["wikitext-2-raw-v1/test-00000-of-00001.parquet",
                           "wikitext-2-raw-v1/validation-00000-of-00001.parquet"], "column": "text"},
    "c4": {"repo": "allenai/c4", "revision": "main",
           "files": ["en/c4-validation.00000-of-00008.json.gz"], "column": "text"},
}
MIN_CHARS = 2000   # ~400 tokens, comfortably more than the 257 needed per window
HEADING = re.compile(r"^ = [^=].*[^=] = \s*$")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def wikitext_articles(lines):
    """Split WikiText raw lines into (title, body) per top-level ' = Title = ' heading."""
    articles, title, body = [], None, []
    for line in lines:
        if HEADING.match(line):
            if title is not None:
                articles.append((title, "".join(body).strip()))
            title, body = line.strip().strip("=").strip(), []
        elif title is not None:
            body.append(line)
    if title is not None:
        articles.append((title, "".join(body).strip()))
    return articles


def select(texts, limit, min_chars=MIN_CHARS):
    """First `limit` distinct texts with at least `min_chars` characters, in input order."""
    seen, chosen = set(), []
    for text in texts:
        if len(text) < min_chars:
            continue
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if digest in seen:
            continue
        seen.add(digest)
        chosen.append((digest, text))
        if len(chosen) >= limit:
            break
    return chosen


def resolve(api, name, spec):
    """Pin a moving revision to its commit and pick the file."""
    info = api.dataset_info(spec["repo"], revision=spec["revision"])
    commit = info.sha
    if "files" in spec:
        return commit, list(spec["files"])
    files = sorted(f for f in api.list_repo_files(spec["repo"], repo_type="dataset", revision=commit)
                   if re.search(spec["file_regex"], f))
    if not files:
        raise SystemExit("%s: no file matches %s at %s" % (name, spec["file_regex"], commit))
    return commit, files[:1]


def read_column(path, column):
    """Rows of one text column from a parquet or json.gz (one JSON object per line) file."""
    if str(path).endswith(".json.gz"):
        import gzip
        with gzip.open(path, "rt", encoding="utf-8") as f:
            return [json.loads(line)[column] for line in f]
    import pyarrow.parquet as pq
    return pq.read_table(path, columns=[column]).column(column).to_pylist()


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", required=True)
    p.add_argument("--n", type=int, default=100, help="texts per domain")
    p.add_argument("--domains", default=",".join(SOURCES))
    args = p.parse_args()
    from huggingface_hub import HfApi, hf_hub_download

    out = Path(args.out)
    (out / "raw").mkdir(parents=True, exist_ok=True)
    lock_path = out / "data_lock.json"
    lock = json.loads(lock_path.read_text()) if lock_path.exists() else None
    api = HfApi()
    new_lock, selected = {}, []
    for name in args.domains.split(","):
        spec = SOURCES[name]
        if lock:
            commit, filenames = lock[name]["commit"], [e["file"] for e in lock[name]["files"]]
        else:
            commit, filenames = resolve(api, name, spec)
        entries, rows = [], []
        for filename in filenames:
            local = hf_hub_download(spec["repo"], filename, repo_type="dataset", revision=commit,
                                    local_dir=str(out / "raw" / name))
            entry = {"file": filename, "size": Path(local).stat().st_size, "sha256": sha256_file(local)}
            if lock and entry not in lock[name]["files"]:
                raise SystemExit("%s: %s differs from data_lock.json" % (name, filename))
            entries.append(entry)
            rows.extend(read_column(local, spec["column"]))
        new_lock[name] = {"repo": spec["repo"], "commit": commit, "files": entries}
        if name == "wikitext":
            texts = [body for _, body in wikitext_articles(rows)]
        else:
            texts = [t for t in rows if isinstance(t, str)]
        chosen = select(texts, args.n)
        print("%s: %d rows -> %d candidate texts -> %d selected" % (name, len(rows), len(texts), len(chosen)))
        for i, (digest, text) in enumerate(chosen):
            selected.append({"domain": name, "doc_id": "%s-%03d" % (name, i), "text_sha256": digest, "text": text})

    new_lock["selection"] = {"min_chars": MIN_CHARS, "n_per_domain": args.n,
                             "rule": "file order, length filter, sha256 dedupe; wikitext = article bodies"}
    if not lock:
        lock_path.write_text(json.dumps(new_lock, indent=1) + "\n")
    with open(out / "texts.jsonl", "w", encoding="utf-8") as f:
        for row in selected:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print("wrote %d texts and %s" % (len(selected), lock_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
