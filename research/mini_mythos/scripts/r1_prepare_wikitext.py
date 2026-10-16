#!/usr/bin/env python3
"""Prepare separate real-text train/validation files from WikiText-2.

Downloads public dataset only when explicitly run in the user's environment.
Output bytes and metadata stay in ignored results/, never committed automatically.
"""
import argparse
import hashlib
from pathlib import Path
import json

from common import atomic_json, get_repo


DATASET_ID = "Salesforce/wikitext"
CONFIG = "wikitext-2-raw-v1"


def select_documents(rows, max_documents):
    """Preserve source order, skip empty/markup-only entries."""
    if max_documents < 1:
        raise ValueError("max_documents must be positive")
    docs = []
    for row in rows:
        value = row.get("text")
        if not isinstance(value, str):
            raise ValueError("Dataset entry missing string text")
        text = value.strip()
        if len(text) >= 16:
            docs.append(text)
        if len(docs) == max_documents:
            break
    if not docs:
        raise ValueError("No eligible documents in dataset split")
    return docs


def write_text(path, docs):
    text = "\n\n".join(docs) + "\n"
    data = text.encode("utf-8")
    path.write_bytes(data)
    return {
        "path": str(path),
        "bytes": len(data),
        "documents": len(docs),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", default=".")
    ap.add_argument("--revision", default="main",
                    help="HF dataset git revision. Pin a commit SHA for strict reproduction.")
    ap.add_argument("--train-docs", type=int, default=2000)
    ap.add_argument("--validation-docs", type=int, default=300)
    ap.add_argument("--out-dir", default="research/mini_mythos/results/r1/data")
    args = ap.parse_args()
    if args.train_docs < 1 or args.validation_docs < 1:
        ap.error("document limits must be positive")
    root = get_repo(args.repo)
    out = Path(args.out_dir).resolve()
    if not out.is_relative_to(root / "research/mini_mythos/results"):
        ap.error("output directory must be under research/mini_mythos/results")
    out.mkdir(parents=True, exist_ok=True)

    try:
        from datasets import load_dataset
    except ImportError as exc:
        raise SystemExit("Install the project's 'datasets' dependency first") from exc

    manifests = {}
    for split, limit in (("train", args.train_docs), ("validation", args.validation_docs)):
        print(f"Fetching {DATASET_ID} / {CONFIG} / {split} at {args.revision}", flush=True)
        stream = load_dataset(
            DATASET_ID, name=CONFIG, split=split,
            streaming=True, revision=args.revision
        )
        docs = select_documents(stream, limit)
        manifests[split] = write_text(out / f"{split}.txt", docs)

    if manifests["train"]["sha256"] == manifests["validation"]["sha256"]:
        raise RuntimeError("Training and validation files are identical")
    manifest = {
        "source": DATASET_ID, "config": CONFIG, "revision_requested": args.revision,
        "revision_warning": "main is mutable; use immutable dataset commit SHA for exact reruns"
                            if args.revision == "main" else None,
        "content_split": "separate HF train and validation splits; independent document selection",
        "selection": "first N non-empty text entries >=16 characters in stream order",
        "license_note": "Check upstream dataset card and attribution obligations before redistribution",
        "files": manifests,
    }
    atomic_json(out / "manifest.json", manifest)
    print("Prepared:", json.dumps(manifests, ensure_ascii=False, indent=2))
    print("Manifest:", out / "manifest.json")


if __name__ == "__main__":
    main()
