"""
CPU / static contract tests for Mini-Mythos baseline interfaces.

Full shape and call-count tests require torch and are marked NOT TESTED
if torch is unavailable. These tests do not claim language-learning success.
"""

import sys
from pathlib import Path

# Allow pytest discovery from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

from contracts import RecurrenceConfig, MiniMythosInterfaceStub, ParcaeBaselineAdapter


def test_recurrence_config_export():
    cfg = RecurrenceConfig()
    assert cfg.n_layers_in_prelude == 2
    assert cfg.mean_recurrence == 8
    assert cfg.tie_embeddings is True
    print("test_recurrence_config_export: PASS")


def test_stub_is_labeled():
    cfg = RecurrenceConfig(recurrent_embedding_dimension=32)
    stub = MiniMythosInterfaceStub(cfg, n_embd=16, vocab=64)
    assert "STUB" in stub.__class__.__name__.upper() or "stub" in stub.__class__.__doc__.lower()
    print("test_stub_is_labeled: PASS")


def test_adapter_exposes_native_modules():
    """Static structural check; full wrapping requires a real Parcae instance."""
    # Verify the adapter class stores the expected attribute names
    src = Path(__file__).resolve().parent / "contracts.py"
    text = src.read_text()
    for name in ["prelude", "adapter", "core_block", "C", "coda", "ln_f"]:
        assert f"self.{name} = parcae_model.transformer.{name}" in text
    print("test_adapter_exposes_native_modules: PASS")


def test_forward_signature_alignment():
    import inspect
    sig = inspect.signature(MiniMythosInterfaceStub.forward)
    params = list(sig.parameters)
    expected = ["self", "input_ids", "attention_mask", "position_ids",
                "labels", "return_logits", "num_steps_pair"]
    assert params == expected
    print("test_forward_signature_alignment: PASS")


def test_shapes_sharing_and_calls():
    if not TORCH_AVAILABLE:
        print("test_shapes_sharing_and_calls: NOT TESTED (no torch)")
        return

    cfg = RecurrenceConfig(
        n_layers_in_prelude=1,
        n_layers_in_recurrent_block=1,
        n_layers_in_coda=1,
        recurrent_embedding_dimension=32,
        tie_embeddings=True,
    )
    model = MiniMythosInterfaceStub(cfg, n_embd=16, vocab=64)
    model.eval()

    B, T = 2, 8
    input_ids = torch.randint(0, 64, (B, T))
    labels = torch.randint(0, 64, (B, T))

    out = model(input_ids, labels=labels, return_logits=False)
    assert isinstance(out, dict)
    assert set(out) == {"loss", "logits", "log_ppl"}
    assert out["logits"] is None          # labels present + return_logits=False
    assert out["loss"] is not None
    assert torch.isfinite(out["loss"])

    out2 = model(input_ids, labels=labels, return_logits=True)
    assert out2["logits"].shape == (B, T, 64)

    # Parameter sharing
    assert model.lm_head.weight.data_ptr() == model.wte.weight.data_ptr()

    # Core call count (stub uses fixed 2 steps)
    assert model._core_call_count == 2

    # Separation
    prelude_ids = {id(p) for p in model.prelude.parameters()}
    core_ids = {id(p) for p in model.core_block.parameters()}
    coda_ids = {id(p) for p in model.coda.parameters()}
    assert prelude_ids.isdisjoint(core_ids)
    assert core_ids.isdisjoint(coda_ids)

    print("test_shapes_sharing_and_calls: PASS")


def test_parcae_adapter_requires_real_model():
    """Adapter cannot be instantiated without a Parcae-like object."""
    if not TORCH_AVAILABLE:
        print("test_parcae_adapter_requires_real_model: NOT TESTED (no torch)")
        return
    try:
        ParcaeBaselineAdapter(None)  # type: ignore
        raise AssertionError("should have failed")
    except (AttributeError, TypeError):
        print("test_parcae_adapter_requires_real_model: PASS")


if __name__ == "__main__":
    test_recurrence_config_export()
    test_stub_is_labeled()
    test_adapter_exposes_native_modules()
    test_forward_signature_alignment()
    test_shapes_sharing_and_calls()
    test_parcae_adapter_requires_real_model()
    print("CONTRACT TESTS FINISHED")
    print("NOTE: Shape/call tests are NOT TESTED without torch.")
    print("These checks do not represent language-learning success.")
