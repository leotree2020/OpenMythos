#!/usr/bin/env python3
"""Prepare the previously untouched WikiText-2 *test* split for Gate F.

Must not touch existing train/validation artifacts. Resolves the Hugging Face
dataset revision to an immutable commit SHA before fetching text. Writes one
test.txt and manifest.json in a new results directory; refuses overwrite.
"""
import argparse
import json
from pathlib import Path

from common import atomic_json, get_repo
from r1_prepare_wikitext import CONFIG, DATASET_ID, select_documents, write_text


def validate_test_manifest(manifest):
    """Only accept an explicit separate official test split and pinned SHA."""
    if not isinstance(manifest, dict):
        raise ValueError("Test manifest must be an object")
    if (manifest.get("source") != DATASET_ID or
            manifest.get("config") != CONFIG or
            manifest.get("split") != "test"):
        raise ValueError("Gate F requires the official WikiText-2 test split")
    rev = manifest.get("resolved_revision")
    if not isinstance(rev, str) or len(rev) != 40 or any(
        ch not in "0123456789abcdef" for ch in rev.lower()
    ):
        raise ValueError("Resolved dataset revision must be a 40-char commit SHA")
    info = manifest.get("file")
    if (not isinstance(info, dict) or info.get("documents", 0) < 1 or
            info.get("bytes", 0) < 1 or
            not isinstance(info.get("sha256"), str) or len(info["sha256"]) != 64):
        raise ValueError("Missing or invalid test file provenance")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", default=".")
    p.add_argument("--revision", default="main",
                   help="Resolve main to commit SHA or supply a pinned commit SHA")
    p.add_argument("--test-docs", type=int, default=1200)
    p.add_argument("--out-dir", default="research/mini_mythos/results/r1/gate_f_test")
    a = p.parse_args()
    if a.test_docs != 1200:
        p.error("Gate F preregistered protocol uses --test-docs 1200; do not tune using test data")
    root = get_repo(a.repo)
    out = Path(a.out_dir).resolve()
    if not out.is_relative_to(root / "research/mini_mythos/results"):
        p.error("Test output must be in the project's ignored results directory")
    if out.exists():
        p.error("Test directory already exists; refusing to overwrite or retune test selection")

    try:
        from datasets import load_dataset
        from huggingface_hub import HfApi
    except ImportError as exc:
        raise SystemExit("Install datasets and huggingface_hub dependencies") from exc

    # The dataset repo SHA is captured *before* fetch and then used for fetch.
    info = HfApi().dataset_info(repo_id=DATASET_ID, revision=a.revision)
    pinned = info.sha
    if not isinstance(pinned, str) or len(pinned) != 40:
        raise ValueError("Hugging Face did not resolve a 40-character revision SHA")
    print(f"WikiText-2 test revision pinned to: {pinned}", flush=True)
    records = load_dataset(
        DATASET_ID, name=CONFIG, split="test",
        streaming=True, revision=pinned
    )
    docs = select_documents(records, a.test_docs)
    if len(docs) != a.test_docs:
        raise RuntimeError(f"Only found {len(docs)} eligible test texts, expected {a.test_docs}")
    out.mkdir(parents=True)
    details = write_text(out / "test.txt", docs)
    manifest = {
        "source": DATASET_ID, "config": CONFIG, "split": "test",
        "revision_requested": a.revision,
        "resolved_revision": pinned,
        "selection": "first exactly 1200 stream-order text entries with stripped length >=16",
        "protocol": "R1 Gate F frozen one-shot test; no model tuning, no training on this split",
        "file": details,
    }
    validate_test_manifest(manifest)
    atomic_json(out / "manifest.json", manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    print("Test file:", out / "test.txt")
    print("Manifest:", out / "manifest.json")


if __name__ == "__main__":
    main()
