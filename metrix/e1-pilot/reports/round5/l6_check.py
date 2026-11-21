#!/usr/bin/env python3
"""Round 5, task 5; changed in round 6, task 2: leakage check L6 (protocol section 3;
SPLIT_MANIFEST.json leakage_checks.L6_general_text), DEV part: word 13-grams shared between the anchor text and
the general DEV windows. Limit 0.

General DEV windows (protocol 2.7, DATA_MANIFEST.json general_text): rows of
research/mini_mythos/stage1/results/r1/eval_sets.jsonl with split == "dev", first 25 per domain (books, c4,
fineweb, wikitext) in file order; tokens decoded with SandyResearch/parcae-tokenizer@6247b5d0 (special tokens
skipped), re-tokenized with the protocol tokenizer, at most the first 256 tokens kept (a shorter window is kept
at full length) and decoded. The sha256 of eval_sets.jsonl and of the parcae tokenizer.json must equal
DATA_MANIFEST.json general_text.source_file_sha256 and general_text.decode_tokenizer_json_sha256.
No TEST data is read (protocol section 3: decoding the content of a test row, or computing anything from it):
the split field of every row is read with HEAD (the row prefix written by
research/mini_mythos/stage1/build_data.py: "domain", then "split"); only dev rows are parsed as JSON, and only
the kept dev rows are decoded.
Decoded rows are counted by split; the test count is printed and must be 0.
Anchor text: the 512 texts written by reports/round2/anchor_check.py (--anchor).

Units, each per document (no n-gram crosses a document boundary):
  ws   str.split(), case-sensitive: the protocol's "word" (round 6, item 1a); the check passes only if 0
  w    re.findall(r"\\w+", text.casefold()): case-insensitive, punctuation dropped; report only
  tok  token ids of the protocol tokenizer (the unit used by Stage 1's own 13-gram filter); report only
Shared counts for n = 1..13 are printed for each unit to show the counting is not vacuous.
Tokenizer files only; no model weights.

  python l6_check.py --eval-sets EVAL_SETS.jsonl --parcae-tokenizer TOKENIZER.json --manifest DATA_MANIFEST.json \
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
JUDGED = "ws"                      # the protocol's "word": str.split() (round 6, item 1a)
HEAD = re.compile(r'\{"domain": "[^"\\]*", "split": "([^"\\]*)", ')   # group 1: the split field only


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
    p.add_argument("--manifest", required=True, help="DATA_MANIFEST.json (pins both sha256 values)")
    p.add_argument("--tokenizer-dir", required=True)
    p.add_argument("--anchor", required=True)
    p.add_argument("--general-out", required=True)
    a = p.parse_args()

    gt = json.load(open(a.manifest, encoding="utf-8"))["general_text"]
    for label, path, key in (("eval_sets.jsonl", a.eval_sets, "source_file_sha256"),
                             ("parcae tokenizer.json", a.parcae_tokenizer, "decode_tokenizer_json_sha256")):
        got = sha256_file(path)
        print("%s sha256 %s, DATA_MANIFEST general_text.%s %s, match %s" % (label, got, key, gt[key], got == gt[key]))
        if got != gt[key]:
            sys.exit("%s does not match its pin" % label)
    from tokenizers import Tokenizer
    from transformers import AutoTokenizer
    ptok = Tokenizer.from_file(a.parcae_tokenizer)
    qtok = AutoTokenizer.from_pretrained(a.tokenizer_dir)

    rows_by_split = collections.Counter()
    kept = collections.defaultdict(list)
    with open(a.eval_sets, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            m = HEAD.match(line)
            if m is None:
                sys.exit("eval_sets.jsonl line %d does not start with the domain and split fields" % lineno)
            split = m.group(1)
            rows_by_split[split] += 1
            if split != "dev":
                continue
            r = json.loads(line)
            if r["split"] != split:
                sys.exit("eval_sets.jsonl line %d: parsed split differs from the matched field" % lineno)
            if len(kept[r["domain"]]) < PER_DOMAIN:
                kept[r["domain"]].append(r)
    print("eval_sets rows by split:", dict(sorted(rows_by_split.items())))
    print("dev windows kept per domain:", {d: len(kept[d]) for d in DOMAINS}, "| other domains:",
          sorted(set(kept) - set(DOMAINS)))
    if sorted(kept) != sorted(DOMAINS) or any(len(kept[d]) != PER_DOMAIN for d in DOMAINS):
        sys.exit("general DEV selection does not give 25 windows for each of the 4 domains")

    decoded_by_split = collections.Counter()

    def decode_parcae(r):
        decoded_by_split[r["split"]] += 1
        return ptok.decode(r["tokens"], skip_special_tokens=True)

    general = []
    for d in DOMAINS:
        for r in kept[d]:
            text_p = decode_parcae(r)
            ids = qtok.encode(text_p, add_special_tokens=False)[:WINDOW_TOKENS]
            general.append({"domain": d, "doc_id": r["doc_id"], "parcae_tokens": len(r["tokens"]),
                            "ids": ids, "text": qtok.decode(ids)})
    print("rows decoded by split: %s | test rows decoded: %d" % (dict(sorted(decoded_by_split.items())),
                                                                 decoded_by_split["test"]))
    if set(decoded_by_split) != {"dev"}:
        sys.exit("rows other than dev rows were decoded")
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
    for name, units_of in units.items():
        a_seqs = [units_of(t) for t in anchor]
        g_seqs = [units_of(g["text"]) for g in general]
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
    print("L6 (DEV part) shared word 13-grams (word = str.split(), unit %s): %d; limit 0" % (JUDGED, result[JUDGED]))
    print("report only, no limit: unit w 13-grams %d; Qwen token 13-grams (unit tok) %d" % (result["w"], result["tok"]))
    ok = result[JUDGED] == 0
    print("RESULT:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


def run_guarded(main):
    """Round 6, task 2: on an exception, or on an exit that comes before the RESULT line (sys.exit("message"),
    an argparse error), print RESULT: FAIL and exit non-zero. Exit codes 0 and 1 raised by main() pass through."""
    import sys
    import traceback
    try:
        main()
    except SystemExit as e:
        if e.code is None or (type(e.code) is int and e.code in (0, 1)):
            raise
        sys.stdout.flush()
        if type(e.code) is not int:
            print(e.code, file=sys.stderr)
            sys.stderr.flush()
        print("RESULT: FAIL")
        sys.exit(e.code if type(e.code) is int else 1)
    except BaseException:
        sys.stdout.flush()
        traceback.print_exc()
        sys.stderr.flush()
        print("RESULT: FAIL")
        sys.exit(1)


if __name__ == "__main__":
    run_guarded(main)
