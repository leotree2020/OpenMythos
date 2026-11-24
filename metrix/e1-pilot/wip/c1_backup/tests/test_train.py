"""Training contract and run plan (protocol v1.1 sections 4 and 7; section 8 steps 4-6).

Implementation Task Order V1, section 6 item 6: S and Y use F's selected configuration and are not searched.
Owner, stage B item 7: F and A train every parameter, L only the LoRA parameters; the number of trainable
parameters of each arm is checked (random models, and the protocol architecture on the meta device: no memory, no
weights).
Task order section 7: formal mode cannot use the shortened smoke step count.
Also: the schedule (B1-B3), weight-decay groups (B7), the padded CE (B4), the selection rule of section 7.
"""
import math
import re

import pytest
import torch

from conftest import tiny_model
from metrix_e1 import mode as M
from metrix_e1 import train as T
from metrix_e1.contract import protocol_line
from metrix_e1.errors import ImplementationFail

SELECTED = {"F": "F3", "L": "L2", "A": "A5"}


# ----------------------------------------------------------------------------------------- plan (item 6)

def test_plan_has_30_runs_and_s_y_inherit_f(contract):
    plan = T.training_plan(contract, SELECTED)
    assert len(plan) == 30 == contract.arms.counts["total_training_runs"]
    search = [s for s in plan if s.phase == "search"]
    assert [s.config_id for s in search] == ["F%d" % i for i in range(1, 7)] + ["L%d" % i for i in range(1, 7)] + \
        ["A%d" % i for i in range(1, 7)]
    assert {s.seed for s in search} == {101}
    assert not [s for s in search if s.arm in ("S", "Y")]
    f3 = [c for c in contract.arms.configs["F"] if c["id"] == "F3"][0]
    for arm in ("S", "Y"):
        runs = [s for s in plan if s.arm == arm]
        assert sorted(s.seed for s in runs) == [101, 202, 303]
        for s in runs:
            assert s.config_id == "F3"
            assert s.cfg["learning_rate"] == f3["learning_rate"] and s.cfg["weight_decay"] == f3["weight_decay"]
            assert set(s.cfg) == {"id", "learning_rate", "weight_decay"}
    for arm in ("F", "L", "A"):
        extra = [s for s in plan if s.arm == arm and s.phase == "seeds"]
        assert [(s.config_id, s.seed) for s in extra] == [(SELECTED[arm], 202), (SELECTED[arm], 303)]
    with pytest.raises(ValueError):
        T.search_runs(contract, "S")
    with pytest.raises(ValueError):
        T.search_runs(contract, "Y")


def test_s_and_y_follow_another_f_selection(contract):
    plan = T.training_plan(contract, {"F": "F6", "L": "L1", "A": "A1"})
    f6 = [c for c in contract.arms.configs["F"] if c["id"] == "F6"][0]
    for s in plan:
        if s.arm in ("S", "Y"):
            assert (s.config_id, s.cfg["learning_rate"], s.cfg["weight_decay"]) == ("F6", f6["learning_rate"], f6["weight_decay"])


def test_selection_rule(contract):
    def res(acc, dnll, finite=(True,) * 6):
        return [{"config_id": "F%d" % (i + 1), "learning_rate": c["learning_rate"], "acc": a, "dnll": d, "finite": f}
                for i, (c, a, d, f) in enumerate(zip(contract.arms.configs["F"], acc, dnll, finite))]
    one = [0.5] * 6
    assert T.select_config(contract, "F", res([0.5, 0.6, 0.7, 0.7, 0.4, 0.4], one))[0] == "F3"
    assert T.select_config(contract, "F", res([0.7, 0.7, 0.7, 0.7, 0.4, 0.4], [0.3, 0.2, 0.1, 0.4, 0, 0]))[0] == "F3"
    assert T.select_config(contract, "F", res([0.6] * 6, [0.1] * 6))[0] == "F1"            # lr 1e-5, index 1
    assert T.select_config(contract, "F", res([0.6, 0.6, 0.6, 0.6, 0.9, 0.6], one, [True] * 4 + [False, True]))[0] == "F1"
    assert T.select_config(contract, "F", res([0.6, 0.6, 0.6, 0.6, float("nan"), 0.6], one))[0] == "F1"
    with pytest.raises(ImplementationFail):
        T.select_config(contract, "F", res([0.6] * 6, one, [False] * 6))


