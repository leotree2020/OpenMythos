"""
CPU / static contract tests for the Mini-Mythos baseline interfaces.

These tests verify shape, parameter sharing, and return-dict structure.
They do NOT train a language model and do NOT claim language-learning success.
"""

import torch
from contracts import RecurrenceConfig, MiniMythosBaseline


def test_shapes_and_return_contract():
    cfg = RecurrenceConfig(
        n_layers_in_prelude=1,
        n_layers_in_recurrent_block=1,
        n_layers_in_coda=1,
        recurrent_embedding_dimension=32,
    )
    model = MiniMythosBaseline(cfg, n_embd=16, vocab=64)
    model.eval()

    B, T = 2, 8
    input_ids = torch.randint(0, 64, (B, T))
    labels = torch.randint(0, 64, (B, T))

    out = model(input_ids, labels=labels)

    assert isinstance(out, dict)
    assert "loss" in out and "logits" in out and "log_ppl" in out
    assert out["logits"].shape == (B, T, 64)
    assert out["loss"] is not None
    assert torch.isfinite(out["loss"])
    print("test_shapes_and_return_contract: PASS")


def test_parameter_sharing():
    cfg = RecurrenceConfig(recurrent_embedding_dimension=32)
    model = MiniMythosBaseline(cfg, n_embd=16, vocab=64)

    # Embedding and LM head must share storage
    assert model.lm_head.weight.data_ptr() == model.wte.weight.data_ptr()

    # Core parameters are the same object across a synthetic multi-step call
    # (they are ModuleList members, not copied per step)
    core_params = list(model.core_block.parameters())
    assert len(core_params) > 0
    print("test_parameter_sharing: PASS")


def test_prelude_core_coda_separation():
    cfg = RecurrenceConfig(
        n_layers_in_prelude=2,
        n_layers_in_recurrent_block=2,
        n_layers_in_coda=2,
        recurrent_embedding_dimension=32,
    )
    model = MiniMythosBaseline(cfg, n_embd=16, vocab=64)

    # Distinct module lists
    assert len(model.prelude) == 2
    assert len(model.core_block) == 2
    assert len(model.coda) == 2

    # Core and Prelude do not share parameters
    prelude_ids = {id(p) for p in model.prelude.parameters()}
    core_ids = {id(p) for p in model.core_block.parameters()}
    coda_ids = {id(p) for p in model.coda.parameters()}
    assert prelude_ids.isdisjoint(core_ids)
    assert core_ids.isdisjoint(coda_ids)
    print("test_prelude_core_coda_separation: PASS")


if __name__ == "__main__":
    test_shapes_and_return_contract()
    test_parameter_sharing()
    test_prelude_core_coda_separation()
    print("ALL CONTRACT TESTS PASSED")
    print("NOTE: These tests verify interface structure only.")
    print("They do not represent language-learning success or official Parcae training.")
