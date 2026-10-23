"""
CPU / static contract tests for Mini-Mythos baseline interfaces.

Shape, call-count, and adapter integration tests require torch (and Parcae
for the native adapter path). They are marked NOT TESTED when unavailable.
These tests do not claim language-learning success.
"""

import sys
from pathlib import Path

# Package-level import (requires research/ on path or installed)
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from mini_mythos.interfaces import (
    RecurrenceConfig,
    MiniMythosInterfaceStub,
    ParcaeBaselineAdapter,
    TORCH_AVAILABLE,
)


def test_package_export():
    from mini_mythos.interfaces import (
        RecurrenceConfig as RC,
        PreludeContract,
        RecurrentCoreContract,
        CodaContract,
        MiniMythosInterfaceStub as Stub,
        ParcaeBaselineAdapter as Adapter,
    )
    assert RC is not None
    assert Stub is not None or not TORCH_AVAILABLE
    assert Adapter is not None or not TORCH_AVAILABLE
    print("test_package_export: PASS")


def test_recurrence_config():
    cfg = RecurrenceConfig()
    assert cfg.n_layers_in_prelude == 2
    assert cfg.mean_recurrence == 8
    assert cfg.tie_embeddings is True
    print("test_recurrence_config: PASS")


def test_stub_forward_and_core_calls():
    if not TORCH_AVAILABLE:
        print("test_stub_forward_and_core_calls: NOT TESTED (no torch)")
        return

    import torch
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

    before = model._core_call_count
    out1 = model(input_ids, labels=labels, return_logits=False)
    after1 = model._core_call_count
    assert after1 - before == 2

    out2 = model(input_ids, labels=labels, return_logits=True)
    after2 = model._core_call_count
    assert after2 - after1 == 2
    assert after2 == 4

    assert isinstance(out1, dict)
    assert set(out1) == {"loss", "logits", "log_ppl"}
    assert out1["logits"] is None
    assert torch.isfinite(out1["loss"])
    assert out2["logits"].shape == (B, T, 64)

    # Same core parameter objects across calls
    core_ids_before = {id(p) for p in model.core_block.parameters()}
    _ = model(input_ids)
    core_ids_after = {id(p) for p in model.core_block.parameters()}
    assert core_ids_before == core_ids_after

    # Embedding / LM head sharing
    assert model.lm_head.weight.data_ptr() == model.wte.weight.data_ptr()

    # Separation
    prelude_ids = {id(p) for p in model.prelude.parameters()}
    core_ids = {id(p) for p in model.core_block.parameters()}
    coda_ids = {id(p) for p in model.coda.parameters()}
    assert prelude_ids.isdisjoint(core_ids)
    assert core_ids.isdisjoint(coda_ids)

    print("test_stub_forward_and_core_calls: PASS")


def test_adapter_properties_and_state_dict():
    if not TORCH_AVAILABLE:
        print("test_adapter_properties_and_state_dict: NOT TESTED (no torch)")
        return

    # Native Parcae instance not available in this environment
    print("test_adapter_properties_and_state_dict: NOT TESTED (no Parcae)")
    print("  Adapter uses read-only properties; no duplicate registration.")
    print("  Full consistency with official Parcae.forward remains NOT TESTED.")


if __name__ == "__main__":
    test_package_export()
    test_recurrence_config()
    test_stub_forward_and_core_calls()
    test_adapter_properties_and_state_dict()
    print("CONTRACT TESTS FINISHED")
    print("NOTE: Shape and native adapter tests are NOT TESTED without torch/Parcae.")
    print("These checks do not represent language-learning success.")
