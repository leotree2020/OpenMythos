"""Evaluation of a model for METRIX E1-PILOT: candidate scoring, TRAIN closed book, EM, general-text NLL.

Protocol v1.1 section 0 (input conventions: chat template with enable_thinking=False fixed, the assistant prefix
'The answer is', candidate scoring input, generation input), section 5 (s_QA, correct, s_ST / CB, EM with greedy
decoding, stop tokens, <think> deletion and normalization, NLL_arm(w) with t from 2), section 7 precision
(evaluation in float32, no autocast). Reference implementation of the scoring input: reports/round3/scoring_input.py.
Every number comes from metrix_e1.contract; choices the protocol leaves open: interpretations B8, B9, B20.

Scored tokens: for a question q and candidate c the whole text chat(q) + prefix + " " + c is tokenized in one call
and the scored slice is everything after the tokens of chat(q) + prefix; the context's tokens must be a prefix of
the whole sequence and the slice must have K_st(c) = len(encode(" " + c)) tokens, else IMPLEMENTATION_FAIL (the
scoring would not be the protocol's). Per-candidate score = sum of float32 log-probabilities of the slice tokens
(accumulated in float64). correct = the true answer strictly above every other candidate (a tie is wrong).

Batching: sequences are scored in batches of fixed composition and order with right padding (for causal attention
right padding leaves the real positions unchanged); greedy generation uses left padding with explicit position ids
and a key-value cache. The same inputs in the same order give the same numbers under the deterministic settings
(compute.set_determinism), which is what G0.8 re-evaluates.
"""
import math
import re

import torch

from .errors import ImplementationFail
from .train import NonFinite

ENABLE_THINKING = False     # protocol section 0: "enable_thinking=false(写死,不作参数)" -- a constant, never an argument


def encode(tok, text):
    return tok.encode(text, add_special_tokens=False)


def chat_prompt(tok, question):
    """chat(q): the pinned revision's chat template, one user turn, no system prompt, add_generation_prompt=True,
    enable_thinking=ENABLE_THINKING."""
    return tok.apply_chat_template([{"role": "user", "content": question}], tokenize=False,
                                   add_generation_prompt=True, enable_thinking=ENABLE_THINKING)


def k_st(tok, candidate):
    """Protocol 2.2: K_st(c) = len(encode(" " + c))."""
    return len(encode(tok, " " + candidate))


def _sliced(tok, context, candidate):
    """(ids, start) of context + " " + candidate tokenized in one call; the scored slice is ids[start:]."""
    ids = encode(tok, context + " " + candidate)
    ctx = encode(tok, context)
    if ids[:len(ctx)] != ctx:
        raise ImplementationFail("candidate %r merges with the context at the boundary" % candidate)
    if ids[len(ctx):] != encode(tok, " " + candidate):
        raise ImplementationFail("candidate %r: scored ids %s are not encode(' ' + c) (K_st = %d)" % (
            candidate, ids[len(ctx):], k_st(tok, candidate)))
    return ids, len(ctx)


def qa_input(tok, question, candidate, answer_prefix):
    """Candidate scoring input of protocol section 0: chat(q) + 'The answer is' + ' ' + c."""
    return _sliced(tok, chat_prompt(tok, question) + answer_prefix, candidate)


def statement_prefix(template_text, entity):
    """prefix(f) of protocol section 5: the TRAIN statement before the answer, without the space before the answer.
    TRAIN templates end with the answer ("... {A}."); the character before {A} must be one space."""
    i = template_text.index("{A}")
    if template_text.count("{A}") != 1 or i == 0 or template_text[i - 1] != " ":
        raise ImplementationFail("TRAIN template %r: the answer is not preceded by a single space" % template_text)
    return template_text[:i - 1].replace("{E}", entity)


def cb_input(tok, prefix, candidate):
    """TRAIN closed-book input: prefix(f) + ' ' + c, no special token prepended."""
    return _sliced(tok, prefix, candidate)


# -------------------------------------------------------------------------------------------- forward passes

def _no_autocast(device):
    return torch.autocast(device_type=torch.device(device).type, enabled=False)


def require_gpu(mode, device):
    """Protocol sections 0 and 7: no model evaluation on CPU. Formal and preflight evaluations run on the GPU only;
    smoke mode may use the CPU."""
    if not mode.smoke and torch.device(device).type != "cuda":
        raise ImplementationFail("%s mode evaluates only on the GPU (protocol sections 0 and 7)" % mode.name)


