#!/usr/bin/env python3
"""Round 7, item 1g: build train_S.jsonl (protocol 2.6) and candidates.json (protocol 2.5) with the call order
fixed in round 7, write them in canonical form and print their SHA-256.

Inputs: the 160 facts (canonical JSON list from round2/gen_facts.py, canonical sha256 406c8801...) and the
TRAIN templates of SPLIT_MANIFEST.json. No tokenizer, no model, no TEST data (only the four TRAIN templates
are used). Run it twice in separate processes and compare the files byte by byte.

  python gen_s_cands.py --facts FACTS.json --data-manifest DATA_MANIFEST.json \
      --split-manifest SPLIT_MANIFEST.json --out-dir DIR

Fixed call order (protocol 2.5 and 2.6, round 7):
  S, per cell (cells in the order relation x stratum of 2.2): one generator
     r = rng_rule(DATA_SEED, "s-permutation:<relation>:<stratum>"), created once per cell; each attempt starts
     from p = list(range(15)) and calls r.shuffle(p) once; an attempt with a fixed point (p[i] == i) is
     redrawn with the same r. Statement i = TRAIN template with {E} = entity of learned fact i and
     {A} = answer of learned fact p[i] (facts 01..15 of the cell, i = 0..14).
     Record {"fact_id": fact i, "answer_fact_id": fact p[i], "text": statement}; lines in cell order, then i.
  candidates, per fact: pool = answers of the other facts with the same relation, stratum and exposure, in
     fact order; r = rng_rule(CANDIDATE_SEED, "cand:<fact_id>"); d = r.sample(pool, 3); c = [answer] + d;
     r.shuffle(c). candidates.json = {fact_id: c} for all 160 facts.
Files are written in the canonical serialization of protocol section 0 (JSONL: one canonical object per line,
joined by '\\n', one final '\\n'; JSON: the canonical bytes, no final newline), so byte_sha256 equals
canonical_sha256.
"""
import argparse
import hashlib
import json
import os
import random
import sys


def rng_rule(seed, purpose):
    return random.Random(int.from_bytes(hashlib.sha256(("%s:%s" % (seed, purpose)).encode("utf-8")).digest()[:8], "big"))


