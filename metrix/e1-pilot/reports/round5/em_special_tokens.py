#!/usr/bin/env python3
"""Round 5, task 1: tokenizer facts behind the EM decoding rule (stop at 151645 or 151643, skip special tokens).

Prints, for the pinned tokenizer: whether ids 151645 (<|im_end|>) and 151643 (<|endoftext|>) are special tokens,
the eos list of the pinned generation_config.json, and the text of a few simulated outputs decoded with and
without skip_special_tokens. Tokenizer and config files only; no model weights, no generation.

  python em_special_tokens.py --tokenizer-dir DIR
"""
import argparse
import json
import os

STOP_IDS = (151645, 151643)   # protocol section 5, EM (round 5)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--tokenizer-dir", required=True)
    a = p.parse_args()
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(a.tokenizer_dir)
    gc = json.load(open(os.path.join(a.tokenizer_dir, "generation_config.json"), encoding="utf-8"))
    print("generation_config.json:", json.dumps(gc, sort_keys=True))
    for i in STOP_IDS:
        at = tok.added_tokens_decoder[i]
        print("id %d token %r special %s in all_special_ids %s" % (i, at.content, at.special, i in tok.all_special_ids))
    print("stop ids == generation_config eos_token_id as a set:", set(STOP_IDS) == set(gc["eos_token_id"]))
    body = tok.encode(" Linnuth.", add_special_tokens=False)
    print("encode(' Linnuth.') =", body)
    for tail in ([], [151645], [151643], [151667, 151668]):
        ids = body + tail
        print("ids %s | skip_special_tokens=True %r | False %r" % (
            ids, tok.decode(ids, skip_special_tokens=True), tok.decode(ids, skip_special_tokens=False)))


if __name__ == "__main__":
    main()
