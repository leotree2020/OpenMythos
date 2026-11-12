#!/usr/bin/env python3
"""Round 2, task 4: generate the 160 facts by the protocol's name rules and print their identity.

Writes the facts (entity, answer, fact_id, exposure, relation, stratum) as canonical JSON to --out and
prints SHA-256 of that file and of the canonical per-cell log. No question of any split is built.
Run it twice in separate processes and compare the hashes.

  python gen_facts.py --manifest DATA_MANIFEST.json --tokenizer-dir DIR --out FACTS.json [--anchor ANCHOR.json]
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import names as NM  # noqa: E402


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", required=True)
    p.add_argument("--tokenizer-dir", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--anchor", help="anchor_text JSON from anchor_check.py: names occurring in it are rejected")
    a = p.parse_args()
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(a.tokenizer_dir)
    dm = json.load(open(a.manifest, encoding="utf-8"))
    banned = None
    if a.anchor:
        texts = [t.lower() for t in json.load(open(a.anchor, encoding="utf-8"))["texts"]]
        banned = lambda s: any(s.lower() in t for t in texts)          # noqa: E731
    facts, log = NM.Names(dm, tok).build(banned=banned)
    blob = NM.canonical(facts)
    with open(a.out, "wb") as fh:
        fh.write(blob)
    print("pid %d, PYTHONHASHSEED=%s, anchor rule %s" % (os.getpid(), os.environ.get("PYTHONHASHSEED"), "on" if banned else "off"))
    print("facts %d (learned %d, unread %d), distinct strings %d" % (
        len(facts), sum(f["exposure"] == "learned" for f in facts), sum(f["exposure"] == "unread" for f in facts),
        len({f["entity"] for f in facts} | {f["answer"] for f in facts})))
    print("facts canonical sha256:", NM.sha256(blob))
    print("cell log canonical sha256:", NM.sha256(NM.canonical(log)))
    print("cell log:", json.dumps(log))


if __name__ == "__main__":
    main()
