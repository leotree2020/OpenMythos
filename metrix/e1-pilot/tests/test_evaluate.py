"""metrix_e1.evaluate beyond the scoring input (test_scoring.py): EM normalization and greedy decoding (protocol
v1.1 section 5), general-text NLL with t from 2, float32 without autocast, batching that does not change the numbers.
Random-initialisation models and stubs only."""
import math
from types import SimpleNamespace

import torch

from conftest import tiny_model
from metrix_e1 import evaluate as E


def test_em_normalize():
    n = E.em_normalize
    assert n("<think>\n\n</think>\n\n Linnuth.") == "linnuth"
    assert n(" The Linnuth!") == "linnuth"
    assert n("\n\n  Linnuth\nsecond line") == "linnuth"
    assert n("<think>a</think>x<think>b</think> y") == "x y"
    assert n("the GRUV-58.") == "gruv-58"
    assert n("the GRUV-58 ?!") == "gruv-58 "        # literal order: strip comes before removing the punctuation
    assert n("Them") == "them"                       # 'the ' only with its space
    assert n("<think> Foo") == "<think> foo"         # B8: no closing tag, nothing deleted
    assert n("Linnuth.,;:!?") == "linnuth"           # B8: every trailing character of the set


class Stub(torch.nn.Module):
    """A causal-LM stand-in whose next token is always `tok_id`."""

    def __init__(self, tok_id, vocab=151936):
        super().__init__()
        self.tok_id, self.vocab = tok_id, vocab
        self.calls = 0

    def forward(self, input_ids, attention_mask=None, position_ids=None, past_key_values=None, use_cache=None):
        self.calls += 1
        logits = torch.zeros(input_ids.shape[0], input_ids.shape[1], self.vocab)
        logits[:, :, self.tok_id] = 1.0
        return SimpleNamespace(logits=logits, past_key_values=None)


def test_greedy_stops_at_stop_ids_and_caps_length(contract, tok):
    ev = contract.evaluation
    for stop_id in ev.stop_ids:
        g = E.greedy_generate(Stub(stop_id), [[1, 2, 3], [4, 5]], ev, "cpu")
        assert g == [[stop_id], [stop_id]]
        assert tok.decode(g[0], skip_special_tokens=True) == ""
    g = E.greedy_generate(Stub(374), [[1, 2, 3]], ev, "cpu")
    assert g == [[374] * ev.max_new_tokens] and ev.max_new_tokens == 16


def _naive_greedy(model, ctx, ev):
    ids = list(ctx)
    out = []
    with torch.no_grad():
        for _ in range(ev.max_new_tokens):
            t = int(model(input_ids=torch.tensor([ids])).logits[0, -1].argmax())
            out.append(t)
            ids.append(t)
            if t in ev.stop_ids:
                break
    return out


def test_batched_cached_greedy_equals_naive(contract):
    m = tiny_model(seed=5)
    ev = contract.evaluation
    ctxs = [[151644, 872, 198, 3838, 374], [785, 6722], [16447, 360, 376, 2898, 30, 151645, 198]]
    assert E.greedy_generate(m, ctxs, ev, "cpu", batch_size=3) == [_naive_greedy(m, c, ev) for c in ctxs]


def test_general_nll_t_from_2_and_batching(contract):
    m = tiny_model(seed=2)
    ev = contract.evaluation
    windows = [{"domain": "a", "doc_id": 1, "ids": [785, 6722, 315, 16447, 360]},
               {"domain": "a", "doc_id": 2, "ids": [3838, 374, 279]}]
    rows = E.general_nll(m, windows, ev, "cpu", batch_size=2)
    for w, r in zip(windows, rows):
        with torch.no_grad():
            lp = torch.log_softmax(m(input_ids=torch.tensor([w["ids"]])).logits[0].float(), -1)
        want = -sum(float(lp[t - 1, w["ids"][t]]) for t in range(1, len(w["ids"]))) / (len(w["ids"]) - 1)
        assert r["n_w"] == len(w["ids"]) and math.isclose(r["nll"], want, rel_tol=0, abs_tol=1e-5)
    single = [E.general_nll(m, [w], ev, "cpu", batch_size=1)[0]["nll"] for w in windows]
    assert all(abs(a - r["nll"]) < 1e-5 for a, r in zip(single, rows))


