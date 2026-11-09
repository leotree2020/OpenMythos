#!/usr/bin/env python3
"""Compare two eval_sets.jsonl files domain by domain (rows, order, tokens).

  python compare_sets.py OLD/eval_sets.jsonl NEW/eval_sets.jsonl --expect-changed books
Exit 0 only if every domain not listed in --expect-changed is identical.
"""
import argparse
import json
import sys


def load(path):
    out = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            out.setdefault(r["domain"], []).append((r["split"], r["doc_id"], r["text_sha256"], tuple(r["tokens"])))
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("old")
    p.add_argument("new")
    p.add_argument("--expect-changed", default="")
    args = p.parse_args()
    old, new = load(args.old), load(args.new)
    changed_ok = set(filter(None, args.expect_changed.split(",")))
    bad = False
    for domain in sorted(set(old) | set(new)):
        same = old.get(domain) == new.get(domain)
        print("%-10s %s" % (domain, "identical" if same else "CHANGED"))
        if not same and domain not in changed_ok:
            bad = True
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
