#!/usr/bin/env python3
"""Round 2, task 3: token ratio of the Y corpus to the F corpus (protocol 2.6: [0.80, 1.25]).

Counts the tokens of one pass over the 120 learned facts: F = TRAIN statement + endoftext; Y = the
Y_ENTITY sentence + endoftext + the Y_ANSWER sentence + endoftext. Tokenizer only.

  python y_ratio.py --manifest DATA_MANIFEST.json --split-manifest SPLIT_MANIFEST.json --tokenizer-dir DIR \
      [--label NAME] [--extra-seeds 20]
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import names as NM  # noqa: E402


def ratio(gen, facts, tpl):
    ids = gen.ids
    f_tok = y_tok = 0
    per = {}
    for f in facts:
        if f["exposure"] != "learned":
            continue
        a = len(ids(tpl[(f["relation"], "TRAIN")][0].replace("{E}", f["entity"]).replace("{A}", f["answer"]))) + 1
        b = (len(ids(tpl[(f["relation"], "Y_ENTITY")][0].replace("{E}", f["entity"]))) + 1 +
             len(ids(tpl[(f["relation"], "Y_ANSWER")][0].replace("{A}", f["answer"]))) + 1)
        f_tok += a
        y_tok += b
        r = per.setdefault(f["relation"], [0, 0])
        r[0] += a
        r[1] += b
    return f_tok, y_tok, {k: round(v[1] / v[0], 3) for k, v in sorted(per.items())}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", required=True)
    p.add_argument("--split-manifest", required=True)
    p.add_argument("--tokenizer-dir", required=True)
    p.add_argument("--label", default="")
    p.add_argument("--extra-seeds", type=int, default=20)
    a = p.parse_args()
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(a.tokenizer_dir)
    dm = json.load(open(a.manifest, encoding="utf-8"))
    sm = json.load(open(a.split_manifest, encoding="utf-8"))
    tpl = {}
    for t in sm["templates"]:
        tpl.setdefault((t["relation"], t["kind"]), []).append(t["text"])
    print("[%s] Y templates: %s" % (a.label, json.dumps({r: [tpl[(r, "Y_ENTITY")][0], tpl[(r, "Y_ANSWER")][0]]
                                                         for r in dm["facts"]["relations"]}, ensure_ascii=False)))
    gen = NM.Names(dm, tok)
    seed = dm["seeds"]["DATA_SEED"]
    facts, _ = gen.build(seed)
    f, y, per = ratio(gen, facts, tpl)
    print("[%s] DATA_SEED %d: F %d tokens, Y %d tokens, ratio Y/F %.3f -> %s [0.80, 1.25]; per relation (report only) %s" % (
        a.label, seed, f, y, y / f, "inside" if 0.80 <= y / f <= 1.25 else "OUTSIDE", per))
    rs = []
    for k in range(1, a.extra_seeds + 1):
        fs, _ = gen.build(seed + 1000 * k)
        f2, y2, _ = ratio(gen, fs, tpl)
        rs.append(y2 / f2)
    print("[%s] %d other data seeds: ratio min %.3f, max %.3f, all inside [0.80, 1.25]: %s" % (
        a.label, len(rs), min(rs), max(rs), all(0.80 <= r <= 1.25 for r in rs)))


if __name__ == "__main__":
    main()
