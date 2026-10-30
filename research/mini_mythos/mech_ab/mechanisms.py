"""Isolated, scoped hooks around pinned native Parcae; no base-model rewrite.

Supported research path only: CPU FP32, pytorch head, fixed positions, no cache,
checkpointing or compilation. The original module/method objects are unchanged.
"""
from __future__ import annotations
import math
import torch
from torch import nn
from torch.nn import functional as F

ARMS = {'P4': (1.0, 0.0), 'A': (1.0, 0.25), 'B': (0.5, 0.0)}


def readout(base: nn.Module, state: torch.Tensor, tokens: torch.Tensor) -> torch.Tensor:
    """Reuse the exact native suffix (C, coda incl VE, final norm, output head)."""
    freqs = base.freqs_cis[:, :tokens.shape[1]]
    x = base.transformer.C(state)
    offset = base.config.n_layers_in_prelude + base.config.n_layers_in_recurrent_block
    for i, block in enumerate(base.transformer.coda):
        key = str(offset + i)
        ve = base.value_embeds[key](tokens) if key in base.value_embeds else None
        x = block(x, freqs, None, ve=ve)
    logits = base.lm_head(base.transformer.ln_f(x)).float() * base.config.init.logit_scale
    cap = base.config.logit_softcap
    return logits if cap is None else cap * torch.tanh(logits / cap)


def answer_ce(logits: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
    return F.cross_entropy(logits.reshape(-1, logits.shape[-1]),
                           labels.reshape(-1), ignore_index=-100)


class Mechanism(nn.Module):
    """A: same-trajectory auxiliary loss. B: damp the WHOLE native iteration."""
    def __init__(self, base: nn.Module, alpha: float = 1., auxiliary: float = 0.):
        super().__init__()
        if not (math.isfinite(alpha) and 0 <= alpha <= 1):
            raise ValueError('alpha must be finite in [0,1]')
        if not (math.isfinite(auxiliary) and 0 <= auxiliary <= 1):
            raise ValueError('auxiliary must be finite in [0,1]')
        cfg = base.config
        if (cfg.use_fused_head != 'pytorch' or cfg.randomize_positions_from is not None
                or base.gradient_checkpointing or base.recurrent_iteration_method != 'per-batch'):
            raise ValueError('unsupported native path; do not silently adapt architecture')
        if not len(base.transformer.core_block):
            raise ValueError('empty native core')
        if any(isinstance(m, nn.Dropout) and m.p for m in base.modules()):
            raise ValueError('stochastic readout/dropout is outside this protocol')
        self.base, self.alpha, self.auxiliary = base, float(alpha), float(auxiliary)
        self._busy = False

    def forward(self, tokens: torch.Tensor, labels: torch.Tensor | None = None,
                depth: int = 4, trace: bool = False) -> dict:
        if type(depth) is not int or depth not in (2, 4):
            raise ValueError('only preregistered depths2/4 are supported')
        if tokens.device.type != 'cpu' or tokens.dtype != torch.long or tokens.ndim != 2:
            raise ValueError('CPU int64 BxT tokens required')
        if not (0 < tokens.shape[1] <= self.base.config.block_size):
            raise ValueError('invalid context length')
        if labels is not None and (labels.shape != tokens.shape or labels.dtype != torch.long
                                   or labels.device.type != 'cpu' or not (labels != -100).any()):
            raise ValueError('aligned CPU labels with at least one supervised target required')
        use_aux = labels is not None and self.auxiliary > 0
        if use_aux and depth != 4:
            raise ValueError('auxiliary training requires one four-step trajectory')
        if self._busy:
            raise RuntimeError('concurrent/reentrant forward unsupported')
        self._busy = True
        cache = {'old': None, 'count': 0, 'second': None}
        states = []
        handles = []

        def before_adapter(module, inputs):
            # Capture BEFORE injection, not input to the last Transformer block.
            cache['old'] = inputs[0]

        def after_core(module, inputs, candidate):
            if cache['old'] is None:
                raise RuntimeError('native iteration did not call its adapter')
            old = cache['old']
            if candidate.shape != old.shape:
                raise RuntimeError('native state shape changed')
            # Exact identity avoids cancellation and extra operations when disabled.
            updated = candidate if self.alpha == 1. else old + self.alpha * (candidate - old)
            cache['count'] += 1
            if use_aux and cache['count'] == 2:
                cache['second'] = updated  # INTENTIONALLY not detached
            if trace:
                states.append(updated)
            cache['old'] = None
            return updated

        try:
            handles.append(self.base.transformer.adapter.register_forward_pre_hook(before_adapter))
            handles.append(self.base.transformer.core_block[-1].register_forward_hook(after_core))
            native = self.base(tokens, labels=labels, return_logits=True, num_steps_pair=[0, depth])
        finally:
            for handle in handles:
                handle.remove()
            self._busy = False
        if cache['count'] != depth:
            raise RuntimeError('wrong number of whole-iteration hooks')
        final = native['loss'] if labels is not None else None
        aux = None
        if use_aux:
            # Readout is AFTER the full trajectory. Preserve caller RNG and graph.
            with torch.random.fork_rng(devices=[]):
                aux = answer_ce(readout(self.base, cache['second'], tokens), labels)
            loss = (1 - self.auxiliary) * final + self.auxiliary * aux
        else:
            loss = final
        return {'loss': loss, 'final_loss': final, 'aux_loss': aux,
                'logits': native['logits'], 'states': states if trace else None}