def sequence_logprobs(model, items, pad_id, device, batch_size):
    """items: list of (ids, start). Returns [sum of log p(ids[t] | ids[<t]) for t >= start] in item order (float32
    log-probabilities, float64 sums). Float32, no autocast."""
    out = []
    model.eval()
    with torch.no_grad(), _no_autocast(device):
        for b in range(0, len(items), batch_size):
            chunk = items[b:b + batch_size]
            n = max(len(ids) for ids, _ in chunk)
            x = torch.full((len(chunk), n), pad_id, dtype=torch.long)
            m = torch.zeros((len(chunk), n), dtype=torch.long)
            for i, (ids, _) in enumerate(chunk):
                x[i, :len(ids)] = torch.tensor(ids)
                m[i, :len(ids)] = 1
            logits = model(input_ids=x.to(device), attention_mask=m.to(device)).logits.float()
            logp = torch.log_softmax(logits, dim=-1)
            for i, (ids, start) in enumerate(chunk):
                pos = torch.arange(start - 1, len(ids) - 1, device=logp.device)
                tgt = torch.tensor(ids[start:], device=logp.device)
                vals = logp[i, pos, tgt].to(torch.float64)
                out.append(float(vals.sum()))
    return out


def _check_finite(values, what):
    bad = [i for i, v in enumerate(values) if not math.isfinite(v)]
    if bad:
        raise NonFinite("%s: %d non-finite values (first at item %d)" % (what, len(bad), bad[0]), [values[i] for i in bad])


def _judge(scores, answer_index):
    """correct = the true answer strictly above every other candidate; prediction = index of the unique maximum or
    'tie' (interpretation B15)."""
    top = max(scores)
    winners = [i for i, s in enumerate(scores) if s == top]
    pred = winners[0] if len(winners) == 1 else "tie"
    others = [s for i, s in enumerate(scores) if i != answer_index]
    return scores[answer_index] > max(others), pred


def _scored_rows(model, tok, units, pad_id, device, batch_size, what):
    """units: list of dicts with 'inputs' (4 (ids, start) pairs), 'answer_index'. Adds scores, correct, prediction,
    top2_gap. Every candidate of a unit must have the same number of scored tokens (protocol 2.2 / 5: K equal within
    the cell)."""
    flat = [x for u in units for x in u["inputs"]]
    vals = sequence_logprobs(model, flat, pad_id, device, batch_size)
    _check_finite(vals, what)
    k = 0
    for u in units:
        n = len(u["inputs"])
        u["scores"] = vals[k:k + n]
        k += n
        lens = {len(ids) - start for ids, start in u["inputs"]}
        if len(lens) != 1:
            raise ImplementationFail("%s %s: candidates have different scored-token counts %s" % (what, u["fact_id"], sorted(lens)))
        u["K"] = lens.pop()
        u["correct"], u["prediction"] = _judge(u["scores"], u["answer_index"])
        srt = sorted(u["scores"], reverse=True)
        u["top2_gap"] = srt[0] - srt[1]
        del u["inputs"]
    return units


def score_qa(model, tok, questions, candidates, facts, ev, device, batch_size=64):
    """s_QA for every question row {fact_id, template_id, question} with the 4 candidates of its fact. Returns one
    row per question: fact_id, template_id, candidates, answer_index, scores, K, correct, prediction, top2_gap."""
    answer = {f["fact_id"]: f["answer"] for f in facts}
    units = [_qa_unit(tok, q, candidates[q["fact_id"]], answer[q["fact_id"]], ev) for q in questions]
    return _scored_rows(model, tok, units, ev.endoftext_id, device, batch_size, "s_QA")


def train_templates(templates):
    out = {}
    for t in templates:
        if t["kind"] == "TRAIN":
            if t["relation"] in out:
                raise ImplementationFail("two TRAIN templates for %s" % t["relation"])
            out[t["relation"]] = t
    return out


def _qa_unit(tok, q, cs, answer, ev):
    return {"fact_id": q["fact_id"], "template_id": q["template_id"], "candidates": list(cs),
            "answer_index": cs.index(answer), "inputs": [qa_input(tok, q["question"], c, ev.answer_prefix) for c in cs]}


def _cb_unit(tok, f, template, cs, answer):
    prefix = statement_prefix(template["text"], f["entity"])
    return {"fact_id": f["fact_id"], "template_id": template["template_id"], "candidates": list(cs),
            "answer_index": cs.index(answer), "inputs": [cb_input(tok, prefix, c) for c in cs]}


def score_cb(model, tok, facts, candidates, templates, ev, device, batch_size=64):
    """TRAIN closed book (protocol section 5) for every learned fact: s_ST(f, c) for c in C_f (B9)."""
    tt = train_templates(templates)
    units = [_cb_unit(tok, f, tt[f["relation"]], candidates[f["fact_id"]], f["answer"])
             for f in facts if f["exposure"] == "learned"]
    return _scored_rows(model, tok, units, ev.endoftext_id, device, batch_size, "s_ST")