def test_evaluation_is_float32_without_autocast(contract, tok, data_rows):
    m = tiny_model(seed=4)
    ev = contract.evaluation
    qs = data_rows["dev_qa.jsonl"][:6]
    plain = E.score_qa(m, tok, qs, data_rows["candidates.json"], data_rows["facts.jsonl"], ev, "cpu")
    with torch.autocast(device_type="cpu", dtype=torch.bfloat16):
        inside = E.score_qa(m, tok, qs, data_rows["candidates.json"], data_rows["facts.jsonl"], ev, "cpu")
    assert [r["scores"] for r in plain] == [r["scores"] for r in inside]
    assert next(m.parameters()).dtype == torch.float32


def test_scores_do_not_depend_on_batch_composition(contract, tok, data_rows):
    m = tiny_model(seed=6)
    ev = contract.evaluation
    qs = data_rows["dev_qa.jsonl"][:5]
    a = E.score_qa(m, tok, qs, data_rows["candidates.json"], data_rows["facts.jsonl"], ev, "cpu", batch_size=20)
    b = E.score_qa(m, tok, qs, data_rows["candidates.json"], data_rows["facts.jsonl"], ev, "cpu", batch_size=1)
    assert max(abs(x - y) for ra, rb in zip(a, b) for x, y in zip(ra["scores"], rb["scores"])) < 1e-4


def test_s_mapping_uses_the_s_answer(contract, tok, data_rows, fz):
    m = tiny_model(seed=7)
    facts = {f["fact_id"]: f for f in data_rows["facts.jsonl"]}
    qa, cb = E.score_s_mapping(m, tok, data_rows["facts.jsonl"], data_rows["candidates.json"], fz.templates,
                               data_rows["dev_qa.jsonl"][:4], data_rows["train_S.jsonl"], contract.evaluation, "cpu")
    s_ans = {r["fact_id"]: r["answer_fact_id"] for r in data_rows["train_S.jsonl"]}
    for r in qa + cb:
        af = facts[s_ans[r["fact_id"]]]
        assert r["candidates"] == data_rows["candidates.json"][af["fact_id"]]
        assert r["candidates"][r["answer_index"]] == af["answer"] != facts[r["fact_id"]]["answer"]
    assert len(cb) == 120


def test_formal_evaluation_refuses_cpu(contract, tok, data_rows, fz):
    import pytest
    from metrix_e1 import mode as M
    from metrix_e1.errors import ImplementationFail
    for mode in (M.FORMAL_MODE, M.preflight_mode(contract)):
        with pytest.raises(ImplementationFail, match="evaluates only on the GPU"):
            E.evaluate_model(tiny_model(), tok, data_rows, fz.templates, contract.evaluation, mode, "cpu")


def test_think_marks_are_checked(contract, tok, data_rows):
    import dataclasses
    import pytest
    from metrix_e1.errors import ImplementationFail
    bad = dataclasses.replace(contract.evaluation, think_open_id=151643)
    with pytest.raises(ImplementationFail):
        E.em(Stub(151645), tok, data_rows["dev_qa.jsonl"][:1], data_rows["facts.jsonl"], bad, "cpu")
    rows = E.em(Stub(151645), tok, data_rows["dev_qa.jsonl"][:2], data_rows["facts.jsonl"], contract.evaluation, "cpu")
    assert [r["generated_ids"] for r in rows] == [[151645], [151645]] and all(r["output"] == "" for r in rows)


class NaNStub(Stub):
    def forward(self, input_ids, attention_mask=None, position_ids=None, past_key_values=None, use_cache=None):
        out = super().forward(input_ids, attention_mask, position_ids, past_key_values, use_cache)
        out.logits[:] = float("nan")
        return out