# -------------------------------------------------------------------------------- trainable counts (Owner 7)

def _independent_counts(cfg, rank):
    h, inter, L = cfg.hidden_size, cfg.intermediate_size, cfg.num_hidden_layers
    q, kv = cfg.num_attention_heads * cfg.head_dim, cfg.num_key_value_heads * cfg.head_dim
    per_layer = h * q + 2 * h * kv + q * h + 3 * h * inter + 2 * cfg.head_dim + 2 * h
    full = cfg.vocab_size * h + L * per_layer + h                    # tied embedding / lm_head counted once
    shapes = [(h, q), (h, kv), (h, kv), (q, h), (h, inter), (h, inter), (inter, h)]     # (in, out)
    lora = L * sum(rank * (i + o) for i, o in shapes)
    return full, lora


def _spec(contract, arm, cid):
    if arm in ("S", "Y"):
        return [s for s in T.seed_runs(contract, SELECTED) if s.arm == arm][0]
    return [s for s in T.search_runs(contract, arm) if s.config_id == cid][0]


@pytest.mark.parametrize("arm,cid", [("F", "F1"), ("A", "A1"), ("S", None), ("Y", None), ("L", "L1"), ("L", "L2")])
def test_trainable_counts_random_model(contract, arm, cid):
    m = tiny_model()
    spec = _spec(contract, arm, cid)
    T.prepare_arm(m, spec, contract, M.smoke_mode(3))
    full, lora = _independent_counts(m.config, spec.cfg.get("rank", 0))
    want = lora if arm == "L" else full
    assert T.count_trainable(m) == want
    if arm == "L":
        assert all(p.requires_grad == (n.endswith("lora_A") or n.endswith("lora_B")) for n, p in m.named_parameters())
    else:
        assert all(p.requires_grad for p in m.parameters())


@pytest.mark.parametrize("arm,cid", [("F", "F1"), ("A", "A1"), ("S", None), ("Y", None), ("L", "L1"), ("L", "L2")])
def test_trainable_counts_protocol_architecture(contract, fz, real_config, arm, cid):
    """The pinned config.json on the meta device: F, A, S, Y train all 1,720,574,976 parameters (protocol section 7);
    L with rank 32 trains 3,486 x 10^4 (protocol section 7: '秩 32 时 3,486 万参数'), rank 8 a quarter of that."""
    from transformers import Qwen3ForCausalLM
    with torch.device("meta"):
        m = Qwen3ForCausalLM(real_config)
    spec = _spec(contract, arm, cid)
    T.prepare_arm(m, spec, contract, M.FORMAL_MODE)          # formal: LoRA on exactly the protocol's 28 layers
    full, lora = _independent_counts(real_config, spec.cfg.get("rank", 0))
    line = protocol_line(fz.protocol_text, "- 唯一参数 ")
    unique = int(re.match(r"- 唯一参数 ([0-9,]+)", line).group(1).replace(",", ""))
    assert full == unique == 1720574976
    if arm == "L":
        assert T.count_trainable(m) == lora
        if spec.cfg["rank"] == 32:
            wan = int(re.search(r"适配器\(秩 32 时 ([0-9,]+) 万参数", fz.protocol_text).group(1).replace(",", ""))
            assert T.count_trainable(m) // 10000 == wan == 3486
    else:
        assert T.count_trainable(m) == unique


# -------------------------------------------------------------------------------------- formal vs smoke

def test_formal_mode_cannot_take_a_shortened_step_count(contract):
    with pytest.raises(ValueError):
        M.RunMode(M.FORMAL, 3)
    assert M.FORMAL_MODE.steps(contract.training.total_steps) == 300
    with pytest.raises(ValueError):
        M.smoke_mode(300).steps(contract.training.total_steps)
    with pytest.raises(ValueError):
        M.smoke_mode(0)
    assert M.preflight_mode(contract).steps(contract.training.total_steps) == contract.preflight_steps == 20


def test_formal_mode_does_not_train_on_cpu(tok, data_rows, contract):
    m = tiny_model()
    before = T.state_sha256(m)
    with pytest.raises(ImplementationFail, match="trains only on the GPU"):
        T.train_run(m, tok, data_rows, _spec(contract, "F", "F1"), contract, M.FORMAL_MODE, "cpu")
    assert T.state_sha256(m) == before


