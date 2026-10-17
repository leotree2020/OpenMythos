"""
Depth-extrapolation ablations for OpenMythos, applied from outside the
library so `open_mythos` itself stays untouched.

`apply_depth_ablation(model, ...)` swaps the instance's
`RecurrentBlock.forward` for a copy of the original loop with two optional
switches, neither of which adds parameters (so they work on any checkpoint):

    act_final_remainder -- on the last loop, give every still-running position
                           its leftover halting mass, so ACT weights sum to 1
                           at any n_loops (the original leaves positions that
                           never cross act_threshold with weights summing < 1)
    clamp_loop_emb      -- clamp the loop-index embedding to max_loop_iters - 1
                           when n_loops exceeds it, mirroring the LoRA scale
                           clamp already in LoRAAdapter

The patched forward also records `last_loops_run` (loops actually executed,
which can be < n_loops after ACT early exit).

With both switches off the patched forward must reproduce the original one
exactly; `check_matches_original` verifies that against the installed
open_mythos version, so drift in the library is caught instead of silently
evaluating a different model.
"""

import types
from typing import Optional

import torch

from open_mythos.main import RecurrentBlock, loop_index_embedding


def _ablated_forward(
    self,
    h: torch.Tensor,
    e: torch.Tensor,
    freqs_cis: torch.Tensor,
    mask: Optional[torch.Tensor] = None,
    n_loops: Optional[int] = None,
    kv_cache: Optional[dict] = None,
) -> torch.Tensor:
    """Copy of RecurrentBlock.forward with the two ablation switches."""
    n_loops = n_loops or self.cfg.max_loop_iters
    B, T, _ = h.shape

    halted = torch.zeros(B, T, device=h.device, dtype=torch.bool)
    cumulative_p = torch.zeros(B, T, device=h.device)
    h_out = torch.zeros_like(h)

    for t in range(n_loops):
        emb_t = t
        if self.clamp_loop_emb:
            emb_t = min(t, self.cfg.max_loop_iters - 1)
        h_loop = loop_index_embedding(h, emb_t, self.loop_dim)
        combined = self.norm(h_loop + e)
        cache_key = f"recurrent_loop_{t}"
        trans_out = self.block(combined, freqs_cis, mask, kv_cache, cache_key)
        trans_out = trans_out + self.lora(trans_out, t)
        h = self.injection(h, e, trans_out)

        p = self.act(h)  # (B, T)
        still_running = ~halted

        remainder = (1.0 - cumulative_p).clamp(min=0)
        if self.act_final_remainder and t == n_loops - 1:
            weight = remainder
        else:
            weight = torch.where(
                cumulative_p + p >= self.cfg.act_threshold,
                remainder,
                p,
            )
        weight = weight * still_running.float()
        h_out = h_out + weight.unsqueeze(-1) * h

        cumulative_p = cumulative_p + p * still_running.float()
        halted = halted | (cumulative_p >= self.cfg.act_threshold)

        if halted.all() and kv_cache is None:
            break

    self.last_loops_run = t + 1
    return h_out


def apply_depth_ablation(
    model: torch.nn.Module,
    act_final_remainder: bool = False,
    clamp_loop_emb: bool = False,
) -> torch.nn.Module:
    """Patch every RecurrentBlock in `model` in place; returns `model`."""
    for m in model.modules():
        if isinstance(m, RecurrentBlock):
            m.act_final_remainder = act_final_remainder
            m.clamp_loop_emb = clamp_loop_emb
            m.forward = types.MethodType(_ablated_forward, m)
    return model


@torch.no_grad()
def check_matches_original(
    block: RecurrentBlock,
    h: torch.Tensor,
    e: torch.Tensor,
    freqs_cis: torch.Tensor,
    mask: Optional[torch.Tensor],
    n_loops: int,
) -> None:
    """Assert the patched forward with switches off equals the library's."""
    ref = RecurrentBlock.forward(block, h, e, freqs_cis, mask, n_loops)
    flags = (block.act_final_remainder, block.clamp_loop_emb)
    block.act_final_remainder = block.clamp_loop_emb = False
    try:
        out = _ablated_forward(block, h, e, freqs_cis, mask, n_loops)
    finally:
        block.act_final_remainder, block.clamp_loop_emb = flags
    if not torch.equal(ref, out):
        raise RuntimeError(
            "depth_ablation._ablated_forward no longer matches "
            "open_mythos RecurrentBlock.forward; re-sync the copy"
        )
