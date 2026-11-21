#!/usr/bin/env python3
"""Round 6, task 2: inputs that show which unit decides the L6 verdict of reports/round5/l6_check.py.

Writes two modified copies of the anchor JSON (scratch only; the anchor text of the protocol is not changed):
  ws13      anchor document 0 + "\\n" + the first 13 str.split() words of general DEV window 0:
            one shared word 13-gram, so l6_check.py must print RESULT: FAIL and exit 1.
  tok_only  anchor document 0 + "\\n" + the first 12 str.split() words of a general DEV window whose words 2..12
            have at least 13 Qwen tokens: shared Qwen-token 13-grams but no shared word 13-gram, so l6_check.py
            must report a token 13-gram count > 0 and still print RESULT: PASS (round 6, item 1a).
Only DEV windows are used (the --general file written by l6_check.py). Tokenizer only; no model weights.

  python l6_judgment_demo.py --anchor ANCHOR.json --general GENERAL_DEV.json --tokenizer-dir QWEN_DIR --out-dir DIR
"""
import argparse
import json
import os


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--anchor", required=True)
    p.add_argument("--general", required=True)
    p.add_argument("--tokenizer-dir", required=True)
    p.add_argument("--out-dir", required=True)
    a = p.parse_args()
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(a.tokenizer_dir)
    anchor = json.load(open(a.anchor, encoding="utf-8"))
    general = json.load(open(a.general, encoding="utf-8"))

    def write(name, extra):
        out = dict(anchor, texts=[anchor["texts"][0] + "\n" + extra] + anchor["texts"][1:])
        path = os.path.join(a.out_dir, "anchor_%s.json" % name)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(out, fh, ensure_ascii=False)
        print("%s: appended %d str.split() words to anchor document 0 -> %s" % (name, len(extra.split()), path))

    write("ws13", " ".join(general[0]["text"].split()[:13]))
    for k, g in enumerate(general):
        words = g["text"].split()[:12]
        n_tok = len(tok.encode(" " + " ".join(words[1:]), add_special_tokens=False))
        if len(words) == 12 and n_tok >= 13:
            print("tok_only: general DEV window %d (%s); Qwen tokens of words 2..12: %d" % (k, g["doc_id"], n_tok))
            write("tok_only", " ".join(words))
            return
    raise SystemExit("no general DEV window gives 13 Qwen tokens in words 2..12")


if __name__ == "__main__":
    main()
