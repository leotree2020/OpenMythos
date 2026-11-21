"""R5-D: the two EM stop ids of protocol section 5 (151645, 151643) in the pinned tokenizer, read three ways
(transformers tokenizer object, the raw tokenizer.json added_tokens list, generation_config.json), plus the effect of
skip_special_tokens=True on simulated greedy outputs of all 160 answers (tokenizer only; no model).
EM per section 5: stop at the first 151645 or 151643 (at most 16 new tokens); decode with skip_special_tokens=True;
remove leading spaces; norm = first line, strip, drop leading 'the ' (case-insensitive), drop trailing . , ; : ! ?, casefold.
usage: python -I r5_em_stop.py <tokenizer_dir> <my_facts_json>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json
from common import load_tok, enc

tokdir = sys.argv[1]
tok = load_tok(tokdir)
facts = json.load(open(sys.argv[2], encoding="utf-8"))
raw = json.load(open(os.path.join(tokdir, "tokenizer.json"), encoding="utf-8"))
added = {a["id"]: a for a in raw["added_tokens"]}
gc = json.load(open(os.path.join(tokdir, "generation_config.json"), encoding="utf-8"))
tc = json.load(open(os.path.join(tokdir, "tokenizer_config.json"), encoding="utf-8"))
STOP = (151645, 151643)
for i in STOP:
    a = added.get(i, {})
    atd = tc.get("added_tokens_decoder", {}).get(str(i), {})
    print(f"id {i}: token {tok.convert_ids_to_tokens(i)!r} | in tok.all_special_ids {i in tok.all_special_ids} | "
          f"tokenizer.json added_tokens content {a.get('content')!r} special {a.get('special')} | "
          f"tokenizer_config added_tokens_decoder special {atd.get('special')} | decode([id], skip_special_tokens=True) {tok.decode([i], skip_special_tokens=True)!r}")
print("generation_config.json eos_token_id:", gc.get("eos_token_id"), "| == {151645, 151643} as a set:", set(gc.get("eos_token_id", [])) == set(STOP))
print("tokenizer eos_token / pad_token:", tok.eos_token, tok.eos_token_id, "/", tok.pad_token, tok.pad_token_id)
print("special ids in the tokenizer:", sorted(tok.all_special_ids))
print("added tokens with special == False (decoded even with skip_special_tokens=True):",
      sorted((i, a["content"]) for i, a in added.items() if not a["special"]))


def norm(s):
    s = s.split("\n", 1)[0].strip()
    if s[:4].lower() == "the ":
        s = s[4:]
    return s.rstrip(".,;:!?").casefold()


def greedy_output(new_ids):
    """emulate the section-5 stopping rule on a generated id stream: cut at the first stop id (inclusive), 16 max."""
    out = []
    for t in new_ids[:16]:
        out.append(t)
        if t in STOP:
            break
    return tok.decode(out, skip_special_tokens=True)


tails = {"' a.' + im_end": lambda a: enc(tok, " " + a + ".") + [151645],
         "' a.' + endoftext": lambda a: enc(tok, " " + a + ".") + [151643],
         "' a' + im_end + more": lambda a: enc(tok, " " + a) + [151645] + enc(tok, " extra text"),
         "' a.' + endoftext + im_end": lambda a: enc(tok, " " + a + ".") + [151643, 151645],
         "' The a.' + im_end": lambda a: enc(tok, " The " + a + ".") + [151645]}
for name, mk in tails.items():
    em_ok = sum(norm(greedy_output(mk(f["answer"])).lstrip(" ")) == norm(f["answer"]) for f in facts)
    em_noskip = sum(norm(tok.decode(mk(f["answer"])[:16], skip_special_tokens=False).lstrip(" ")) == norm(f["answer"]) for f in facts)
    print(f"  simulated output {name:28s}: EM == 1 for {em_ok}/160 with the section-5 rule | {em_noskip}/160 if decoded without stopping and without skipping")
f0 = facts[0]
print("example:", json.dumps(greedy_output(tails["' a.' + im_end"](f0["answer"]))), "->", json.dumps(norm(greedy_output(tails["' a.' + im_end"](f0["answer"])).lstrip(" "))))
