#!/usr/bin/env python3
"""Round 2, task 5: leakage check L3 extended to arm A.

Builds the anchor text exactly as protocol 2.7 says (pinned FineWeb-Edu shard, sha256-checked; first 512
documents in file order with at least 600 characters; each cut to its first 128 tokens of the pinned
tokenizer and decoded), then counts, case-insensitive substring, in those 512 texts:
  L3a  every unread entity and every unread answer   (limit 0, unchanged)
  L3b  every learned answer                           (limit 0, new: arm A sees no learned answer twice)
  report only: learned entities.
The facts come from FACTS.json (gen_facts.py). The anchor texts are written to --anchor-out (scratch).

  python anchor_check.py --manifest DATA_MANIFEST.json --tokenizer-dir DIR --facts FACTS.json \
      --cache-dir DIR --anchor-out ANCHOR.json
"""
import argparse
import hashlib
import json
import os


def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", required=True)
    p.add_argument("--tokenizer-dir", required=True)
    p.add_argument("--facts", help="facts JSON from gen_facts.py; without it only the anchor text is built")
    p.add_argument("--cache-dir", required=True)
    p.add_argument("--anchor-out", required=True)
    a = p.parse_args()
    dm = json.load(open(a.manifest, encoding="utf-8"))
    src = dm["anchor_text"]
    repo, rest = src["source"].split("@", 1)
    commit, _, tail = rest.partition(", ")
    fname = tail.split(" ")[0]
    want_sha = tail.split("sha256 ")[1].rstrip(")")
    from huggingface_hub import hf_hub_download
    path = hf_hub_download(repo, fname, repo_type="dataset", revision=commit, local_dir=a.cache_dir)
    got = file_sha256(path)
    print("anchor source: %s@%s %s" % (repo, commit, fname))
    print("file sha256 %s, pinned %s, match %s" % (got, want_sha, got == want_sha))
    if got != want_sha:
        raise SystemExit("anchor source does not match its pin")
    import pyarrow.parquet as pq
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(a.tokenizer_dir)
    docs, seen = [], 0
    for batch in pq.ParquetFile(path).iter_batches(columns=["text"], batch_size=256):
        for text in batch.column(0).to_pylist():
            seen += 1
            if isinstance(text, str) and len(text) >= 600:
                docs.append(text)
                if len(docs) == 512:
                    break
        if len(docs) == 512:
            break
    texts = [tok.decode(tok.encode(d, add_special_tokens=False)[:128]) for d in docs]
    with open(a.anchor_out, "w", encoding="utf-8") as fh:
        json.dump({"source": src["source"], "documents_read": seen, "texts": texts}, fh, ensure_ascii=False)
    blob = json.dumps(texts, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    print("documents read %d, kept %d, anchor texts canonical sha256 %s, total chars %d" % (
        seen, len(texts), hashlib.sha256(blob).hexdigest(), sum(len(t) for t in texts)))
    if not a.facts:
        return
    low = [t.lower() for t in texts]
    facts = json.load(open(a.facts, encoding="utf-8"))

    def hits(strings):
        out = {}
        for s in strings:
            n = sum(t.count(s.lower()) for t in low)
            if n:
                out[s] = n
        return out
    groups = {"L3a unread entities": [f["entity"] for f in facts if f["exposure"] == "unread"],
              "L3a unread answers": [f["answer"] for f in facts if f["exposure"] == "unread"],
              "L3b learned answers": [f["answer"] for f in facts if f["exposure"] == "learned"],
              "report only: learned entities": [f["entity"] for f in facts if f["exposure"] == "learned"]}
    fail = False
    for name, strings in groups.items():
        h = hits(strings)
        limited = not name.startswith("report")
        if limited and h:
            fail = True
        print("%-32s strings %3d, occurrences %d, strings found %d %s%s" % (
            name, len(strings), sum(h.values()), len(h), json.dumps(h, ensure_ascii=False) if h else "",
            "" if not limited else ("  -> limit 0: %s" % ("FAIL" if h else "PASS"))))
    print("L3 (a + b):", "FAIL" if fail else "PASS")
    raise SystemExit(1 if fail else 0)


if __name__ == "__main__":
    main()
