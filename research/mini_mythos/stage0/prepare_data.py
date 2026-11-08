#!/usr/bin/env python3
"""Stage 0 data: download two pinned text sources and select document-start texts.

Needs only `huggingface_hub` and `pyarrow` (no torch). Writes into --out:
  data_lock.json   exact repo / commit / file / size / sha256 of every downloaded file
  texts.jsonl      one selected document per line: domain, doc_id, text_sha256, text

Domains
  fineweb   FineWeb-Edu validation shard used by the Parcae authors (in-distribution)
  wikitext  WikiText-2 raw test split, one text per article body (other domain; also
            comparable with the earlier 32-window depth experiment)

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
                 "file": "wikitext-2-raw-v1/test-00000-of-00001.parquet", "column": "text"},
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
    if "file" in spec:
        filename = spec["file"]
    else:
        files = sorted(f for f in api.list_repo_files(spec["repo"], repo_type="dataset", revision=commit)
                       if re.search(spec["file_regex"], f))
        if not files:
            raise SystemExit("%s: no file matches %s at %s" % (name, spec["file_regex"], commit))
        filename = files[0]
    return commit, filename


def read_column(path, column):
    import pyarrow.parquet as pq
    return pq.read_table(path, columns=[column]).column(column).to_pylist()


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", required=True)
    p.add_argument("--fineweb-n", type=int, default=100)
    p.add_argument("--wikitext-n", type=int, default=100)
    args = p.parse_args()
    from huggingface_hub import HfApi, hf_hub_download

    out = Path(args.out)
    (out / "raw").mkdir(parents=True, exist_ok=True)
    lock_path = out / "data_lock.json"
    lock = json.loads(lock_path.read_text()) if lock_path.exists() else None
    api = HfApi()
    new_lock, selected = {}, []
    for name, spec in SOURCES.items():
        if lock:
            commit, filename = lock[name]["commit"], lock[name]["file"]
        else:
            commit, filename = resolve(api, name, spec)
        local = hf_hub_download(spec["repo"], filename, repo_type="dataset", revision=commit,
                                local_dir=str(out / "raw" / name))
        entry = {"repo": spec["repo"], "commit": commit, "file": filename,
                 "size": Path(local).stat().st_size, "sha256": sha256_file(local)}
        if lock and (lock[name]["sha256"], lock[name]["size"]) != (entry["sha256"], entry["size"]):
            raise SystemExit("%s: downloaded bytes differ from data_lock.json" % name)
        new_lock[name] = entry
        rows = read_column(local, spec["column"])
        if name == "wikitext":
            texts = [body for _, body in wikitext_articles(rows)]
            limit = args.wikitext_n
        else:
            texts = [t for t in rows if isinstance(t, str)]
            limit = args.fineweb_n
        chosen = select(texts, limit)
        print("%s: %d rows -> %d candidate texts -> %d selected" % (name, len(rows), len(texts), len(chosen)))
        for i, (digest, text) in enumerate(chosen):
            selected.append({"domain": name, "doc_id": "%s-%03d" % (name, i), "text_sha256": digest, "text": text})

    new_lock["selection"] = {"min_chars": MIN_CHARS, "fineweb_n": args.fineweb_n, "wikitext_n": args.wikitext_n,
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
