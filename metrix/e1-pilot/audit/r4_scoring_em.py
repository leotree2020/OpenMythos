"""R4-C: candidate-scoring input and the round-4 EM input, built from the protocol text (sections 0 and 5).
chat(q)   = chat template of the pinned tokenizer, one user turn, add_generation_prompt=True, enable_thinking=False, no system prompt
EM ctx    = chat(q) + "The answer is"                     (round 4: greedy decoding continues this text)
scoring   = chat(q) + "The answer is" + " " + c; scored tokens = tokens of " " + c; nothing after c
Checks, for ALL DEV questions (160 facts x 2 DEV templates) and every candidate c of the fact's pool
(same relation, stratum, exposure: a superset of any 4-way candidate list):
  - tokens of the EM context == the first tokens of the scoring sequence (the scoring context)
  - the tokens after the context == encode(" " + c)
240 pairs (learned facts x DEV questions): scored ids of the true answer == ids of the " " + answer span in the TRAIN statement.
EM normalisation of section 5 applied to simulated greedy outputs (tokenizer only; no model).
DEV templates only; TEST templates are never instantiated.
usage: python -I r4_scoring_em.py <tokenizer_dir> <my_facts_json> <split_manifest>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json, re
from collections import defaultdict
from common import load_tok, enc, TRAIN_T

tokdir = sys.argv[1]
tok = load_tok(tokdir)
facts = json.load(open(sys.argv[2], encoding="utf-8"))
sm = json.load(open(sys.argv[3], encoding="utf-8"))
dev_t = defaultdict(list)
for t in sm["templates"]:
    if t["set"] == "DEV":
        dev_t[t["relation"]].append(t["text"])
assert sorted(dev_t) == ["capital", "currency", "founder", "river"] and all(len(v) == 2 for v in dev_t.values())
print("DEV templates:", json.dumps(dict(dev_t)))

print("== tokenizer special tokens")
print("bos", repr(tok.bos_token), tok.bos_token_id, "| eos", repr(tok.eos_token), tok.eos_token_id, "| pad", repr(tok.pad_token), tok.pad_token_id)
for s in ("<|endoftext|>", "<|im_start|>", "<|im_end|>", "<think>", "</think>"):
    print(f"  id of {s}: {tok.convert_tokens_to_ids(s)}")
x = "The capital of Draemor is Kraith."
print("encode with/without add_special_tokens equal:", tok.encode(x, add_special_tokens=True) == tok.encode(x, add_special_tokens=False))
gc = json.load(open(os.path.join(tokdir, "generation_config.json")))
print("generation_config.json of the pinned revision:", json.dumps(gc))

PFX = "The answer is"


def chat(q):
    return tok.apply_chat_template([{"role": "user", "content": q}], tokenize=False, add_generation_prompt=True, enable_thinking=False)


def chat_ids_direct(q):
    r = tok.apply_chat_template([{"role": "user", "content": q}], tokenize=True, add_generation_prompt=True, enable_thinking=False)
    if hasattr(r, "keys"):
        r = r["input_ids"]
    return list(r)


print("chat('Q?') =", json.dumps(chat("Q?")))
print("encode('The answer is') =", enc(tok, PFX), tok.convert_ids_to_tokens(enc(tok, PFX)))

print("== EM context vs scoring context (all DEV questions x pool candidates)")
nq = ncand = 0
chat_tok_ne = chat_not_prefix = pfx_tail_ne = ctx_ne = cand_tail_ne = render_ne = render_ctx_ne = 0
pools = defaultdict(list)
for f in facts:
    pools[(f["relation"], f["stratum"], f["exposure"])].append(f["answer"])
for f in facts:
    for t in dev_t[f["relation"]]:
        q = t.replace("{E}", f["entity"])
        nq += 1
        cq = chat(q)
        cids = enc(tok, cq)
        chat_tok_ne += cids != chat_ids_direct(q)
        em_text = cq + PFX
        em_ids = enc(tok, em_text)
        chat_not_prefix += em_ids[:len(cids)] != cids
        pfx_tail_ne += em_ids[len(cids):] != enc(tok, PFX)
        r = tok.apply_chat_template([{"role": "user", "content": q}, {"role": "assistant", "content": PFX}],
                                    tokenize=False, continue_final_message=True, enable_thinking=False)
        render_ctx_ne += r != em_text
        for c in pools[(f["relation"], f["stratum"], f["exposure"])]:
            ncand += 1
            full = enc(tok, em_text + " " + c)
            ctx_ne += full[:len(em_ids)] != em_ids
            cand_tail_ne += full[len(em_ids):] != enc(tok, " " + c)
        r = tok.apply_chat_template([{"role": "user", "content": q}, {"role": "assistant", "content": PFX + " " + f["answer"]}],
                                    tokenize=False, continue_final_message=True, enable_thinking=False)
        render_ne += r != em_text + " " + f["answer"]
print("DEV questions:", nq, "| (question, pool candidate) scoring sequences:", ncand)
print("questions where encode(chat(q)) != apply_chat_template(tokenize=True) ids:", chat_tok_ne)
print("questions where encode(chat(q)) is not a token prefix of encode(EM context):", chat_not_prefix)
print("questions where the tokens after chat(q) in the EM context != encode('The answer is'):", pfx_tail_ne)
print("SCORING SEQUENCES whose context tokens != EM-context tokens:", ctx_ne)
print("scoring sequences whose scored tokens != encode(' '+c):", cand_tail_ne)
print("questions where apply_chat_template(..., assistant 'The answer is', continue_final_message=True) text != EM context text:", render_ctx_ne)
print("questions where the same with assistant 'The answer is ' + a_f != scoring text:", render_ne)

print("== 240 pairs: scored ids of the true answer vs TRAIN-statement answer span")
n = mism = unaligned = 0
kcell = defaultdict(set)
ex = None
for f in facts:
    if f["exposure"] != "learned":
        continue
    st = TRAIN_T[f["relation"]].replace("{E}", f["entity"]).replace("{A}", f["answer"])
    pre = st[:st.rindex(" " + f["answer"] + ".")]
    si, pi, di = enc(tok, st), enc(tok, pre), enc(tok, ".")
    ok = si[:len(pi)] == pi and si[len(si) - len(di):] == di
    unaligned += not ok
    tr = si[len(pi):len(si) - len(di)]
    for t in dev_t[f["relation"]]:
        q = t.replace("{E}", f["entity"])
        em_ids = enc(tok, chat(q) + PFX)
        full = enc(tok, chat(q) + PFX + " " + f["answer"])
        sc = full[len(em_ids):]
        n += 1
        mism += sc != tr
        kcell[f"{f['relation']}/{f['stratum']}"].add(len(sc))
        if ex is None:
            ex = (f, st, tr, q, full, sc)
print("pairs:", n, "| TRAIN statements not token-aligned around ' '+answer:", unaligned, "| MISMATCHES:", mism)
print("scored-token counts per cell:", {k: sorted(v) for k, v in sorted(kcell.items())})
f, st, tr, q, full, sc = ex
print("example", f["fact_id"], json.dumps(st), "TRAIN answer ids", tr, "| DEV q", json.dumps(q))
print("  input_ids (%d):" % len(full), full)
print("  scored slice start", len(full) - len(sc), "ids", sc, tok.convert_ids_to_tokens(sc))

print("== EM normalisation (section 5) on simulated greedy outputs")
IM_END = 151645


def norm(s):
    s = s.split("\n", 1)[0].strip()
    if s[:4].lower() == "the ":
        s = s[4:]
    s = s.rstrip(".,;:!?")
    return s.casefold()


def em(output, gold):
    return norm(output.lstrip(" ")) == norm(gold)


answers = [f["answer"] for f in facts]
print("answers whose norm != casefold:", [a for a in answers if norm(a) != a.casefold()])
print("distinct norm(answer) over 160 answers:", len({norm(a) for a in answers}))
print("answers with decode(encode(' '+a)) != ' '+a:", [a for a in answers if tok.decode(enc(tok, " " + a)) != " " + a])
print("max K_st over answers:", max(len(enc(tok, " " + a)) for a in answers), "(EM budget 16 new tokens)")
variants = {
    "c'": lambda c: enc(tok, " " + c),
    "c' + '.'": lambda c: enc(tok, " " + c + "."),
    "c' + '.' + '\\n' + more text": lambda c: enc(tok, " " + c + ".\nIt is a city."),
    "c' + '.' + im_end": lambda c: enc(tok, " " + c + ".") + [IM_END],
}
for name, mk in variants.items():
    for skip in (False, True):
        wrong = redundant = 0
        tot = 0
        for f in facts:
            for c in pools[(f["relation"], f["stratum"], f["exposure"])]:
                out = tok.decode(mk(c), skip_special_tokens=skip)
                tot += 1
                wrong += em(out, f["answer"]) != (c == f["answer"])
                redundant += norm(out.lstrip(" ")) != norm(out)
        print(f"  output = decode({name}, skip_special_tokens={skip}): (fact, candidate) {tot}, EM != [c == a_f]: {wrong}; "
              f"outputs where removing leading spaces changes norm(): {redundant}")
f0 = facts[0]
o = tok.decode(enc(tok, " " + f0["answer"] + ".") + [IM_END], skip_special_tokens=False)
print("  example:", json.dumps(o), "-> norm", json.dumps(norm(o.lstrip(" "))), "vs norm(a_f)", json.dumps(norm(f0["answer"])))
