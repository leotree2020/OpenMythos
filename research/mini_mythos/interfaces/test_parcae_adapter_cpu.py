"""
CPU integration tests for ParcaeBaselineAdapter against pinned Parcae.

Pinned Parcae: 69284c13746e849104f738d6d1a347b1f457df76

These tests require:
  - torch (CPU is sufficient)
  - the official parcae package importable (parcae_lm)

If either is missing the tests are SKIPPED, never counted as PASS.
They do not train, do not use GPU, and do not claim language learning.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

try:
    import torch
    TORCH_OK = True
except ImportError:
    TORCH_OK = False

try:
    from parcae_lm.models.parcae import Parcae, ParcaeConfig
    PARCAE_OK = True
except ImportError:
    PARCAE_OK = False

from mini_mythos.interfaces import ParcaeBaselineAdapter


def _skip(reason: str) -> None:
    print(f"SKIPPED: {reason}")


def _make_model():
    cfg = ParcaeConfig(
        n_embd=64,
        intermediate_size=128,
        num_attention_heads=4,
        num_key_value_heads=4,
        vocab_size=128,
        padded_vocab_size=128,
        block_size=16,
        n_layers_in_prelude=1,
        n_layers_in_recurrent_block=1,
        n_layers_in_coda=1,
        mean_recurrence=2,
        mean_backprop_depth=1,
        recurrent_embedding_dimension=64,
        recurrent_intermediation_embedding_dimension=128,
        prelude_norm=True,
        injection_type="diagonal",
        state_init="normal",
        tie_embeddings=True,
        use_fused_head="pytorch",
    )
    return Parcae(cfg)


def test_module_identity():
    if not (TORCH_OK and PARCAE_OK):
        _skip("torch or parcae unavailable")
        return
    model = _make_model()
    adapter = ParcaeBaselineAdapter(model)
    assert adapter.prelude is model.transformer.prelude
    assert adapter.adapter is model.transformer.adapter
    assert adapter.core_block is model.transformer.core_block
    assert adapter.C is model.transformer.C
    assert adapter.coda is model.transformer.coda
    assert adapter.ln_f is model.transformer.ln_f
    print("PASS: module identity")


def test_parameter_identity_and_count():
    """
    42 parameters is the count of unique tensors returned by model.parameters()
    on this minimal config. Because tie_embeddings=True, lm_head.weight is not
    a separate entry; it aliases transformer.wte.weight.
    """
    if not (TORCH_OK and PARCAE_OK):
        _skip("torch or parcae unavailable")
        return
    model = _make_model()
    adapter = ParcaeBaselineAdapter(model)
    model_params = list(model.parameters())
    adapter_params = list(adapter.parameters())
    assert len(model_params) == 42, f"expected 42, got {len(model_params)}"
    assert len(adapter_params) == 42
    for a, b in zip(model_params, adapter_params):
        assert a.data_ptr() == b.data_ptr()
    # tied embedding
    assert model.lm_head.weight.data_ptr() == model.transformer.wte.weight.data_ptr()
    print("PASS: parameter identity and count (42)")


def test_state_dict_no_aliases():
    if not (TORCH_OK and PARCAE_OK):
        _skip("torch or parcae unavailable")
        return
    model = _make_model()
    adapter = ParcaeBaselineAdapter(model)
    keys = list(adapter.state_dict().keys())
    aliases = [k for k in keys if k.startswith(
        ("prelude.", "core_block.", "coda.", "adapter.", "C.", "ln_f.")
    )]
    assert aliases == []
    assert all(k.startswith("parcae.") for k in keys)
    print(f"PASS: state_dict no aliases ({len(keys)} keys)")


def test_forward_consistency():
    if not (TORCH_OK and PARCAE_OK):
        _skip("torch or parcae unavailable")
        return
    model = _make_model()
    adapter = ParcaeBaselineAdapter(model)
    torch.manual_seed(0)
    ids = torch.randint(0, 128, (2, 8))
    pair = (torch.tensor(1), torch.tensor(1))
    torch.manual_seed(0)
    o1 = adapter(ids, return_logits=True, num_steps_pair=pair)
    torch.manual_seed(0)
    o2 = model(ids, return_logits=True, num_steps_pair=pair)
    assert o1["logits"].shape == o2["logits"].shape
    assert torch.allclose(o1["logits"], o2["logits"], atol=1e-5)
    # labels + return_logits=False → logits is None
    labels = torch.randint(0, 128, (2, 8))
    out = adapter(ids, labels=labels, return_logits=False, num_steps_pair=pair)
    assert out["logits"] is None
    assert out["loss"] is not None
    print("PASS: forward consistency")


def test_backward_and_participation():
    """
    On this config, value_embeds.2.weight receives no gradient.
    This is expected: has_ve() only creates value embeddings for selected
    layer indices, and layer 2 (the single coda layer) is not used as a
    value-embed source under the current has_ve rule for a 3-layer effective
    stack. The remaining 41 parameters do receive finite gradients.
    """
    if not (TORCH_OK and PARCAE_OK):
        _skip("torch or parcae unavailable")
        return
    model = _make_model()
    adapter = ParcaeBaselineAdapter(model)
    model.zero_grad()
    ids = torch.randint(0, 128, (2, 8))
    labels = torch.randint(0, 128, (2, 8))
    out = adapter(ids, labels=labels, num_steps_pair=(torch.tensor(1), torch.tensor(1)))
    out["loss"].backward()

    no_grad = [n for n, p in model.named_parameters() if p.grad is None]
    assert no_grad == ["value_embeds.2.weight"], f"unexpected no-grad: {no_grad}"

    grads = [p.grad for p in model.parameters() if p.grad is not None]
    assert len(grads) == 41
    assert all(torch.isfinite(g).all() for g in grads)

    prelude_has = any(
        p.grad is not None and p.grad.abs().sum() > 0
        for p in model.transformer.prelude.parameters()
    )
    core_has = any(
        p.grad is not None and p.grad.abs().sum() > 0
        for p in model.transformer.core_block.parameters()
    )
    coda_has = any(
        p.grad is not None and p.grad.abs().sum() > 0
        for p in model.transformer.coda.parameters()
    )
    assert prelude_has and core_has and coda_has
    print("PASS: backward and participation (expected no-grad: value_embeds.2.weight)")


if __name__ == "__main__":
    print(f"torch={TORCH_OK} parcae={PARCAE_OK}")
    if TORCH_OK:
        print(f"torch version: {torch.__version__}")
    passed = skipped = failed = 0
    for fn in [
        test_module_identity,
        test_parameter_identity_and_count,
        test_state_dict_no_aliases,
        test_forward_consistency,
        test_backward_and_participation,
    ]:
        try:
            before = skipped
            fn()
            # crude: if the function printed SKIPPED it returns without assert
            # we detect by checking stdout is hard; instead re-check availability
            if not (TORCH_OK and PARCAE_OK):
                skipped += 1
            else:
                passed += 1
        except Exception as e:
            failed += 1
            print(f"FAIL: {fn.__name__}: {e}")
    print(f"PASS={passed} FAIL={failed} SKIPPED={skipped}")
    sys.exit(0 if failed == 0 else 1)
