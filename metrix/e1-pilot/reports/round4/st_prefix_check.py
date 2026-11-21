#!/usr/bin/env python3
"""Round 4, task 2: the token count K' of s_ST (protocol section 5, TRAIN closed-book check).

s_ST(f, c) scores c' = " " + c after prefix(f), the text of the TRAIN statement before the answer. The protocol
now defines K' = K_st(c) = len(encode(" " + c)). This holds only if prefix(f) and c' do not merge at the
boundary. For every learned fact f and every learned answer c of the same cell (the distractor pool of section
2.5, which contains C_f), tokenize prefix(f) + " " + c in one call and check that
  (1) the tokens of prefix(f) are a prefix of the whole sequence,
  (2) the remaining (scored) tokens equal encode(" " + c), so their number is K_st(c),
  (3) that number is the same for every c of the cell.
No TEST template is read; DEV templates are not needed. Tokenizer only; no model weights.

  python st_prefix_check.py --facts FACTS.json --split-manifest SPLIT_MANIFEST.json --tokenizer-dir DIR
"""
import argparse
import collections
import json
import sys


def encode(tok, text):
    return tok.encode(text, add_special_tokens=False)


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
    train_tpl = {}
    for t in sm["templates"]:
        if t["kind"] == "TRAIN":                              # only TRAIN templates are read
            if t["relation"] in train_tpl:
                sys.exit("more than one TRAIN template for %s" % t["relation"])
            train_tpl[t["relation"]] = t["text"]
    for rel, text in sorted(train_tpl.items()):
        if text.count("{A}") != 1 or not text.endswith(" {A}."):
            sys.exit("TRAIN template of %s does not end with ' {A}.': %r" % (rel, text))
        print("TRAIN template %-8s %s" % (rel, json.dumps(text)))

    learned = [f for f in facts if f["exposure"] == "learned"]
    pool = collections.defaultdict(list)
    for f in learned:
        pool[(f["relation"], f["stratum"])].append(f["answer"])

    pairs = merged = differs = 0
    k_by_cell = collections.defaultdict(set)
    example = None
    for f in learned:
        prefix = train_tpl[f["relation"]][:-len(" {A}.")].replace("{E}", f["entity"])
        p_ids = encode(tok, prefix)
        for c in pool[(f["relation"], f["stratum"])]:
            ids = encode(tok, prefix + " " + c)
            scored = ids[len(p_ids):]
            want = encode(tok, " " + c)
            pairs += 1
            if ids[:len(p_ids)] != p_ids:
                merged += 1
                print("MERGED", f["fact_id"], json.dumps(prefix), json.dumps(c))
                continue
            if scored != want:
                differs += 1
                print("DIFFERS", f["fact_id"], json.dumps(c), scored, want)
            k_by_cell[(f["relation"], f["stratum"])].add(len(scored))
            if example is None and c == f["answer"]:
                example = (f, prefix, ids, len(p_ids))
    print("learned facts: %d; (fact, same-cell learned answer) pairs: %d" % (len(learned), pairs))
    print("pairs where the tokens of prefix(f) are not a prefix of the whole sequence: %d" % merged)
    print("pairs where the scored tokens != encode(' ' + c): %d" % differs)
    print("K' per cell:", {"%s/%s" % k: sorted(v) for k, v in sorted(k_by_cell.items())})
    print("cells with more than one K': %d" % sum(len(v) > 1 for v in k_by_cell.values()))
    f, prefix, ids, start = example
    print("example", f["fact_id"], "prefix(f)", json.dumps(prefix), "c", json.dumps(f["answer"]))
    print("  ids", ids, "scored", ids[start:], [tok.decode([i]) for i in ids[start:]])
    ok = merged == 0 and differs == 0 and all(len(v) == 1 for v in k_by_cell.values())
    print("RESULT:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