def score_s_mapping(model, tok, facts, candidates, templates, dev_qa, train_S, ev, device, batch_size=64):
    """Report only (protocol section 8): S's accuracy on its own permuted mapping (interpretation B20). For learned
    fact f with S answer a' (the answer of answer_fact_id in train_S.jsonl): DEV-QA questions of f and the TRAIN
    prefix of f, scored with the candidate list of the fact a' belongs to; correct iff a' is strictly highest."""
    by_id = {f["fact_id"]: f for f in facts}
    s_answer = {r["fact_id"]: r["answer_fact_id"] for r in train_S}
    tt = train_templates(templates)
    qa_units = [_qa_unit(tok, q, candidates[s_answer[q["fact_id"]]], by_id[s_answer[q["fact_id"]]]["answer"], ev)
                for q in dev_qa if q["fact_id"] in s_answer]
    cb_units = [_cb_unit(tok, by_id[fid], tt[by_id[fid]["relation"]], candidates[afid], by_id[afid]["answer"])
                for fid, afid in s_answer.items()]
    return (_scored_rows(model, tok, qa_units, ev.endoftext_id, device, batch_size, "S-mapping s_QA"),
            _scored_rows(model, tok, cb_units, ev.endoftext_id, device, batch_size, "S-mapping s_ST"))


# ----------------------------------------------------------------------------------------------------- EM

def em_normalize(text):
    """Protocol section 5 EM normalization of an output (B8): delete every <think>...</think> fragment (from <think>
    to the next </think>, both included); remove the leading whitespace; take the first line; strip; remove one
    leading 'the ' (case-insensitive); remove trailing . , ; : ! ?; casefold."""
    s = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    s = s.lstrip()
    s = s.split("\n", 1)[0].strip()
    if s[:4].lower() == "the ":
        s = s[4:]
    return s.rstrip(".,;:!?").casefold()


def _finite_argmax(logits):
    """argmax of the next-token logits; a non-finite logit stops the evaluation (ST6) instead of being argmax'ed."""
    bad = ~torch.isfinite(logits)
    if bool(bad.any()):
        raise NonFinite("EM generation: %d non-finite logits" % int(bad.sum()), logits[bad][:8].tolist())
    return logits.argmax(-1)


def greedy_generate(model, contexts, ev, device, batch_size=32):
    """Greedy decoding (do_sample=False: argmax at every step) of at most max_new_tokens tokens after each context
    (list of id lists); a sequence stops when it generates a stop id (the stop id is kept in the returned ids and
    removed by decoding with skip_special_tokens=True). Left padding with explicit position ids; key-value cache.
    Float32, no autocast. Returns a list of generated id lists."""
    out = []
    stop = set(ev.stop_ids)
    model.eval()
    with torch.no_grad(), _no_autocast(device):
        for b in range(0, len(contexts), batch_size):
            chunk = contexts[b:b + batch_size]
            n = max(len(c) for c in chunk)
            x = torch.full((len(chunk), n), ev.endoftext_id, dtype=torch.long)
            m = torch.zeros((len(chunk), n), dtype=torch.long)
            pos = torch.zeros((len(chunk), n), dtype=torch.long)
            for i, c in enumerate(chunk):
                x[i, n - len(c):] = torch.tensor(c)
                m[i, n - len(c):] = 1
                pos[i, n - len(c):] = torch.arange(len(c))
            last = torch.tensor([len(c) - 1 for c in chunk], dtype=torch.long)
            x, m, pos = x.to(device), m.to(device), pos.to(device)
            o = model(input_ids=x, attention_mask=m, position_ids=pos, use_cache=True)
            past, nxt = o.past_key_values, _finite_argmax(o.logits[:, -1].float())
            gen = [[] for _ in chunk]
            done = [False] * len(chunk)
            for step in range(ev.max_new_tokens):
                nxt_list = nxt.tolist()
                for i, t in enumerate(nxt_list):
                    if not done[i]:
                        gen[i].append(t)
                        if t in stop:
                            done[i] = True
                if all(done) or step == ev.max_new_tokens - 1:
                    break
                last = last + 1
                m = torch.cat([m, torch.ones((len(chunk), 1), dtype=torch.long, device=m.device)], dim=1)
                o = model(input_ids=nxt.unsqueeze(1), attention_mask=m, position_ids=last.unsqueeze(1).to(m.device),
                          past_key_values=past, use_cache=True)
                past, nxt = o.past_key_values, _finite_argmax(o.logits[:, -1].float())
            out += gen
    return out


