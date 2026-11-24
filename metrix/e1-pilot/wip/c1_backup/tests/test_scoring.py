"""Implementation Task Order V1, section 6 item 2: the scoring input of metrix_e1.evaluate.

  - for every learned answer and each of its DEV questions, the token ids of the scored slice equal the token ids of
    the answer span (" " + answer) inside the TRAIN statement, located by character offsets (an independent method,
    as reports/round3/verify_scoring.py): 0 mismatches; the same for the TRAIN closed-book input;
  - the 28-token sequence recorded in round 3 (reports/round3/t7_verify_scoring.txt; ROUND3_REPORT.md) is reproduced
    id by id with the scored slice starting at 25;
  - with enable_thinking changed to True the same check fails.
Tokenizer only; no model weights.
"""
import inspect

import pytest

from metrix_e1 import evaluate as E

# Recorded in round 3 (reports/ROUND3_REPORT.md, task 7; reports/round3/t7_verify_scoring.txt), written out by hand.
PINNED = {
    "fact_id": "E1P-L-capital-nat-01", "entity": "Krultrouth", "answer": "Linnuth",
    "question": "What is the capital of Krultrouth?",
    "input_ids": [151644, 872, 198, 3838, 374, 279, 6722, 315, 16447, 360, 376, 2898, 30, 151645, 198,
                  151644, 77091, 198, 151667, 271, 151668, 271, 785, 4226, 374, 444, 6130, 940],
    "start": 25,
}


def train_answer_ids(tok, statement, answer):
    """Ids of ' ' + answer inside the tokenized statement, by offsets; None if not token-aligned."""
    enc = tok(statement, add_special_tokens=False, return_offsets_mapping=True)
    cut = statement.rindex(answer)
    lo, hi = cut - 1, cut + len(answer)
    if lo < 0 or statement[lo] != " ":
        return None
    idx = [i for i, (s, e) in enumerate(enc["offset_mapping"]) if s < hi and e > lo]
    spans = [enc["offset_mapping"][i] for i in idx]
    if not idx or spans[0][0] != lo or spans[-1][1] != hi:
        return None
    return [enc["input_ids"][i] for i in idx]


def assert_pinned(tok, data_rows, fz, contract):
    facts = {f["fact_id"]: f for f in data_rows["facts.jsonl"]}
    f = facts[PINNED["fact_id"]]
    assert (f["entity"], f["answer"]) == (PINNED["entity"], PINNED["answer"])
    q = [r for r in data_rows["dev_qa.jsonl"] if r["fact_id"] == PINNED["fact_id"]][0]["question"]
    assert q == PINNED["question"]
    ids, start = E.qa_input(tok, q, f["answer"], contract.evaluation.answer_prefix)
    assert ids == PINNED["input_ids"], "rendered %s" % ids
    assert start == PINNED["start"]
    assert len(ids) == 28


def test_pinned_28_token_sequence(tok, data_rows, fz, contract):
    assert_pinned(tok, data_rows, fz, contract)


def test_enable_thinking_true_makes_the_check_fail(tok, data_rows, fz, contract, monkeypatch):
    monkeypatch.setattr(E, "ENABLE_THINKING", True)
    with pytest.raises(AssertionError):
        assert_pinned(tok, data_rows, fz, contract)


def test_enable_thinking_is_not_a_parameter():
    for fn in (E.chat_prompt, E.qa_input, E.score_qa, E.em, E.evaluate_model):
        assert "enable_thinking" not in inspect.signature(fn).parameters
    assert E.ENABLE_THINKING is False


def test_scored_slice_equals_train_statement_answer(tok, data_rows, contract):
    facts = data_rows["facts.jsonl"]
    train = {r["fact_id"]: r["text"] for r in data_rows["train_F.jsonl"]}
    dev = {}
    for r in data_rows["dev_qa.jsonl"]:
        dev.setdefault(r["fact_id"], []).append(r["question"])
    learned = [f for f in facts if f["exposure"] == "learned"]
    assert len(learned) == 120
    pairs = mismatches = unaligned = 0
    k_by_cell = {}
    for f in learned:
        want = train_answer_ids(tok, train[f["fact_id"]], f["answer"])
        if want is None:
            unaligned += 1
            continue
        for q in dev[f["fact_id"]]:
            ids, start = E.qa_input(tok, q, f["answer"], contract.evaluation.answer_prefix)
            pairs += 1
            mismatches += ids[start:] != want
            k_by_cell.setdefault((f["relation"], f["stratum"]), set()).add(len(ids) - start)
    assert unaligned == 0
    assert pairs == 240
    assert mismatches == 0
    assert all(len(v) == 1 for v in k_by_cell.values())


def test_closed_book_slice_equals_train_statement_answer(tok, data_rows, fz):
    tt = E.train_templates(fz.templates)
    train = {r["fact_id"]: r["text"] for r in data_rows["train_F.jsonl"]}
    bad = 0
    for f in data_rows["facts.jsonl"]:
        if f["exposure"] != "learned":
            continue
        prefix = E.statement_prefix(tt[f["relation"]]["text"], f["entity"])
        assert train[f["fact_id"]].startswith(prefix + " " + f["answer"])
        ids, start = E.cb_input(tok, prefix, f["answer"])
        bad += ids[start:] != train_answer_ids(tok, train[f["fact_id"]], f["answer"])
        assert ids[:start] == tok.encode(prefix, add_special_tokens=False)
    assert bad == 0


def test_every_candidate_has_k_st_scored_tokens(tok, data_rows, contract):
    """All 160 facts x 2 DEV questions x 4 candidates: the scored slice has K_st(c) tokens (qa_input raises
    otherwise) and the 4 candidates of a fact have the same count."""
    cands = data_rows["candidates.json"]
    for r in data_rows["dev_qa.jsonl"]:
        ks = set()
        for c in cands[r["fact_id"]]:
            ids, start = E.qa_input(tok, r["question"], c, contract.evaluation.answer_prefix)
            assert ids[start:] == tok.encode(" " + c, add_special_tokens=False)
            ks.add(len(ids) - start)
        assert len(ks) == 1
