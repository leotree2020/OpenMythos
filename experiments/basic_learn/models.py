"""
Arms of the basic-learnability experiment.

openmythos  -- the library OpenMythos, unmodified (fixed T=4, ACT readout)
transformer -- the same three blocks (dense, MoE, dense) stacked once, no
               recurrence; same embedding/tied head, norm and init. Parameter
               count matches OpenMythos minus the loop-only parts (LTI
               injection, ACT head, depth LoRA): 607,104 vs 609,698.
"""

import os
import sys

import torch
import torch.nn as nn

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "loop_mech")
)

from train_task import task_cfg  # noqa: E402

from open_mythos.main import (  # noqa: E402
    OpenMythos,
    RMSNorm,
    TransformerBlock,
    precompute_rope_freqs,
)


class PlainTransformer(nn.Module):
    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg
        self.embed = nn.Embedding(cfg.vocab_size, cfg.dim)
        self.layers = nn.ModuleList(
            [
                TransformerBlock(cfg, use_moe=False),
                TransformerBlock(cfg, use_moe=True),
                TransformerBlock(cfg, use_moe=False),
            ]
        )
        self.norm = RMSNorm(cfg.dim)
        self.head = nn.Linear(cfg.dim, cfg.vocab_size, bias=False)
        self.head.weight = self.embed.weight
        self.register_buffer(
            "freqs_cis",
            precompute_rope_freqs(
                cfg.dim // cfg.n_heads, cfg.max_seq_len, cfg.rope_theta
            ),
            persistent=False,
        )
        for m in self.modules():
            if isinstance(m, (nn.Linear, nn.Embedding)):
                nn.init.normal_(m.weight, std=0.02)

    def forward(self, input_ids, n_loops=None):
        T = input_ids.shape[1]
        x = self.embed(input_ids)
        freqs = self.freqs_cis[:T]
        mask = torch.triu(
            torch.full((1, 1, T, T), float("-inf"), device=x.device, dtype=x.dtype), 1
        )
        for i, layer in enumerate(self.layers):
            x = layer(x, freqs, mask, None, f"layer_{i}")
        return self.head(self.norm(x))


def build(arm: str, n_statements: int):
    from task_v2 import seq_len

    cfg = task_cfg(4, n_statements)
    cfg.max_seq_len = seq_len(n_statements)
    if arm == "openmythos":
        return OpenMythos(cfg)
    if arm == "transformer":
        return PlainTransformer(cfg)
    raise ValueError(arm)


def block_applications(model, n_loops_executed: int) -> int:
    """Transformer-block forward passes per token for one forward call."""
    if isinstance(model, PlainTransformer):
        return len(model.layers)
    return len(model.prelude) + n_loops_executed + len(model.coda)
