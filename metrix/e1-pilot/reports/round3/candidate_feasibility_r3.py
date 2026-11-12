#!/usr/bin/env python3
"""Round 3, task 8: candidate feasibility under the round-3 scoring tokenization.

Pool of a fact = the answers of all facts (itself included) with the same relation, the same stratum, the same
exposure (learned / unread) and the same number of scored answer tokens, where the scored tokens are those of
" " + answer after "The answer is" in scoring_input.py (task 6). A fact needs 3 distractors, i.e. a pool of at
least 4. Each fact's token count is measured with each of its DEV questions (no TEST template is read); the
count must not depend on the question, and must equal K_st = len(encode(" " + answer)) of protocol 2.2.

  python candidate_feasibility_r3.py --facts FACTS.json --split-manifest SPLIT_MANIFEST.json --tokenizer-dir DIR
"""
import argparse
import collections
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scoring_input as SI  # noqa: E402

NEEDED = 4


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--facts", required=True)
    p.add_argument("--split-manifest", required=True)
    p.add_argument("--tokenizer-dir", required=True)
    a = p.parse_args()
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(a.tokenizer_dir)
    facts = json.load(open(a.facts, encoding="utf-8"))
    sm = json.load(open(a.split_manifest, encoding="utf-8"))
    dev = collections.defaultdict(list)
    for t in sm["templates"]:
        if t["kind"] == "DEV":
            dev[t["relation"]].append(t["text"])

    pools = collections.defaultdict(list)
    question_dependent = not_k_st = 0
    for f in facts:
        ks = set()
        for q_t in dev[f["relation"]]:
            _, ids, start = SI.scoring_input(tok, q_t.replace("{E}", f["entity"]), f["answer"])
            ks.add(len(ids) - start)
        if len(ks) != 1:
            question_dependent += 1
            print("token count depends on the question:", f["fact_id"], sorted(ks))
        if ks != {len(SI.encode(tok, " " + f["answer"]))}:
            not_k_st += 1
            print("scored-token count differs from K_st = len(encode(' ' + answer)):", f["fact_id"], sorted(ks))
        pools[(f["relation"], f["stratum"], f["exposure"], min(ks))].append(f["fact_id"])

    print("facts %d; facts whose scored-token count depends on the DEV question: %d" % (len(facts), question_dependent))
    print("facts whose scored-token count differs from K_st: %d" % not_k_st)
    print("pools under the four constraints (relation, stratum, exposure, scored-token count): %d" % len(pools))
    for (rel, st, ex, k), v in sorted(pools.items()):
        print("  %-8s %-7s %-7s K=%d: %2d answers -> %2d possible distractors per fact (3 needed)" % (
            rel, st, ex, k, len(v), len(v) - 1))
    groups = collections.Counter(key[:3] for key in pools)
    split = sorted(g for g, c in groups.items() if c > 1)
    sizes = [len(v) for v in pools.values()]
    short = sorted(key for key, v in pools.items() if len(v) < NEEDED)
    print("(relation, stratum, exposure) groups split over more than one token count: %d %s" % (len(split), split))
    print("minimum pool size: %d" % min(sizes))
    print("pools with fewer than %d answers: %d %s" % (NEEDED, len(short), short))
    ok = not short and not question_dependent and not not_k_st
    print("RESULT:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
