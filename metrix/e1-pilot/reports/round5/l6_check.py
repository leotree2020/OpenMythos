#!/usr/bin/env python3
"""Round 5, task 5: leakage check L6 (protocol section 3; SPLIT_MANIFEST.json leakage_checks.L6_general_text),
DEV part: word 13-grams shared between the anchor text and the general DEV windows. Limit 0.

General DEV windows (protocol 2.7, DATA_MANIFEST.json general_text): rows of
research/mini_mythos/stage1/results/r1/eval_sets.jsonl with split == "dev", first 25 per domain (books, c4,
fineweb, wikitext) in file order; tokens decoded with SandyResearch/parcae-tokenizer@6247b5d0 (special tokens
skipped), re-tokenized with the protocol tokenizer, cut to the first 256 tokens and decoded.
Rows with split == "test" are counted and skipped: they are not decoded (general_test is generated only after
PROTOCOL_FROZEN).
Anchor text: the 512 texts written by reports/round2/anchor_check.py (--anchor).

The protocol does not define "word". Three definitions are counted, each per document (no n-gram crosses a
document boundary); the check passes only if all three give 0 shared 13-grams:
  ws   text.split(), case-sensitive
  w    re.findall(r"\\w+", text.casefold()): case-insensitive, punctuation dropped
  tok  token ids of the protocol tokenizer (the unit used by Stage 1's own 13-gram filter), for reference
Shared counts for n = 1..13 are printed for each definition to show the counting is not vacuous.
Tokenizer files only; no model weights.

  python l6_check.py --eval-sets EVAL_SETS.jsonl --parcae-tokenizer TOKENIZER.json --data-lock DATA_LOCK.json \
      --tokenizer-dir QWEN_DIR --anchor ANCHOR.json --general-out GENERAL_DEV.json
"""
import argparse
import collections
import hashlib
import json
import re
import sys

DOMAINS = ("books", "c4", "fineweb", "wikitext")
PER_DOMAIN = 25
WINDOW_TOKENS = 256
N = 13


def sha256_file(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def canonical_sha256(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
                                     allow_nan=False).encode("utf-8")).hexdigest()


def ngrams(seq, n):
    return {tuple(seq[i:i + n]) for i in range(len(seq) - n + 1)}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--eval-sets", required=True)
    p.add_argument("--parcae-tokenizer", required=True, help="tokenizer.json of SandyResearch/parcae-tokenizer")
    p.add_argument("--data-lock", required=True, help="Stage 1 data_lock.json (pins the parcae tokenizer sha256)")
    p.add_argument("--tokenizer-dir", required=True)
    p.add_argument("--anchor", required=True)
    p.add_argument("--general-out", required=True)
    a = p.parse_args()

    got, pinned = sha256_file(a.parcae_tokenizer), json.load(open(a.data_lock, encoding="utf-8"))["tokenizer_sha256"]
    print("parcae tokenizer.json sha256 %s, Stage 1 data_lock tokenizer_sha256 %s, match %s" % (got, pinned, got == pinned))
    if got != pinned:
        sys.exit("parcae tokenizer does not match its pin")
    from tokenizers import Tokenizer
    from transformers import AutoTokenizer
    ptok = Tokenizer.from_file(a.parcae_tokenizer)
    qtok = AutoTokenizer.from_pretrained(a.tokenizer_dir)

    rows_by_split = collections.Counter()
    kept = collections.defaultdict(list)
    with open(a.eval_sets, encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            rows_by_split[r["split"]] += 1
            if r["split"] != "dev" or len(kept[r["domain"]]) >= PER_DOMAIN:
                continue
            kept[r["domain"]].append(r)
    print("eval_sets rows by split:", dict(sorted(rows_by_split.items())), "| test rows decoded: 0")
    print("dev windows kept per domain:", {d: len(kept[d]) for d in DOMAINS}, "| other domains:",
          sorted(set(kept) - set(DOMAINS)))
    if sorted(kept) != sorted(DOMAINS) or any(len(kept[d]) != PER_DOMAIN for d in DOMAINS):
        sys.exit("general DEV selection does not give 25 windows for each of the 4 domains")

    general = []
    for d in DOMAINS:
        for r in kept[d]:
            text_p = ptok.decode(r["tokens"], skip_special_tokens=True)
            ids = qtok.encode(text_p, add_special_tokens=False)[:WINDOW_TOKENS]
            general.append({"domain": d, "doc_id": r["doc_id"], "parcae_tokens": len(r["tokens"]),
                            "ids": ids, "text": qtok.decode(ids)})
    lens = collections.Counter(len(g["ids"]) for g in general)
    print("general DEV windows: %d; protocol-tokenizer lengths: %s" % (len(general), dict(sorted(lens.items()))))
    print("general DEV canonical sha256 (list of window texts, domain order books, c4, fineweb, wikitext): %s" %
          canonical_sha256([g["text"] for g in general]))
    print("general DEV canonical sha256 (list of token-id lists, same order): %s" %
          canonical_sha256([g["ids"] for g in general]))
    with open(a.general_out, "w", encoding="utf-8") as fh:
        json.dump(general, fh, ensure_ascii=False)

    anchor = json.load(open(a.anchor, encoding="utf-8"))["texts"]
    print("anchor texts: %d; canonical sha256 %s" % (len(anchor), canonical_sha256(anchor)))

    units = {
        "ws": lambda t: t.split(),
        "w": lambda t: re.findall(r"\w+", t.casefold()),
        "tok": lambda t: qtok.encode(t, add_special_tokens=False),
    }
    result = {}
    for name, split in units.items():
        a_seqs = [split(t) for t in anchor]
        g_seqs = [split(g["text"]) for g in general]
        counts = []
        for n in range(1, N + 1):
            a_set = set().union(*(ngrams(s, n) for s in a_seqs))
            g_set = set().union(*(ngrams(s, n) for s in g_seqs))
            counts.append(len(a_set & g_set))
        longest = max([n for n in range(1, N + 1) if counts[n - 1]], default=0)
        result[name] = counts[N - 1]
        print("unit %-3s | units: anchor %d, general %d | shared n-grams n=1..13: %s | longest shared n <= 13: %d" % (
            name, sum(map(len, a_seqs)), sum(map(len, g_seqs)), counts, longest))
        if counts[N - 1]:
            g13 = set().union(*(ngrams(s, N) for s in g_seqs))
            for gram in sorted(set().union(*(ngrams(s, N) for s in a_seqs)) & g13)[:5]:
                print("  shared 13-gram:", json.dumps(list(gram), ensure_ascii=False))
    print("L6 (DEV part) shared word 13-grams: ws %d, w %d; token 13-grams (reference): %d; limit 0" % (
        result["ws"], result["w"], result["tok"]))
    ok = not any(result.values())
    print("RESULT:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
