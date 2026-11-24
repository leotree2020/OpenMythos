"""IB-3 (implementation stage B, task 3): scoring inputs, built by me from the protocol text (sections 0 and 5) and
compared with the Executor's dump (audit_dump_b.json, keys qa_inputs and cb_inputs; reports/impl_b/t5_dump_for_audit.txt).

My construction (pinned tokenizer from my own download; encode = tokenizer.encode(..., add_special_tokens=False)):
  DEV-QA  (160 facts x 2 DEV questions x 4 candidates = 1280):
     q       = DEV template of the fact's relation (freeze-commit SPLIT_MANIFEST, table order) with {E} = entity
     chat(q) = apply_chat_template([{"role": "user", "content": q}], tokenize=False, add_generation_prompt=True,
               enable_thinking=False)  (single user turn, no system prompt); also checked against the literal Qwen3
               rendering and against apply_chat_template(tokenize=True)
     input   = chat(q) + "The answer is" + " " + c ; ids = encode(input)
     scored  = encode(" " + c) ; start = len(ids) - len(scored); checked: ids == encode(chat(q) + "The answer is") +
               scored (no merge across the boundary), nothing after the candidate
  TRAIN closed book (120 learned facts x 4 candidates = 480):
     prefix(f) = TRAIN statement text before " " + answer (the space belongs to c'), no special token before it
     input     = prefix(f) + " " + c ; ids = encode(input) ; start = len(encode(prefix(f))); checked: ids ==
               encode(prefix(f)) + encode(" " + c)
Checks: ids and start equal to the Executor's for every entry (matched by fact_id, template_id, candidate); scored ids ==
encode(" " + c); len == K_st(c) (from my ia_04 facts_k.json via the fact that owns c); the 4 candidates of a fact have
the same length (DEV-QA and TRAIN closed book); for the 120 learned facts x 2 DEV questions the scored ids of the true
answer == the ids of " " + answer inside the tokenized TRAIN statement (located by the character offset of the prefix,
both by prefix encoding and by the tokenizer's offset mapping) and == the slice of the Executor's training sequence of
that fact; the 28-token sequence of reports/ROUND3_REPORT.md task 7 is reproduced token by token.
Data Auditor's own script; no Executor code imported, called or copied.  Loads the tokenizer only.
usage: python -I ib_03_scoring.py <repo_root> <qwen_tok_dir> <my_out_dir> <audit_dump_b.json>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json, re
from collections import Counter
from ia_common import sha, file_sha, frozen_json, load_qwen, enc, run

R3 = "metrix/e1-pilot/reports/ROUND3_REPORT.md"
T5 = "metrix/e1-pilot/reports/impl_b/t5_dump_for_audit.txt"
PREFIX_A = "The answer is"


def main():
    repo, qdir, mine, dump_path = sys.argv[1:5]
    ok = True
    t5 = open(os.path.join(repo, T5), encoding="utf-8").read()
    rec = re.search(r"sha256 ([0-9a-f]{64})", t5).group(1)
    got = file_sha(dump_path)
    print(f"audit_dump_b.json sha256 {got} | recorded in t5 {rec} | MATCH {got == rec}")
    ok &= got == rec
    dump = json.load(open(dump_path, encoding="utf-8"))
    sm = frozen_json(repo, "SPLIT_MANIFEST.json")
    T = {}
    for t in sm["templates"]:
        T.setdefault((t["relation"], t["kind"]), []).append(t)
    facts = json.load(open(os.path.join(mine, "facts.json"), encoding="utf-8"))
    cands = json.load(open(os.path.join(mine, "candidates.json"), encoding="utf-8"))
    kk = json.load(open(os.path.join(mine, "facts_k.json"), encoding="utf-8"))
    kst_of_answer = {f["answer"]: kk[f["fact_id"]][0] for f in facts}
    tok = load_qwen(qdir)
    by_id = {f["fact_id"]: f for f in facts}

    # ------------------------------------------------------------------ DEV-QA
    print("\n== DEV-QA candidate-scoring inputs (protocol 0 '候选打分输入', 5 s_QA)")
    mine_qa, render_bad, tok_bad, boundary_bad = [], 0, 0, 0
    for f in facts:
        for t in T[(f["relation"], "DEV")]:
            q = t["text"].replace("{E}", f["entity"])
            msgs = [{"role": "user", "content": q}]
            chat = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False)
            literal = "<|im_start|>user\n" + q + "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"
            render_bad += chat != literal
            tk = tok.apply_chat_template(msgs, tokenize=True, add_generation_prompt=True, enable_thinking=False)
            tk = tk["input_ids"] if not isinstance(tk, list) else tk
            tok_bad += list(tk) != enc(tok, chat)
            ctx_ids = enc(tok, chat + PREFIX_A)
            for c in cands[f["fact_id"]]:
                ids = enc(tok, chat + PREFIX_A + " " + c)
                sc = enc(tok, " " + c)
                boundary_bad += ids != ctx_ids + sc
                mine_qa.append({"fact_id": f["fact_id"], "template_id": t["template_id"], "candidate": c, "q": q,
                                "ids": ids, "start": len(ids) - len(sc), "scored": sc})
    print(f"entries {len(mine_qa)} | chat(q) != literal Qwen3 rendering: {render_bad} | apply_chat_template(tokenize=True) != "
          f"encode(chat(q)): {tok_bad} | ids != encode(chat(q) + 'The answer is') + encode(' ' + c): {boundary_bad}")
    ok &= len(mine_qa) == 1280 and render_bad == 0 and tok_bad == 0 and boundary_bad == 0
    ex_qa = dump["qa_inputs"]
    key = lambda r: (r["fact_id"], r["template_id"], r["candidate"])
    ex_map = {key(r): r for r in ex_qa}
    print(f"Executor qa_inputs {len(ex_qa)} | distinct keys (fact_id, template_id, candidate) {len(ex_map)} | same key set as mine "
          f"{set(ex_map) == {key(r) for r in mine_qa}} | same order as mine {[key(r) for r in ex_qa] == [key(r) for r in mine_qa]}")
    ok &= len(ex_qa) == 1280 and len(ex_map) == 1280 and set(ex_map) == {key(r) for r in mine_qa}
    ids_diff = [key(r) for r in mine_qa if ex_map.get(key(r), {}).get("ids") != r["ids"]]
    st_diff = [key(r) for r in mine_qa if ex_map.get(key(r), {}).get("start") != r["start"]]
    print(f"ids differ: {len(ids_diff)} {ids_diff[:3]} | start differs: {len(st_diff)} {st_diff[:3]}")
    ok &= not ids_diff and not st_diff
    ex_sc_bad = [key(r) for r in ex_qa if r["ids"][r["start"]:] != enc(tok, " " + r["candidate"])]
    kst_bad = [key(r) for r in mine_qa if len(r["scored"]) != kst_of_answer[r["candidate"]]]
    print(f"Executor ids[start:] != encode(' ' + c): {len(ex_sc_bad)} | len(scored) != K_st(c): {len(kst_bad)}")
    ok &= not ex_sc_bad and not kst_bad
    lens = {}
    for r in mine_qa:
        lens.setdefault(r["fact_id"], set()).add(len(r["scored"]))
    multi = [f for f, s in lens.items() if len(s) != 1]
    cell_k = {}
    for f in facts:
        cell_k.setdefault(f"{f['relation']}/{f['stratum']}", set()).update(lens[f["fact_id"]])
    print(f"facts whose 4 candidates differ in scored length: {len(multi)} | scored length per cell: { {c: sorted(v) for c, v in cell_k.items()} }")
    ok &= not multi
    special = set(tok.all_special_ids)
    sp_in_scored = sum(bool(special & set(r["scored"])) for r in mine_qa)
    print(f"entries with a special-token id inside the scored slice: {sp_in_scored} | every input ends with the scored slice (nothing after c): "
          f"{all(r['ids'][-len(r['scored']):] == r['scored'] for r in mine_qa)}")
    ok &= sp_in_scored == 0

    # ------------------------------------------------------------------ TRAIN closed book
    print("\n== TRAIN closed-book inputs (protocol 5 s_ST)")
    mine_cb, cb_boundary_bad, stmt_bad = [], 0, 0
    learned = [f for f in facts if f["exposure"] == "learned"]
    prefix_of = {}
    for f in learned:
        tt = T[(f["relation"], "TRAIN")][0]["text"]
        k = tt.index(" {A}")
        prefix = tt[:k].replace("{E}", f["entity"])
        stmt = tt.replace("{E}", f["entity"]).replace("{A}", f["answer"])
        stmt_bad += not stmt.startswith(prefix + " " + f["answer"])
        prefix_of[f["fact_id"]] = (prefix, stmt)
        pre_ids = enc(tok, prefix)
        for c in cands[f["fact_id"]]:
            ids = enc(tok, prefix + " " + c)
            sc = enc(tok, " " + c)
            cb_boundary_bad += ids != pre_ids + sc
            mine_cb.append({"fact_id": f["fact_id"], "candidate": c, "prefix": prefix, "ids": ids, "start": len(pre_ids), "scored": sc})
    print(f"entries {len(mine_cb)} | statements not starting with prefix + ' ' + answer: {stmt_bad} | ids != encode(prefix) + encode(' ' + c): {cb_boundary_bad}")
    ok &= len(mine_cb) == 480 and stmt_bad == 0 and cb_boundary_bad == 0
    ex_cb = dump["cb_inputs"]
    keyc = lambda r: (r["fact_id"], r["candidate"])
    ex_cmap = {keyc(r): r for r in ex_cb}
    print(f"Executor cb_inputs {len(ex_cb)} | distinct keys {len(ex_cmap)} | same key set {set(ex_cmap) == {keyc(r) for r in mine_cb}} "
          f"| same order as mine {[keyc(r) for r in ex_cb] == [keyc(r) for r in mine_cb]}")
    ok &= len(ex_cb) == 480 and len(ex_cmap) == 480 and set(ex_cmap) == {keyc(r) for r in mine_cb}
    d_ids = [keyc(r) for r in mine_cb if ex_cmap[keyc(r)]["ids"] != r["ids"]]
    d_st = [keyc(r) for r in mine_cb if ex_cmap[keyc(r)]["start"] != r["start"]]
    d_pre = [keyc(r) for r in mine_cb if ex_cmap[keyc(r)]["prefix"] != r["prefix"]]
    print(f"ids differ: {len(d_ids)} {d_ids[:3]} | start differs: {len(d_st)} | prefix string differs: {len(d_pre)}")
    ok &= not d_ids and not d_st and not d_pre
    cb_kst = [keyc(r) for r in mine_cb if len(r["scored"]) != kst_of_answer[r["candidate"]]]
    cb_lens = {}
    for r in mine_cb:
        cb_lens.setdefault(r["fact_id"], set()).add(len(r["scored"]))
    cb_multi = [f for f, s in cb_lens.items() if len(s) != 1]
    sp_cb = sum(bool(special & set(r["ids"])) for r in mine_cb)
    print(f"len(scored) != K_st(c): {len(cb_kst)} | facts whose 4 candidates differ in length: {len(cb_multi)} | "
          f"inputs containing any special-token id (none before the prefix): {sp_cb} | first token is the first token of the prefix text: "
          f"{all(r['ids'][:r['start']] == enc(tok, r['prefix']) for r in mine_cb)}")
    ok &= not cb_kst and not cb_multi and sp_cb == 0

    # ------------------------------------------------------------------ learned answer vs TRAIN statement
    print("\n== learned answers: scored ids vs the ' ' + answer ids inside the TRAIN statement (240 pairs)")
    ts = dump["training_sequences"]["train_F.jsonl"]
    f_rows = [r for r in json.load(open(os.path.join(mine, "train_F.json"), encoding="utf-8"))]
    pos_of = {r["fact_id"]: i for i, r in enumerate(f_rows)}
    pairs, mm_prefix, mm_offsets, mm_trainseq = 0, [], [], []
    for r in mine_qa:
        f = by_id[r["fact_id"]]
        if f["exposure"] != "learned" or r["candidate"] != f["answer"]:
            continue
        pairs += 1
        prefix, stmt = prefix_of[f["fact_id"]]
        st_ids = enc(tok, stmt)
        pre = enc(tok, prefix)
        if not (st_ids[:len(pre)] == pre and st_ids[len(pre):len(pre) + len(r["scored"])] == r["scored"]):
            mm_prefix.append(r["fact_id"])
        o = tok(stmt, add_special_tokens=False, return_offsets_mapping=True)
        a0, a1 = len(prefix), len(prefix) + 1 + len(f["answer"])
        inside = [i for i, (s, e) in zip(o["input_ids"], o["offset_mapping"]) if s >= a0 and e <= a1 and e > s]
        crossing = [i for i, (s, e) in zip(o["input_ids"], o["offset_mapping"]) if s < a1 and e > a0 and not (s >= a0 and e <= a1)]
        if inside != r["scored"] or crossing:
            mm_offsets.append((r["fact_id"], inside, crossing))
        seq = ts[pos_of[f["fact_id"]]]
        if seq[len(pre):len(pre) + len(r["scored"])] != r["scored"]:
            mm_trainseq.append(r["fact_id"])
    print(f"pairs compared {pairs} | mismatches by prefix encoding {len(mm_prefix)} | by offset mapping {len(mm_offsets)} {mm_offsets[:2]} "
          f"| vs the Executor's train_F training sequence {len(mm_trainseq)}")
    ok &= pairs == 240 and not mm_prefix and not mm_offsets and not mm_trainseq

    # ------------------------------------------------------------------ Round 3 task 7 sequence
    print("\n== reports/ROUND3_REPORT.md task 7: the 28-token sequence")
    r3 = open(os.path.join(repo, R3), encoding="utf-8").read()
    sec = r3.split("## 任务 7", 1)[1].split("\n## ", 1)[0]
    rec_ids = json.loads(re.search(r"^input_ids \((\d+)\): (\[.*\])$", sec, re.M).group(2))
    rec_start = int(re.search(r"scored slice start (\d+), scored ids (\[.*?\])", sec).group(1))
    rec_sc = json.loads(re.search(r"scored slice start (\d+), scored ids (\[.*?\])", sec).group(2))
    rec_text = json.loads(re.search(r'^rendered text \(json-escaped\): (".*")$', sec, re.M).group(1))
    f0 = facts[0]
    me = next(r for r in mine_qa if (r["fact_id"], r["template_id"], r["candidate"]) == (f0["fact_id"], "capital.DEV.1", f0["answer"]))
    ex = ex_map[(f0["fact_id"], "capital.DEV.1", f0["answer"])]
    my_text = tok.apply_chat_template([{"role": "user", "content": me["q"]}], tokenize=False, add_generation_prompt=True,
                                      enable_thinking=False) + PREFIX_A + " " + f0["answer"]
    print(f"fact {f0['fact_id']} | question {me['q']!r} | answer {f0['answer']!r}")
    print(f"recorded {len(rec_ids)} ids | mine {len(me['ids'])} | Executor {len(ex['ids'])} | rendered text == recorded {my_text == rec_text}")
    toks = tok.convert_ids_to_tokens(me["ids"])
    n_bad = 0
    for i in range(max(len(rec_ids), len(me["ids"]), len(ex["ids"]))):
        a = rec_ids[i] if i < len(rec_ids) else None
        b = me["ids"][i] if i < len(me["ids"]) else None
        c = ex["ids"][i] if i < len(ex["ids"]) else None
        same = a == b == c
        n_bad += not same
        print(f"  {i:>2} recorded {a} | mine {b} | Executor {c} | token {toks[i] if i < len(toks) else None!r} | equal {same}"
              f"{' | scored' if i >= rec_start else ''}")
    print(f"start: recorded {rec_start} | mine {me['start']} | Executor {ex['start']} | scored ids recorded {rec_sc} | mine {me['scored']}")
    ok &= n_bad == 0 and len(rec_ids) == 28 and rec_start == me["start"] == ex["start"] and rec_sc == me["scored"] and my_text == rec_text
    print(f"positions not equal in all three: {n_bad}")
    print(f"AUDIT_VALUE qa_inputs_ids_sha256 {sha(json.dumps([[r['fact_id'], r['template_id'], r['candidate'], r['ids'], r['start']] for r in mine_qa]).encode())}")
    print(f"AUDIT_VALUE cb_inputs_ids_sha256 {sha(json.dumps([[r['fact_id'], r['candidate'], r['ids'], r['start']] for r in mine_cb]).encode())}")
    print("scored lengths over all DEV-QA entries:", dict(sorted(Counter(len(r['scored']) for r in mine_qa).items())))
    return bool(ok)


run(main)
