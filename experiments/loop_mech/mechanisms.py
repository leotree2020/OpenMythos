"""
Loop mechanisms under comparison, applied from outside open_mythos.

Readout:
    act   -- the library's RecurrentBlock.forward, unmodified (ACT-weighted
             sum of per-loop states, early exit once every position halts)
    final -- every loop runs; the output is the last loop's state, so each
             extra loop changes the output (the ACT head is left unused)

Training depth (handled by the training loop, not here):
    fixed -- n_loops = cfg.max_loop_iters every step
    rand  -- n_loops ~ Uniform{1..rand_max} per step
"""

import types
from typing import Optional

import torch

from open_mythos.main import RecurrentBlock, loop_index_embedding

MECHS = {
    "fixed_act": ("fixed", "act"),
    "fixed_final": ("fixed", "final"),
    "rand_act": ("rand", "act"),
    "rand_final": ("rand", "final"),
}


def _final_state_forward(
    self,
    h: torch.Tensor,
    e: torch.Tensor,
    freqs_cis: torch.Tensor,
    mask: Optional[torch.Tensor] = None,
    n_loops: Optional[int] = None,
    kv_cache: Optional[dict] = None,
) -> torch.Tensor:
    """RecurrentBlock.forward with the ACT readout replaced by the last state."""
    n_loops = n_loops or self.cfg.max_loop_iters
    states = []
    for t in range(n_loops):
        h_loop = loop_index_embedding(h, t, self.loop_dim)
        combined = self.norm(h_loop + e)
        trans_out = self.block(
            combined, freqs_cis, mask, kv_cache, f"recurrent_loop_{t}"
        )
        trans_out = trans_out + self.lora(trans_out, t)
        h = self.injection(h, e, trans_out)
        if self.record_states:
            states.append(h)
    self.states = states
    return h


def apply_readout(model: torch.nn.Module, readout: str) -> torch.nn.Module:
    if readout == "final":
        for m in model.modules():
            if isinstance(m, RecurrentBlock):
                m.record_states = False
                m.forward = types.MethodType(_final_state_forward, m)
    elif readout != "act":
        raise ValueError(f"unknown readout {readout!r}")
    return model
