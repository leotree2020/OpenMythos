#!/usr/bin/env python3
"""Round 3, tasks 4 and 7: special-token facts of the pinned tokenizer, and the answer-token check.

Task 4 (tokenizer facts used by the special-token review): bos/eos/pad tokens and ids, whether
add_special_tokens changes encode(), the ids of <|endoftext|>, <|im_start|>, <|im_end|>, and the rendered
generation prompt with enable_thinking=False.

Task 7: for every learned fact and each of its 2 DEV questions (no TEST template is read), compare
  (a) the scored token ids of scoring_input(q, answer)                  (task 6 construction), with
  (b) the token ids of " " + answer inside the tokenized TRAIN statement, located by character offsets.
Reports the number of mismatches (required: 0), the scored-token count per cell (must be constant within a
cell), a cross-check of the renderer against apply_chat_template(..., continue_final_message=True), and one
fully rendered scoring sequence.

Round 5, task 2: PINNED is the 28-token scoring sequence recorded in round 3
(reports/round3/t7_verify_scoring.txt, lines 27-44), written out by hand; scoring_input() must reproduce it
exactly (ids and scored-slice start), and the facts file and the DEV template must still give the same
question and answer. Any difference makes RESULT FAIL. Unlike the renderer cross-check, which passes
enable_thinking=SI.ENABLE_THINKING to both sides and fails for ENABLE_THINKING = True only because the pinned
template puts an empty think block into the final assistant turn, this check compares with fixed ids
(reports/round5/t2_enable_thinking_true_demo.txt).

  python verify_scoring.py --facts FACTS.json --split-manifest SPLIT_MANIFEST.json --tokenizer-dir DIR
"""
import argparse
import collections
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scoring_input as SI  # noqa: E402

# Recorded in round 3 (reports/round3/t7_verify_scoring.txt): fact E1P-L-capital-nat-01, first DEV template.
PINNED = {
    "fact_id": "E1P-L-capital-nat-01",
    "entity": "Krultrouth",
    "answer": "Linnuth",
    "question": "What is the capital of Krultrouth?",
    "input_ids": [151644, 872, 198, 3838, 374, 279, 6722, 315, 16447, 360, 376, 2898, 30, 151645, 198,
                  151644, 77091, 198, 151667, 271, 151668, 271, 785, 4226, 374, 444, 6130, 940],
    "start": 25,
}


def pinned_check(tok, facts, dev_templates):
    """Compare the pinned sequence with what the current code renders; return a list of differences."""
    diffs = []
    f = next((x for x in facts if x["fact_id"] == PINNED["fact_id"]), None)
    if f is None or (f["entity"], f["answer"]) != (PINNED["entity"], PINNED["answer"]):
        diffs.append("facts file: %s gives %r, recorded (%r, %r)" % (
            PINNED["fact_id"], None if f is None else (f["entity"], f["answer"]), PINNED["entity"], PINNED["answer"]))
    q = dev_templates[0].replace("{E}", PINNED["entity"])
    if q != PINNED["question"]:
        diffs.append("first capital DEV template gives %r, recorded %r" % (q, PINNED["question"]))
    _, ids, start = SI.scoring_input(tok, PINNED["question"], PINNED["answer"])
    want = PINNED["input_ids"]
    if ids != want:
        pos = next((i for i, (g, w) in enumerate(zip(ids, want)) if g != w), min(len(ids), len(want)))
        diffs.append("input_ids differ: %d ids rendered, %d recorded; first difference at position %d" % (
            len(ids), len(want), pos))
        diffs.append("rendered ids: %s" % ids)
    if start != PINNED["start"]:
        diffs.append("scored slice start %d, recorded %d" % (start, PINNED["start"]))
    return diffs


