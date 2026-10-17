"""
Depth-extrapolation ablations for OpenMythos, applied from outside the
library so `open_mythos` itself stays untouched.

`apply_depth_ablation(model, ...)` swaps the instance's
`RecurrentBlock.forward` for a copy of the original loop with optional
switches, none of which adds parameters (so they work on any checkpoint).
Protocol names (see RULES):

    BASE -- library behavior
    B1   act_final_remainder -- on the last loop, give every still-running
                                position its leftover halting mass, so ACT
                                weights sum to 1 at any n_loops
    B2   act_normalize       -- divide the ACT output by each position's
                                actual weight sum (convex combination of loop
                                states); mutually exclusive with B1
    C    clamp_loop_emb      -- clamp the loop-index embedding to
                                max_loop_iters - 1 when n_loops exceeds it,
                                mirroring the LoRA scale clamp in LoRAAdapter

The patched forward records `last_loops_run` (loops executed by this forward
call, which can be < n_loops after ACT early exit). Setting
`block.stats = new_stats()` additionally accumulates per-token and per-loop
diagnostics across calls (see `new_stats`).

With both switches off the patched forward must reproduce the original one
exactly; `check_matches_original` verifies that against the installed
open_mythos version, so drift in the library is caught instead of silently
evaluating a different model.
"""

import types
from typing import Optional

import torch

from open_mythos.main import RecurrentBlock, loop_index_embedding

RULES = {
    "BASE": {},
    "B1": {"act_final_remainder": True},
    "B2": {"act_normalize": True},
    "C": {"clamp_loop_emb": True},
    "B1+C": {"act_final_remainder": True, "clamp_loop_emb": True},
    "B2+C": {"act_normalize": True, "clamp_loop_emb": True},
}


def new_stats(max_loops: int) -> dict:
    """
    Accumulator filled by the patched forward when assigned to `block.stats`.

    Per forward call: loops executed. Per token: first halting loop
    (1-based; 0 = never reached act_threshold within the loops executed) and
    the ACT weight sum actually applied before any B2 normalization. Per loop
    index t: sum of squared hidden-state entries and of squared change
    h_t - h_{t-1} (h_{-1} = Prelude output), over the calls that executed t.
    """
    return {
        "forward_calls": 0,
        "loops_executed_sum": 0,
        "token_loops_executed_sum": 0,  # loops executed × tokens (compute)
        "tokens": 0,
        "halt_step_hist": torch.zeros(max_loops + 1, dtype=torch.long),
        "weight_sum_sum": 0.0,
        "weight_sum_below_0_99": 0,
        "loop_calls": torch.zeros(max_loops, dtype=torch.long),
        "loop_elems": torch.zeros(max_loops, dtype=torch.float64),
        "h_sq": torch.zeros(max_loops, dtype=torch.float64),
        "dh_sq": torch.zeros(max_loops, dtype=torch.float64),
        "prev_sq": torch.zeros(max_loops, dtype=torch.float64),
    }


def _ablated_forward(
    self,
    h: torch.Tensor,
    e: torch.Tensor,
    freqs_cis: torch.Tensor,
    mask: Optional[torch.Tensor] = None,
    n_loops: Optional[int] = None,
    kv_cache: Optional[dict] = None,
) -> torch.Tensor:
    """Copy of RecurrentBlock.forward with the ablation switches."""
    n_loops = n_loops or self.cfg.max_loop_iters
    B, T, _ = h.shape

    halted = torch.zeros(B, T, device=h.device, dtype=torch.bool)
    cumulative_p = torch.zeros(B, T, device=h.device)
    h_out = torch.zeros_like(h)
    stats = self.stats
    track_w = stats is not None or self.act_normalize
    if track_w:
        w_sum = torch.zeros(B, T, device=h.device)
    if stats is not None:
        halt_step = torch.zeros(B, T, device=h.device, dtype=torch.long)

    for t in range(n_loops):
        emb_t = t
        if self.clamp_loop_emb:
            emb_t = min(t, self.cfg.max_loop_iters - 1)
        h_loop = loop_index_embedding(h, emb_t, self.loop_dim)
        combined = self.norm(h_loop + e)
        cache_key = f"recurrent_loop_{t}"
        trans_out = self.block(combined, freqs_cis, mask, kv_cache, cache_key)
        trans_out = trans_out + self.lora(trans_out, t)
        h_prev = h
        h = self.injection(h, e, trans_out)
        if stats is not None:
            stats["loop_calls"][t] += 1
            stats["loop_elems"][t] += h.numel()
            stats["h_sq"][t] += h.float().pow(2).sum().item()
            stats["dh_sq"][t] += (h - h_prev).float().pow(2).sum().item()
            stats["prev_sq"][t] += h_prev.float().pow(2).sum().item()

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
        newly = still_running & (cumulative_p >= self.cfg.act_threshold)
        halted = halted | newly
        if track_w:
            w_sum = w_sum + weight
        if stats is not None:
            halt_step[newly] = t + 1

        if halted.all() and kv_cache is None:
            break

    self.last_loops_run = t + 1
    if stats is not None:
        n_tok = B * T
        stats["forward_calls"] += 1
        stats["loops_executed_sum"] += t + 1
        stats["token_loops_executed_sum"] += (t + 1) * n_tok
        stats["tokens"] += n_tok
        stats["halt_step_hist"] += torch.bincount(
            halt_step.flatten().cpu(), minlength=len(stats["halt_step_hist"])
        )[: len(stats["halt_step_hist"])]
        stats["weight_sum_sum"] += w_sum.sum().item()
        stats["weight_sum_below_0_99"] += (w_sum < 0.99).sum().item()
    if self.act_normalize:
        h_out = h_out / w_sum.clamp(min=1e-6).unsqueeze(-1).to(h_out.dtype)
    return h_out


def apply_depth_ablation(
    model: torch.nn.Module,
    act_final_remainder: bool = False,
    clamp_loop_emb: bool = False,
    act_normalize: bool = False,
) -> torch.nn.Module:
    """Patch every RecurrentBlock in `model` in place; returns `model`."""
    if act_final_remainder and act_normalize:
        raise ValueError(
            "B1 (act_final_remainder) and B2 (act_normalize) exclude each other"
        )
    for m in model.modules():
        if isinstance(m, RecurrentBlock):
            m.act_final_remainder = act_final_remainder
            m.act_normalize = act_normalize
            m.clamp_loop_emb = clamp_loop_emb
            m.stats = None
            m.forward = types.MethodType(_ablated_forward, m)
    return model


_SWITCHES = ("act_final_remainder", "act_normalize", "clamp_loop_emb", "stats")


@torch.no_grad()
def check_matches_original(
    block: RecurrentBlock,
    h: torch.Tensor,
    e: torch.Tensor,
    freqs_cis: torch.Tensor,
    mask: Optional[torch.Tensor],
    n_loops: int,
) -> None:
    """Assert the patched forward with all switches off equals the library's."""
    ref = RecurrentBlock.forward(block, h, e, freqs_cis, mask, n_loops)
    saved = {k: getattr(block, k) for k in _SWITCHES}
    for k in _SWITCHES:
        setattr(block, k, None if k == "stats" else False)
    try:
        out = _ablated_forward(block, h, e, freqs_cis, mask, n_loops)
    finally:
        for k, v in saved.items():
            setattr(block, k, v)
    if not torch.equal(ref, out):
        raise RuntimeError(
            "depth_ablation._ablated_forward no longer matches "
            "open_mythos RecurrentBlock.forward; re-sync the copy"
        )
