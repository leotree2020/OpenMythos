import os
import sys

import pytest
import torch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "training"))

import open_mythos.main as om  # noqa: E402
from depth_ablation import apply_depth_ablation, check_matches_original  # noqa: E402
from open_mythos.main import (  # noqa: E402
    MythosConfig,
    OpenMythos,
    RecurrentBlock,
    precompute_rope_freqs,
)

B, T = 2, 8


def cfg(**overrides) -> MythosConfig:
    defaults = dict(
        vocab_size=200,
        dim=64,
        n_heads=4,
        n_kv_heads=2,
        max_seq_len=32,
        max_loop_iters=3,
        prelude_layers=1,
        coda_layers=1,
        attn_type="gqa",
        n_experts=4,
        n_shared_experts=1,
        n_experts_per_tok=2,
        expert_dim=16,
        act_threshold=0.99,
        lora_rank=4,
        kv_lora_rank=16,
        q_lora_rank=32,
        qk_rope_head_dim=8,
        qk_nope_head_dim=8,
        v_head_dim=8,
    )
    defaults.update(overrides)
    return MythosConfig(**defaults)


def inputs(c: MythosConfig):
    torch.manual_seed(0)
    h = torch.randn(B, T, c.dim)
    e = torch.randn(B, T, c.dim)
    freqs = precompute_rope_freqs(c.dim // c.n_heads, c.max_seq_len)[:T]
    return h, e, freqs


@pytest.mark.parametrize("act_threshold", [0.99, 1e9])
@pytest.mark.parametrize("n_loops", [1, 3, 6])
def test_switches_off_match_original(act_threshold, n_loops):
    c = cfg(act_threshold=act_threshold)
    block = RecurrentBlock(c).eval()
    h, e, freqs = inputs(c)
    ref = block(h, e, freqs, n_loops=n_loops)
    apply_depth_ablation(block)
    assert torch.equal(block(h, e, freqs, n_loops=n_loops), ref)
    check_matches_original(block, h, e, freqs, None, n_loops)


@pytest.mark.parametrize("attn_type", ["gqa", "mla"])
def test_full_model_switches_off_match_original(attn_type):
    model = OpenMythos(cfg(attn_type=attn_type)).eval()
    ids = torch.randint(0, 200, (B, T))
    with torch.no_grad():
        ref = model(ids, n_loops=6)
        apply_depth_ablation(model)
        assert torch.equal(model(ids, n_loops=6), ref)


def _zero_halting(block):
    block.act.halt.weight.data.zero_()
    block.act.halt.bias.data.fill_(-1e4)  # p = 0: nothing ever halts


def test_original_leaves_mass_unassigned():
    c = cfg()
    block = apply_depth_ablation(RecurrentBlock(c))
    _zero_halting(block)
    h, e, freqs = inputs(c)
    out = block(h, e, freqs, n_loops=5)
    assert torch.allclose(out, torch.zeros_like(out))


def test_final_remainder_assigns_mass_to_last_loop():
    c = cfg()
    block = apply_depth_ablation(RecurrentBlock(c), act_final_remainder=True)
    _zero_halting(block)
    states = []
    block.injection.register_forward_hook(lambda m, i, o: states.append(o))
    h, e, freqs = inputs(c)
    out = block(h, e, freqs, n_loops=5)
    assert len(states) == 5
    assert torch.allclose(out, states[-1])


@pytest.mark.parametrize(
    "clamp,expected", [(True, [0, 1, 2, 2, 2, 2]), (False, list(range(6)))]
)
def test_clamp_loop_emb(monkeypatch, clamp, expected):
    import depth_ablation

    seen = []
    orig = om.loop_index_embedding

    def spy(h, loop_t, loop_dim, theta=10000.0):
        seen.append(loop_t)
        return orig(h, loop_t, loop_dim, theta)

    monkeypatch.setattr(depth_ablation, "loop_index_embedding", spy)
    c = cfg(act_threshold=1e9)  # max_loop_iters=3
    block = apply_depth_ablation(RecurrentBlock(c), clamp_loop_emb=clamp)
    h, e, freqs = inputs(c)
    block(h, e, freqs, n_loops=6)
    assert seen == expected


def test_last_loops_run():
    h, e, freqs = inputs(cfg())
    block = apply_depth_ablation(RecurrentBlock(cfg(act_threshold=1e9)))
    block(h, e, freqs, n_loops=6)
    assert block.last_loops_run == 6
    block = apply_depth_ablation(RecurrentBlock(cfg(act_threshold=0.0)))
    block(h, e, freqs, n_loops=6)
    assert block.last_loops_run == 1


def _const_halting(block, p):
    block.act.halt.weight.data.zero_()
    block.act.halt.bias.data.fill_(float(torch.logit(torch.tensor(p))))


def test_b2_normalizes_to_convex_combination():
    from depth_ablation import RULES

    c = cfg(act_threshold=1e9)  # never halts: every weight is p
    block = apply_depth_ablation(RecurrentBlock(c), **RULES["B2"])
    _const_halting(block, 0.1)
    states = []
    block.injection.register_forward_hook(lambda m, i, o: states.append(o))
    h, e, freqs = inputs(c)
    out = block(h, e, freqs, n_loops=5)
    assert torch.allclose(out, torch.stack(states).mean(0), atol=1e-5)


def test_b1_and_b2_exclusive():
    with pytest.raises(ValueError):
        apply_depth_ablation(
            RecurrentBlock(cfg()), act_final_remainder=True, act_normalize=True
        )


@pytest.mark.parametrize(
    "n_loops,executed,halt_idx,below", [(6, 4, 4, 0.0), (3, 3, 0, 1.0)]
)
def test_stats(n_loops, executed, halt_idx, below):
    from depth_ablation import new_stats

    c = cfg()  # threshold 0.99; p = 0.3 → crosses on loop 4 (cum 1.2)
    block = apply_depth_ablation(RecurrentBlock(c))
    _const_halting(block, 0.3)
    h, e, freqs = inputs(c)
    ref = block(h, e, freqs, n_loops=n_loops)
    block.stats = new_stats(8)
    out = block(h, e, freqs, n_loops=n_loops)
    s = block.stats
    assert torch.equal(out, ref)  # recording does not change the output
    assert s["forward_calls"] == 1 and s["loops_executed_sum"] == executed
    assert s["halt_step_hist"][halt_idx] == B * T
    assert s["weight_sum_below_0_99"] / s["tokens"] == below
    assert s["loop_calls"][:executed].tolist() == [1] * executed
    assert s["loop_calls"][executed:].sum() == 0
    check_matches_original(block, h, e, freqs, None, n_loops)