def test_nonfinite_in_evaluation_reaches_st6(contract, tok, data_rows, fz):
    """A non-finite score in an evaluation stops it with ST6 carrying the values, so stops.st6 decides: a selected
    configuration or a control -> IMPLEMENTATION_FAIL; otherwise the configuration is excluded."""
    import pytest
    from metrix_e1 import stops as STP
    from metrix_e1.train import NonFinite
    with pytest.raises(NonFinite) as e:
        E.score_qa(NaNStub(0), tok, data_rows["dev_qa.jsonl"][:2], data_rows["candidates.json"],
                   data_rows["facts.jsonl"], contract.evaluation, "cpu")
    assert e.value.stop == "ST6" and e.value.status is None and len(e.value.values) == 8
    with pytest.raises(STP.Stop) as s:
        STP.st6(fz, e.value.values, "evaluation of the selected F", True)
    assert s.value.status == "IMPLEMENTATION_FAIL"
    with pytest.raises(STP.Stop) as s:
        STP.st6(fz, e.value.values, "evaluation of F4 (search)", False)
    assert s.value.exclude_config


def test_test_split_needs_the_authorization(contract, tok, data_rows, fz):
    import pytest
    from metrix_e1 import leakage as LK
    from metrix_e1 import mode as M
    from metrix_e1.errors import ImplementationFail
    for auth in (None, LK.TestAuthorization(fz.record.commit, "a" * 64, "b" * 64)):
        with pytest.raises(ImplementationFail, match="TEST path"):
            E.evaluate_model(tiny_model(), tok, data_rows, fz.templates, contract.evaluation, M.FORMAL_MODE, "cpu",
                             split="test", test_authorization=auth, fz=fz)
    with pytest.raises(ImplementationFail,
                       match="^IMPLEMENTATION_FAIL: TEST path refused: the frozen files \\(fz\\) are needed"):
        E.evaluate_model(tiny_model(), tok, data_rows, fz.templates, contract.evaluation, M.FORMAL_MODE, "cpu",
                         split="test", test_authorization=LK.TestAuthorization(fz.record.commit, "a" * 64, "b" * 64),
                         fz=None)                                     # BE10: the fz is None branch
    for mode in (M.smoke_mode(3), M.preflight_mode(contract)):           # TEST is evaluated in formal mode only
        with pytest.raises(ImplementationFail, match="formal mode only"):
            E.evaluate_model(tiny_model(), tok, data_rows, fz.templates, contract.evaluation, mode, "cpu",
                             split="test", test_authorization=None, fz=fz)


class LateNaNStub(Stub):
    """Finite logits on the first forward (the prompt), NaN from the second on (the cached decoding steps)."""

    def forward(self, input_ids, attention_mask=None, position_ids=None, past_key_values=None, use_cache=None):
        out = super().forward(input_ids, attention_mask, position_ids, past_key_values, use_cache)
        if self.calls > 1:
            out.logits[:] = float("nan")
        return out


def test_nonfinite_logits_stop_em_generation(contract):
    """NaN logits stop greedy decoding with ST6 both on the prompt's forward and inside the decoding loop."""
    import pytest
    from metrix_e1.train import NonFinite
    with pytest.raises(NonFinite) as e:
        E.greedy_generate(NaNStub(0), [[1, 2, 3]], contract.evaluation, "cpu")
    assert e.value.stop == "ST6" and e.value.values and all(v != v for v in e.value.values)
    late = LateNaNStub(374)                                   # 374 is not a stop id: decoding goes on to step 2
    with pytest.raises(NonFinite) as e:
        E.greedy_generate(late, [[1, 2, 3]], contract.evaluation, "cpu")
    assert late.calls == 2 and e.value.stop == "ST6" and e.value.values and all(v != v for v in e.value.values)
    assert E.greedy_generate(Stub(374), [[1, 2, 3]], contract.evaluation, "cpu") == [
        [374] * contract.evaluation.max_new_tokens]                                          # control: finite