def test_run_length_comes_from_the_mode(tok, data_rows, contract, monkeypatch):
    calls = []
    orig = M.RunMode.steps

    def spy(self, n):
        calls.append(n)
        return orig(self, n)
    monkeypatch.setattr(M.RunMode, "steps", spy)
    res = T.train_run(tiny_model(), tok, data_rows, _spec(contract, "F", "F5"), contract, M.smoke_mode(2), "cpu")
    assert calls == [contract.training.total_steps] and res.steps_run == 2 and len(res.log) == 2


# ------------------------------------------------------------------------------------------ schedule (B1-B3)

def test_lr_schedule(contract):
    tr = contract.training
    peak = 3e-5
    assert T.lr_at(1, peak, tr) == peak / 15
    assert T.lr_at(15, peak, tr) == peak
    assert math.isclose(T.lr_at(300, peak, tr), 0.1 * peak, rel_tol=1e-12)
    lrs = [T.lr_at(s, peak, tr) for s in range(15, 301)]
    assert all(a >= b for a, b in zip(lrs, lrs[1:]))
    assert [T.lr_at(s, peak, tr) for s in range(1, 16)] == [peak * s / 15 for s in range(1, 16)]
    for bad in (0, 301):
        with pytest.raises(ValueError):
            T.lr_at(bad, peak, tr)


def test_batch_schedule(contract):
    from metrix_e1 import frozen as FZ
    tr = contract.training
    sch = T.batch_schedule(tr, 120, 8, 101)
    assert [s for s, _, _ in sch] == list(range(1, 301))
    for e in range(1, 21):
        rows = [i for s, ep, b in sch if ep == e for i in b]
        assert sorted(rows) == list(range(120))
        r = FZ.rng_rule(101, "order:%d" % e)
        p = list(range(120))
        r.shuffle(p)
        assert rows == p
    assert T.batch_schedule(tr, 120, 8, 101) == sch
    assert T.batch_schedule(tr, 120, 8, 202) != sch
    y = T.batch_schedule(tr, 240, 16, 303)
    assert len(y) == 300 and all(len(b) == 16 for _, _, b in y)


def test_anchor_schedule(contract):
    a = contract.arms
    assert T.anchor_docs(1, a) == [4, 5, 6, 7]
    assert T.anchor_docs(127, a) == [508, 509, 510, 511]
    assert T.anchor_docs(128, a) == [0, 1, 2, 3]
    used = {d for s in range(1, 301) for d in T.anchor_docs(s, a)}
    assert used == set(range(512))


# ------------------------------------------------------------------------------------ loss and optimizer

def test_padded_ce_is_token_weighted_and_ignores_padding():
    torch.manual_seed(0)
    logits = torch.randn(2, 4, 7)
    ids = torch.tensor([[1, 2, 3, 0], [4, 5, 6, 2]])
    mask = torch.tensor([[1, 1, 1, 0], [1, 1, 1, 1]])
    lp = torch.log_softmax(logits, -1)
    terms = [-lp[0, 0, 2], -lp[0, 1, 3], -lp[1, 0, 5], -lp[1, 1, 6], -lp[1, 2, 2]]
    assert torch.allclose(T.token_ce(logits, ids, mask), sum(terms) / 5)
    logits2 = logits.clone()
    logits2[0, 2:] = 100.0                     # positions whose target is padding (or nothing)
    assert torch.equal(T.token_ce(logits2, ids, mask), T.token_ce(logits, ids, mask))


def test_training_input_ends_with_endoftext(tok, contract):
    seqs = T.encode_corpus(tok, [{"text": "The capital of Krultrouth is Linnuth."}], contract.evaluation.endoftext_id)
    assert seqs[0][-1] == 151643 and seqs[0][:-1] == tok.encode("The capital of Krultrouth is Linnuth.", add_special_tokens=False)


def test_weight_decay_only_on_2d(contract):
    m = tiny_model()
    m.requires_grad_(True)
    opt = T.make_optimizer(list(m.parameters()), contract.training, 1e-4, 0.1)
    decay, other = opt.param_groups
    assert decay["weight_decay"] == 0.1 and other["weight_decay"] == 0.0
    assert all(p.ndim == 2 for p in decay["params"]) and all(p.ndim != 2 for p in other["params"])
    assert any(p is m.model.embed_tokens.weight for p in decay["params"])
    assert opt.defaults["betas"] == (0.9, 0.999) and opt.defaults["eps"] == 1e-8