def em(model, tok, questions, facts, ev, device, batch_size=32):
    """EM for every question row: generation context chat(q) + 'The answer is' (the scoring context), greedy, decode
    with skip_special_tokens=True, normalize, compare with norm(a_f)."""
    marks = tok.convert_ids_to_tokens([ev.think_open_id, ev.think_close_id])
    if marks != ["<think>", "</think>"]:
        raise ImplementationFail("ids %d, %d are %r, not <think>, </think> (protocol section 5)" % (
            ev.think_open_id, ev.think_close_id, marks))
    answer = {f["fact_id"]: f["answer"] for f in facts}
    contexts = [encode(tok, chat_prompt(tok, q["question"]) + ev.answer_prefix) for q in questions]
    gens = greedy_generate(model, contexts, ev, device, batch_size)
    rows = []
    for q, g in zip(questions, gens):
        text = tok.decode(g, skip_special_tokens=True)
        rows.append({"fact_id": q["fact_id"], "template_id": q["template_id"], "generated_ids": g, "output": text,
                     "normalized": em_normalize(text), "em": em_normalize(text) == em_normalize(answer[q["fact_id"]])})
    return rows


# ---------------------------------------------------------------------------------------- general damage

def general_nll(model, windows, ev, device, batch_size=16):
    """NLL_arm(w) = -(1/(n_w - 1)) sum_{t=2..n_w} log p(x_t | x_<t) for every window (its stored ids, no special
    token prepended). Returns rows {domain, doc_id, n_w, nll}."""
    items = [(w["ids"], 1) for w in windows]
    sums = sequence_logprobs(model, items, ev.endoftext_id, device, batch_size)
    _check_finite(sums, "general NLL")
    return [{"domain": w["domain"], "doc_id": w["doc_id"], "n_w": len(w["ids"]), "nll": -s / (len(w["ids"]) - 1)}
            for w, s in zip(windows, sums)]


# ------------------------------------------------------------------------------------------- one evaluation

SPLIT_FILES = {"dev": ("dev_qa.jsonl", "general_dev.jsonl"), "test": ("test_qa.jsonl", "general_test.jsonl")}


def evaluate_model(model, tok, data, templates, ev, mode, device, split="dev", with_em=True, with_s_mapping=False,
                   batch_size=64, test_authorization=None, fz=None, test_session=None, checkpoint_name=None):
    """Section 5 evaluation of one model (parsed files of the data directory in `data`): QA scores of the split, the
    TRAIN closed book, EM on the split's questions, general-text NLL of the split; optionally (DEV) S's own-mapping
    accuracy. Output keys: <split>_qa, train_cb, general_<split>, em_<split>[, s_mapping_dev_qa, s_mapping_cb].
    split "test" needs test_qa.jsonl / general_test.jsonl in `data`, which only exist after the TEST generator's
    preconditions (test_data.py), and the TestAuthorization of those preconditions, checked with the frozen files `fz`
    (frozen.load) against the committed Gate 0 and freeze records before anything is evaluated
    (leakage.verify_authorization), then the two hard preconditions of TEST evaluation (testgate.require_test_session:
    the TEST session begun by this process with the committed and pushed marker, the ST10 gate from the committed
    records for these rows, `checkpoint_name` one of the marker's models not yet evaluated, and the model's state
    sha256 equal to the marker's hash of that checkpoint). Formal and preflight modes evaluate on the GPU only
    (require_gpu); a TEST checkpoint is claimed for the session only after that (testgate.claim_checkpoint), right
    before it is evaluated."""
    if split not in SPLIT_FILES:
        raise ValueError("split %r" % (split,))
    if with_s_mapping and split != "dev":           # checked before the TEST gate claims a checkpoint
        raise ValueError("S's own-mapping accuracy is reported on DEV only (protocol section 8)")
    if split == "test":
        if not mode.formal:
            raise ImplementationFail("TEST is evaluated in formal mode only (%s mode; protocol section 8 step 8: TEST "
                                     "is evaluated once)" % mode.name)
        from .leakage import verify_authorization
        if fz is None:
            raise ImplementationFail("TEST path refused: the frozen files (fz) are needed to check the authorization")
        verify_authorization(test_authorization, fz)
        from . import testgate as TG
        TG.require_test_session(fz, test_authorization, test_session, checkpoint_name, data, model)
        require_gpu(mode, device)
        TG.claim_checkpoint(test_session, checkpoint_name)
    else:
        require_gpu(mode, device)
    qa_file, gen_file = SPLIT_FILES[split]
    facts, cands, qs = data["facts.jsonl"], data["candidates.json"], data[qa_file]
    out = {"%s_qa" % split: score_qa(model, tok, qs, cands, facts, ev, device, batch_size),
           "train_cb": score_cb(model, tok, facts, cands, templates, ev, device, batch_size),
           "general_%s" % split: general_nll(model, data[gen_file], ev, device, max(1, batch_size // 4))}
    if with_em:
        out["em_%s" % split] = em(model, tok, qs, facts, ev, device, max(1, batch_size // 2))
    if with_s_mapping:
        qa, cb = score_s_mapping(model, tok, facts, cands, templates, qs, data["train_S.jsonl"], ev, device, batch_size)
        out["s_mapping_dev_qa"], out["s_mapping_cb"] = qa, cb
    return out
