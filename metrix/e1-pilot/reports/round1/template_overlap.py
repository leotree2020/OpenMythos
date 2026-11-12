#!/usr/bin/env python3
"""Round 1, task 5: recompute the template checks L1 and L2 from SPLIT_MANIFEST.json alone.

L1: normalized template hashes of the TRAIN, DEV, TEST and Y sets are pairwise disjoint.
L2: Jaccard overlap of word 4-gram sets of normalized templates, every pair of templates from
    different sets; the statistic compared with the limit is the MAXIMUM over those pairs.

  python3 template_overlap.py --split-manifest metrix/e1-pilot/SPLIT_MANIFEST.json
"""
import argparse
import hashlib
import itertools
import json
import re


def normalize(t):
    t = t.replace("{E}", "<ENTITY>").replace("{A}", "<ANSWER>").lower()
    t = re.sub(r"[^a-z0-9<> ]+", " ", t)
    return " ".join(t.split())


def grams(t, n):
    w = normalize(t).split()
    return {tuple(w[i:i + n]) for i in range(len(w) - n + 1)}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--split-manifest", required=True)
    a = p.parse_args()
    m = json.load(open(a.split_manifest, encoding="utf-8"))
    rows = m["templates"]
    limit = m["leakage_checks"]["L2_template_ngram"]["limit"]
    n = int(re.search(r"word (\d+)-gram", m["leakage_checks"]["L2_template_ngram"]["rule"]).group(1))
    print("templates:", len(rows), "| per set:", {s: sum(r["set"] == s for r in rows) for s in ("TRAIN", "DEV", "TEST", "Y")})
    # stored hashes reproduce?
    bad = [r["template_id"] for r in rows if hashlib.sha256(normalize(r["text"]).encode("utf-8")).hexdigest() != r["normalized_sha256"]]
    print("stored normalized_sha256 reproduced:", not bad, bad)
    # L1
    by = {}
    for r in rows:
        by.setdefault(r["normalized_sha256"], set()).add(r["set"])
    cross = [h for h, sets in by.items() if len(sets) > 1]
    print("L1: hashes shared across sets: %d (limit 0) -> %s" % (len(cross), "PASS" if not cross else "FAIL"))
    # L2
    pairs = []
    for x, y in itertools.combinations(rows, 2):
        if x["set"] == y["set"]:
            continue
        gx, gy = grams(x["text"], n), grams(y["text"], n)
        j = len(gx & gy) / len(gx | gy) if gx and gy else 0.0
        pairs.append((j, x, y, gx & gy, len(gx), len(gy)))
    js = [t[0] for t in pairs]
    print("L2: word %d-gram Jaccard over %d cross-set pairs: max %.4f, mean %.6f, pairs > 0: %d, limit (max) %.2f -> %s" % (
        n, len(pairs), max(js), sum(js) / len(js), sum(j > 0 for j in js), limit, "PASS" if max(js) <= limit else "FAIL"))
    for j, x, y, shared, nx, ny in sorted(pairs, key=lambda t: -t[0]):
        if j == 0:
            break
        print("  %.4f  %s %r (%d grams)  vs  %s %r (%d grams); shared: %s" % (
            j, x["template_id"], normalize(x["text"]), nx, y["template_id"], normalize(y["text"]), ny, sorted(shared)))
    short = [r["template_id"] for r in rows if not grams(r["text"], n)]
    print("templates with fewer than %d words (no %d-gram, Jaccard 0 by definition): %s" % (n, n, short))
    # sensitivity: the same statistic with 3-grams and 2-grams (report only)
    for k in (3, 2):
        s = []
        for x, y in itertools.combinations(rows, 2):
            if x["set"] != y["set"]:
                gx, gy = grams(x["text"], k), grams(y["text"], k)
                s.append(len(gx & gy) / len(gx | gy) if gx and gy else 0.0)
        print("  sensitivity, word %d-grams: max %.4f, mean %.6f, pairs > 0: %d" % (k, max(s), sum(s) / len(s), sum(v > 0 for v in s)))


if __name__ == "__main__":
    main()