def test_smoke_run_is_reproducible(tok, data_rows, contract):
    spec = _spec(contract, "F", "F5")
    a, b = tiny_model(), tiny_model()
    ra = T.train_run(a, tok, data_rows, spec, contract, M.smoke_mode(2), "cpu")
    rb = T.train_run(b, tok, data_rows, spec, contract, M.smoke_mode(2), "cpu")
    assert T.state_sha256(a) == T.state_sha256(b)
    assert [e["loss"] for e in ra.log] == [e["loss"] for e in rb.log]
    assert ra.log[0]["lr"] == spec.cfg["learning_rate"] / 15
    assert ra.log[0]["rows"] == T.batch_schedule(contract.training, 120, 8, 101)[0][2]


def test_preflight_runs_exactly_the_protocol_steps(tok, data_rows, contract):
    with pytest.raises(ImplementationFail, match="trains only on the GPU"):
        T.train_run(tiny_model(), tok, data_rows, _spec(contract, "F", "F1"), contract, M.preflight_mode(contract), "cpu")
    with pytest.raises(ImplementationFail, match="preflight runs the protocol's 20 steps"):
        T.train_run(tiny_model(), tok, data_rows, _spec(contract, "F", "F1"), contract, M.RunMode(M.PREFLIGHT, 5), "cuda")
    with pytest.raises(ImplementationFail, match="preflight runs the first configuration F-F1-seed101"):
        T.train_run(tiny_model(), tok, data_rows, _spec(contract, "F", "F2"), contract, M.preflight_mode(contract), "cuda")


def test_kl_call_site_order_and_gradient(tok, data_rows, contract, monkeypatch):
    """Owner stage B item 6 at the call site: train_run passes (trained-model logits, base logits) in that order; the
    first carries the gradient, the second does not, and the logged KL is KL(p_base || p_theta) of those logits."""
    seen = []
    real = T.anchor_kl

    def spy(lt, lb, mask):
        seen.append((lt.requires_grad, lb.requires_grad))
        val = real(lt, lb, mask)
        lp_t = torch.log_softmax(lt[:, :-1].float(), -1)
        lp_b = torch.log_softmax(lb[:, :-1].float(), -1)
        m = mask[:, 1:].float()
        hand = ((lp_b.exp() * (lp_b - lp_t)).sum(-1) * m).sum() / m.sum()
        rev = ((lp_t.exp() * (lp_t - lp_b)).sum(-1) * m).sum() / m.sum()
        seen.append((float(val.detach()), float(hand.detach()), float(rev.detach())))
        return val
    monkeypatch.setattr(T, "anchor_kl", spy)
    T.train_run(tiny_model(), tok, data_rows, _spec(contract, "A", "A6"), contract, M.smoke_mode(2), "cpu")
    assert seen[0] == (True, False) and seen[2] == (True, False)
    val, hand, rev = seen[3]
    assert val > 0 and abs(val - hand) < 1e-6 and abs(val - rev) > 1e-9


def test_kl_term_moves_the_parameters(tok, data_rows, contract, monkeypatch):
    """The KL term reaches the gradient: A1 and A3 differ only in lambda (0.3 vs 3.0, same learning rate), so their
    parameters after 2 steps differ. Control: with the KL detached (what a wrong call site would do) lambda has no
    effect and the two runs end bit-identical, so this test catches a detached KL."""
    a1, a3 = _spec(contract, "A", "A1"), _spec(contract, "A", "A3")
    assert a1.cfg["learning_rate"] == a3.cfg["learning_rate"] and a1.cfg["anchor_lambda"] != a3.cfg["anchor_lambda"]
    attached = [T.state_sha256(_trained(tok, data_rows, contract, s, 2)) for s in (a1, a3)]
    assert attached[0] != attached[1]
    real = T.anchor_kl
    monkeypatch.setattr(T, "anchor_kl", lambda lt, lb, m: real(lt, lb, m).detach())
    detached = [T.state_sha256(_trained(tok, data_rows, contract, s, 2)) for s in (a1, a3)]
    assert detached[0] == detached[1]


def _trained(tok, data_rows, contract, spec, steps):
    m = tiny_model()
    T.train_run(m, tok, data_rows, spec, contract, M.smoke_mode(steps), "cpu")
    return m
