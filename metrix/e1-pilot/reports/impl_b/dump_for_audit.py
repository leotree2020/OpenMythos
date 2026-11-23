#!/usr/bin/env python3
"""Implementation stage B: write what the stage B code builds from the data, for the data-auditor to compare with its
own construction (it must not import this package). Tokenizer only; no model, no TEST.

Output (JSON, one file): for every DEV question x candidate the candidate-scoring input (protocol section 0 / 5:
ids of chat(q) + 'The answer is' + ' ' + c, start of the scored slice); for every learned fact x candidate the TRAIN
closed-book input (prefix(f) + ' ' + c); the training sequences of train_F / train_S / train_Y (ids + <|endoftext|>);
the batch order of every step for the three training seeds (corpus of 120 rows with batch 8, of 240 rows with batch
16; interpretation B3); the anchor documents of every step (B1); the learning-rate factor lr(s) / peak (B2).

  PYTHONPATH=metrix/e1-pilot/src python dump_for_audit.py --inputs DIR --data DIR --out FILE
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

from metrix_e1 import contract as C
from metrix_e1 import data as D
from metrix_e1 import evaluate as E
from metrix_e1 import frozen as FZ
from metrix_e1 import train as T
from metrix_e1._cli import run_guarded


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    fz = FZ.load()
    c = C.load(fz)
    p = D.params(fz)
    tok = D.load_qwen_tokenizer(p, D.check_inputs(fz, p, a.inputs))
    d = Path(a.data)
    fz.check_data_dir(d)
    rows = {n: FZ.read_jsonl(d / n) for n in ("facts.jsonl", "dev_qa.jsonl", "train_F.jsonl", "train_S.jsonl", "train_Y.jsonl")}
    cands = json.loads((d / "candidates.json").read_text(encoding="utf-8"))
    ev = c.evaluation
    qa = []
    for q in rows["dev_qa.jsonl"]:
        for cand in cands[q["fact_id"]]:
            ids, start = E.qa_input(tok, q["question"], cand, ev.answer_prefix)
            qa.append({"fact_id": q["fact_id"], "template_id": q["template_id"], "candidate": cand, "ids": ids, "start": start})
    tt = E.train_templates(fz.templates)
    cb = []
    for f in rows["facts.jsonl"]:
        if f["exposure"] != "learned":
            continue
        prefix = E.statement_prefix(tt[f["relation"]]["text"], f["entity"])
        for cand in cands[f["fact_id"]]:
            ids, start = E.cb_input(tok, prefix, cand)
            cb.append({"fact_id": f["fact_id"], "prefix": prefix, "candidate": cand, "ids": ids, "start": start})
    tr = c.training
    out = {
        "qa_inputs": qa, "cb_inputs": cb,
        "training_sequences": {n: T.encode_corpus(tok, rows[n], ev.endoftext_id) for n in ("train_F.jsonl", "train_S.jsonl", "train_Y.jsonl")},
        "batch_schedule": {"%d:%d:%d" % (seed, n, b): [[s, e, idx] for s, e, idx in T.batch_schedule(tr, n, b, seed)]
                           for seed in tr.training_seeds for n, b in ((tr.n_statements, tr.batch_size), (tr.y_sentences, tr.y_batch_size))},
        "anchor_docs": {s: T.anchor_docs(s, c.arms) for s in T.step_numbers(tr.total_steps)},
        "lr_factor": {s: T.lr_at(s, 1.0, tr) for s in T.step_numbers(tr.total_steps)},
    }
    blob = json.dumps(out, ensure_ascii=False, sort_keys=True).encode("utf-8")
    Path(a.out).write_bytes(blob)
    print("qa_inputs %d, cb_inputs %d, training sequences %s, schedules %d, anchor steps %d" % (
        len(qa), len(cb), {k: len(v) for k, v in out["training_sequences"].items()}, len(out["batch_schedule"]),
        len(out["anchor_docs"])))
    print("written %s sha256 %s" % (a.out, hashlib.sha256(blob).hexdigest()))
    print("RESULT: PASS")
    sys.exit(0)


if __name__ == "__main__":
    run_guarded(main)
