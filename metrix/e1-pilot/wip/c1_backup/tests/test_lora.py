"""Arm L, the LoRA implemented in metrix_e1.train (no peft).

Implementation Task Order V1, section 6 item 4: at training step 0 the model's output equals the base model's (B = 0).
Owner, stage B item 5: the forward output equals W x + (alpha / r) B A x computed by hand; only LoRA parameters are
trainable; every base parameter is frozen and its hash is unchanged after training.
Protocol v1.1 section 4: LoRA on q, k, v, o, gate, up, down of every layer; alpha = 2 x rank; dropout 0; B = 0.
Random-initialisation models only; no weights are loaded.
"""
import math
import random

import torch

from conftest import tiny_model
from metrix_e1 import mode as M
from metrix_e1 import train as T


def _ids():
    return torch.tensor([[785, 6722, 315, 16447, 360, 376, 2898, 374, 444, 6130, 940, 13, 151643]])


def test_step0_output_equals_base(contract):
    base = tiny_model()
    lora = tiny_model()
    T.apply_lora(lora, contract.arms, 8, 101, expect_layers=None)
    x = _ids()
    with torch.no_grad():
        a = base(input_ids=x).logits
        b = lora(input_ids=x).logits
    assert torch.equal(a, b)
    # A is not zero (the adapter is live; only B = 0 makes the output equal)
    mods = [m for m in lora.modules() if isinstance(m, T.LoRALinear)]
    assert mods and all(m.lora_A.abs().sum() > 0 and m.lora_B.abs().sum() == 0 for m in mods)


def test_forward_equals_hand_computation():
    torch.manual_seed(3)
    lin = torch.nn.Linear(6, 5, bias=False).double()
    layer = T.LoRALinear(lin, rank=2, alpha=4.0, rng=random.Random(7)).double()
    with torch.no_grad():
        layer.lora_B.copy_(torch.randn(5, 2, dtype=torch.float64))
    x = torch.randn(3, 6, dtype=torch.float64)
    W, A, B = lin.weight.detach(), layer.lora_A.detach(), layer.lora_B.detach()
    want = torch.empty(3, 5, dtype=torch.float64)
    for n in range(3):                                   # W x + (alpha / r) B A x, element by element
        for i in range(5):
            wx = sum(W[i, j] * x[n, j] for j in range(6))
            bax = sum(B[i, k] * sum(A[k, j] * x[n, j] for j in range(6)) for k in range(2))
            want[n, i] = wx + (4.0 / 2) * bax
    got = layer(x)
    assert torch.allclose(got, want, rtol=0, atol=1e-12)
    assert layer.scaling == 2.0


def test_alpha_is_two_times_rank_on_all_modules_of_all_layers(contract):
    m = tiny_model(layers=3)
    paths = T.apply_lora(m, contract.arms, 32, 101, expect_layers=None)
    assert contract.arms.lora_alpha_per_rank == 2.0 and contract.arms.lora_dropout == 0.0
    want = ["model.layers.%d.%s.%s" % (i, p, n) for i in range(3)
            for n, p in [(n, "self_attn") for n in ("q_proj", "k_proj", "v_proj", "o_proj")]
            + [(n, "mlp") for n in ("gate_proj", "up_proj", "down_proj")]]
    assert paths == want
    for mod in m.modules():
        if isinstance(mod, T.LoRALinear):
            assert mod.rank == 32 and mod.alpha == 64 and mod.scaling == 2.0
            assert not any(isinstance(c, torch.nn.Dropout) for c in mod.modules())


def test_layer_count_is_checked_outside_smoke(contract):
    m = tiny_model()
    try:
        T.apply_lora(m, contract.arms, 8, 101, expect_layers=contract.arms.lora_layers)
    except Exception as e:
        assert "28" in str(e)
    else:
        raise AssertionError("a 2-layer model was accepted where the protocol puts LoRA on 28 layers")


def test_only_lora_trainable_and_base_hash_unchanged_after_training(tok, data_rows, contract):
    m = tiny_model()
    spec = [s for s in T.search_runs(contract, "L") if s.config_id == "L5"][0]      # rank 8, lr 1e-3
    base_before = T.params_sha256([(n, p) for n, p in m.named_parameters()])
    res = T.train_run(m, tok, data_rows, spec, contract, M.smoke_mode(3), "cpu")
    trainable = [n for n, p in m.named_parameters() if p.requires_grad]
    assert trainable and all(n.endswith(".lora_A") or n.endswith(".lora_B") for n in trainable)
    frozen = [(n.replace(".base.", "."), p) for n, p in m.named_parameters() if not p.requires_grad]
    assert len(frozen) == len(list(tiny_model().named_parameters()))
    assert T.params_sha256(frozen) == base_before                   # every base parameter unchanged
    assert res.frozen_sha256_before == res.frozen_sha256_after
    assert any(float(mod.lora_B.detach().abs().sum()) > 0 for mod in m.modules() if isinstance(mod, T.LoRALinear))
    assert res.steps_run == 3


def test_lora_a_values_come_from_rng_rule(contract):
    """B5: every value of A is r.uniform(-1/sqrt(in), 1/sqrt(in)) of r = rng_rule(TRAIN_SEED, 'lora_A:<path>')."""
    from metrix_e1 import frozen as FZ
    m = tiny_model()
    T.apply_lora(m, contract.arms, 8, 202, expect_layers=None)
    mod = m.model.layers[1].mlp.down_proj
    r = FZ.rng_rule(202, "lora_A:model.layers.1.mlp.down_proj")
    b = 1 / math.sqrt(mod.base.in_features)
    want = torch.tensor([r.uniform(-b, b) for _ in range(8 * mod.base.in_features)], dtype=torch.float64)
    assert torch.equal(mod.lora_A.detach(), want.reshape(8, -1).float())
    other = m.model.layers[1].mlp.up_proj
    assert not torch.equal(other.lora_A.detach()[:, :8], mod.lora_A.detach()[:, :8])     # one stream per module