def canonical(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def build_s(facts, train_tpl, seed):
    cells, out, attempts = {}, [], {}
    for f in facts:
        if f["exposure"] == "learned":
            cells.setdefault((f["relation"], f["stratum"]), []).append(f)
    for (rel, st), group in cells.items():          # insertion order = fact order = cell order of 2.2
        r = rng_rule(seed, "s-permutation:%s:%s" % (rel, st))
        n = 0
        while True:
            p = list(range(len(group)))
            r.shuffle(p)
            n += 1
            if all(p[i] != i for i in range(len(p))):
                break
        attempts["%s/%s" % (rel, st)] = n
        for i, f in enumerate(group):
            g = group[p[i]]
            text = train_tpl[rel].replace("{E}", f["entity"]).replace("{A}", g["answer"])
            out.append({"fact_id": f["fact_id"], "answer_fact_id": g["fact_id"], "text": text})
    return out, attempts


def build_candidates(facts, seed):
    out = {}
    for f in facts:
        pool = [g["answer"] for g in facts
                if g is not f and (g["relation"], g["stratum"], g["exposure"]) == (f["relation"], f["stratum"], f["exposure"])]
        r = rng_rule(seed, "cand:%s" % f["fact_id"])
        c = [f["answer"]] + r.sample(pool, 3)
        r.shuffle(c)
        out[f["fact_id"]] = c
    return out


def checks(facts, s_rows, cands):
    """Self-checks of the generated content; returns a list of problems (empty = all good)."""
    bad = []
    by_id = {f["fact_id"]: f for f in facts}
    learned = [f for f in facts if f["exposure"] == "learned"]
    unread = [f for f in facts if f["exposure"] == "unread"]
    if len(s_rows) != len(learned):
        bad.append("train_S rows %d != learned facts %d" % (len(s_rows), len(learned)))
    if [r["fact_id"] for r in s_rows] != [f["fact_id"] for f in learned]:
        bad.append("train_S row order differs from the learned fact order")
    if sorted(r["answer_fact_id"] for r in s_rows) != sorted(f["fact_id"] for f in learned):
        bad.append("train_S answers are not a permutation of the learned answers")
    for r in s_rows:
        e, a = by_id[r["fact_id"]], by_id[r["answer_fact_id"]]
        if r["fact_id"] == r["answer_fact_id"]:
            bad.append("fixed point %s" % r["fact_id"])
        if (e["relation"], e["stratum"]) != (a["relation"], a["stratum"]):
            bad.append("answer from another cell in %s" % r["fact_id"])
    low = "\n".join(r["text"] for r in s_rows).lower()
    once = [s for f in learned for s in (f["entity"], f["answer"]) if low.count(s.lower()) != 1]
    zero = [s for f in unread for s in (f["entity"], f["answer"]) if low.count(s.lower()) != 0]
    if once:
        bad.append("learned strings not exactly once in train_S: %s" % once)
    if zero:
        bad.append("unread strings in train_S (L3a): %s" % zero)
    if sorted(cands) != sorted(by_id):
        bad.append("candidates keys differ from the 160 fact_ids")
    for fid, c in cands.items():
        f = by_id[fid]
        pool = {g["answer"] for g in facts
                if g is not f and (g["relation"], g["stratum"], g["exposure"]) == (f["relation"], f["stratum"], f["exposure"])}
        if len(c) != 4 or len(set(c)) != 4 or c.count(f["answer"]) != 1 or not set(c) - {f["answer"]} <= pool:
            bad.append("candidate list of %s violates 2.5: %s" % (fid, c))
    return bad


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--facts", required=True)
    p.add_argument("--data-manifest", required=True)
    p.add_argument("--split-manifest", required=True)
    p.add_argument("--out-dir", required=True)
    a = p.parse_args()
    facts_blob = open(a.facts, "rb").read()
    facts = json.loads(facts_blob)
    dm = json.load(open(a.data_manifest, encoding="utf-8"))
    sm = json.load(open(a.split_manifest, encoding="utf-8"))
    want_facts = dm["name_generation"]["expected_facts_canonical_sha256"]
    got_facts = sha256(canonical(facts))
    print("pid %d, PYTHONHASHSEED=%s, python %s" % (os.getpid(), os.environ.get("PYTHONHASHSEED"), sys.version.split()[0]))
    print("facts canonical sha256 %s, expected %s, match %s" % (got_facts, want_facts, got_facts == want_facts))
    if got_facts != want_facts:
        sys.exit("facts do not match the protocol hash")
    train_tpl = {t["relation"]: t["text"] for t in sm["templates"] if t["set"] == "TRAIN"}
    if sorted(train_tpl) != sorted(dm["facts"]["relations"]):
        sys.exit("TRAIN templates do not cover the four relations")
    s_rows, attempts = build_s(facts, train_tpl, dm["seeds"]["DATA_SEED"])
    cands = build_candidates(facts, dm["seeds"]["CANDIDATE_SEED"])
    s_blob = b"".join(canonical(r) + b"\n" for r in s_rows)
    c_blob = canonical(cands)
    os.makedirs(a.out_dir, exist_ok=True)
    for name, blob in (("train_S.jsonl", s_blob), ("candidates.json", c_blob)):
        with open(os.path.join(a.out_dir, name), "wb") as fh:
            fh.write(blob)
    # canonical sha256 recomputed from the parsed files (protocol section 0), independently of the write path
    s_parsed = [json.loads(line) for line in open(os.path.join(a.out_dir, "train_S.jsonl"), encoding="utf-8")]
    c_parsed = json.load(open(os.path.join(a.out_dir, "candidates.json"), encoding="utf-8"))
    s_canon = sha256(b"".join(canonical(r) + b"\n" for r in s_parsed))
    c_canon = sha256(canonical(c_parsed))
    print("S derangement attempts per cell:", json.dumps(attempts))
    print("train_S.jsonl   rows %d, byte_sha256 %s, canonical_sha256 %s" % (len(s_rows), sha256(s_blob), s_canon))
    print("candidates.json facts %d, byte_sha256 %s, canonical_sha256 %s" % (len(cands), sha256(c_blob), c_canon))
    print("first S row:", s_rows[0]["text"], "| first candidates:", json.dumps(cands[facts[0]["fact_id"]], ensure_ascii=False))
    bad = checks(facts, s_rows, cands)
    for b in bad:
        print("PROBLEM:", b)
    print("self-checks: train_S derangement within cell, learned strings exactly once, unread strings 0;"
          " candidates 4 distinct, true answer once, distractors from the 2.5 pool")
    print("RESULT: %s" % ("FAIL" if bad else "PASS"))
    sys.exit(1 if bad else 0)


def run_guarded(main):
    """Same guard as the round 6 check scripts: on an exception, or on an exit before the RESULT line
    (sys.exit("message"), an argparse error), print RESULT: FAIL and exit non-zero."""
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