def train_answer_ids(tok, statement, answer):
    """Token ids of ' ' + answer in the tokenized statement, found by offsets.

    None if the answer is not preceded by a space or the span is not token-aligned (counted as unaligned).
    """
    enc = tok(statement, add_special_tokens=False, return_offsets_mapping=True)
    cut = statement.rindex(answer)
    lo, hi = cut - 1, cut + len(answer)                       # include the leading space
    if lo < 0 or statement[lo] != " ":
        return None
    idx = [i for i, (s, e) in enumerate(enc["offset_mapping"]) if s < hi and e > lo]
    spans = [enc["offset_mapping"][i] for i in idx]
    if not idx or spans[0][0] != lo or spans[-1][1] != hi:
        return None
    return [enc["input_ids"][i] for i in idx]


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
    tpl = collections.defaultdict(list)
    for t in sm["templates"]:
        if t["kind"] in ("TRAIN", "DEV"):                     # TEST templates are not read
            tpl[(t["relation"], t["kind"])].append(t["text"])

    print("== task 4: tokenizer special tokens")
    print("class", type(tok).__name__)
    print("bos_token %r bos_token_id %r" % (tok.bos_token, tok.bos_token_id))
    print("eos_token %r eos_token_id %r" % (tok.eos_token, tok.eos_token_id))
    print("pad_token %r pad_token_id %r" % (tok.pad_token, tok.pad_token_id))
    for s in ("<|endoftext|>", "<|im_start|>", "<|im_end|>", "<think>", "</think>"):
        print("id of %s: %d" % (s, tok.convert_tokens_to_ids(s)))
    sample = "The capital of Draemor is Kraith."
    print("encode(%r) add_special_tokens=True : %s" % (sample, tok.encode(sample, add_special_tokens=True)))
    print("encode(%r) add_special_tokens=False: %s" % (sample, tok.encode(sample, add_special_tokens=False)))
    print("generation prompt (enable_thinking=False):", json.dumps(SI.chat_prompt(tok, "Q?")))
    print("generation prompt (enable_thinking=True) :", json.dumps(
        tok.apply_chat_template([{"role": "user", "content": "Q?"}], tokenize=False, add_generation_prompt=True,
                                enable_thinking=True)))

    print("== task 7: scored answer ids vs TRAIN statement answer ids (learned facts, DEV questions)")
    n = mismatch = unaligned = renderer_diff = 0
    k_by_cell = collections.defaultdict(set)
    example = None
    for f in facts:
        if f["exposure"] != "learned":
            continue
        st = tpl[(f["relation"], "TRAIN")][0].replace("{E}", f["entity"]).replace("{A}", f["answer"])
        want = train_answer_ids(tok, st, f["answer"])
        if want is None:
            unaligned += 1
            print("UNALIGNED in TRAIN statement:", f["fact_id"], json.dumps(st))
            continue
        for q_t in tpl[(f["relation"], "DEV")]:
            q = q_t.replace("{E}", f["entity"])
            text, ids, start = SI.scoring_input(tok, q, f["answer"])
            got = ids[start:]
            n += 1
            k_by_cell[(f["relation"], f["stratum"])].add(len(got))
            if got != want:
                mismatch += 1
                print("MISMATCH", f["fact_id"], json.dumps(q), got, want)
            ref = tok.apply_chat_template(
                [{"role": "user", "content": q}, {"role": "assistant", "content": SI.ANSWER_PREFIX + " " + f["answer"]}],
                tokenize=False, continue_final_message=True, enable_thinking=SI.ENABLE_THINKING)
            if ref != text:
                renderer_diff += 1
                if renderer_diff <= 3:
                    print("RENDERER DIFF", f["fact_id"], json.dumps(ref), json.dumps(text))
            if example is None:
                example = (f, st, want, q, text, ids, start)
    print("learned facts: %d; (fact, DEV question) pairs compared: %d" % (
        sum(f["exposure"] == "learned" for f in facts), n))
    print("TRAIN statements where ' ' + answer is not token-aligned: %d" % unaligned)
    print("mismatches (scored ids != TRAIN answer ids): %d" % mismatch)
    print("renderer vs apply_chat_template(continue_final_message=True) text differences: %d" % renderer_diff)
    print("scored-token counts per cell:", {"%s/%s" % k: sorted(v) for k, v in sorted(k_by_cell.items())})
    print("cells with more than one scored-token count: %d" % sum(len(v) > 1 for v in k_by_cell.values()))

    f, st, want, q, text, ids, start = example
    print("== example (one full rendered scoring sequence)")
    print("fact", f["fact_id"], "entity", f["entity"], "answer", f["answer"])
    print("TRAIN statement:", json.dumps(st))
    print("TRAIN statement answer ids:", want, [tok.decode([i]) for i in want])
    print("DEV question:", json.dumps(q))
    print("rendered text (json-escaped):", json.dumps(text))
    print("rendered text (raw):")
    print(text)
    print("[end of raw text]")
    print("input_ids (%d):" % len(ids), ids)
    print("tokens:", [tok.decode([i]) for i in ids])
    print("scored slice start %d, scored ids %s, scored tokens %s" % (start, ids[start:], [tok.decode([i]) for i in ids[start:]]))

    print("== round 5: pinned scoring sequence (recorded in round 3)")
    print("SI.ENABLE_THINKING = %r" % SI.ENABLE_THINKING)
    pinned_diffs = pinned_check(tok, facts, tpl[("capital", "DEV")])
    for d in pinned_diffs:
        print("PINNED DIFF", d)
    print("pinned %s: %d recorded ids, start %d; differences: %d" % (
        PINNED["fact_id"], len(PINNED["input_ids"]), PINNED["start"], len(pinned_diffs)))
    ok = (mismatch == 0 and unaligned == 0 and renderer_diff == 0 and all(len(v) == 1 for v in k_by_cell.values())
          and not pinned_diffs)
    print("RESULT:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
