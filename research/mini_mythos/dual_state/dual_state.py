"""Isolated work/answer routing around unchanged native Parcae calls.

D0: z=F(z,e), a=F(a,z). D1: z=F(z,e+a), a=F(a,z).
Two cycles mean FOUR total native core calls. No new parameters or losses.
"""
from __future__ import annotations
import torch
from torch import nn
from mechanisms import Mechanism


class DualState(nn.Module):
    def __init__(self, base: nn.Module, arm: str):
        super().__init__()
        if arm not in ('P4', 'D0', 'D1'):
            raise ValueError('unknown state-routing arm')
        # Reuse existing restrictions WITHOUT keeping a second registered module.
        Mechanism(base)
        if base.config.n_embd != base.config.recurrent_embedding_dimension:
            raise ValueError('D1 requires equal input/state width; no silent projection')
        self.base, self.arm, self._busy = base, arm, False

    def forward(self, tokens, labels=None, depth=4, trace=False, intervention=None):
        if type(depth) is not int or depth not in (2, 4):
            raise ValueError('depth is total native calls: only2/4')
        if (tokens.device.type != 'cpu' or tokens.dtype != torch.long or tokens.ndim != 2
                or not 0 < tokens.shape[1] <= self.base.config.block_size):
            raise ValueError('CPU int64 BxT within block size required')
        if labels is not None and (labels.shape != tokens.shape or labels.dtype != torch.long
                or labels.device.type != 'cpu' or not (labels != -100).any()):
            raise ValueError('aligned masked CPU labels required')
        if intervention not in (None, 'noop', 'zero_z', 'zero_a'):
            raise ValueError('unknown diagnostic intervention')
        if intervention is not None and (labels is not None or self.training or depth != 4
                                        or self.arm == 'P4'):
            raise ValueError('intervention only on eval/no-label four-call dual paths')
        if self._busy:
            raise RuntimeError('concurrent/reentrant routing unsupported')
        self._busy = True
        cache = dict(z=None, a=None, e=None, calls=0)
        states, route, handles = [], [], []

        def before(module, inputs):
            if len(inputs) != 2 or cache['calls'] >= depth:
                raise RuntimeError('native adapter call contract changed')
            incoming, e = inputs
            if incoming.shape != e.shape:
                raise RuntimeError('state/input dimensions differ')
            if cache['z'] is None:
                cache.update(z=incoming, a=incoming, e=e)
                if trace:
                    states.append(dict(call=0, role='initial', z=incoming, a=incoming))
            # Never use labels or newly generated answer tokens in this routing.
            k = cache['calls']
            if self.arm == 'P4':
                route.append('single')
                return None  # byte-exact original argument path
            if k == 2:
                if intervention == 'zero_z':
                    cache['z'] = torch.zeros_like(cache['z'])
                elif intervention == 'zero_a':
                    cache['a'] = torch.zeros_like(cache['a'])
            if k % 2 == 0:
                route.append('work')
                injected = e + cache['a'] if self.arm == 'D1' else e
                return (cache['z'], injected)
            route.append('answer')
            return (cache['a'], cache['z'])  # newly computed working state

        def after(module, inputs, candidate):
            if cache['z'] is None or candidate.shape != cache['z'].shape:
                raise RuntimeError('native core routing shape changed')
            k = cache['calls']
            if self.arm == 'P4':
                cache['z'] = cache['a'] = candidate
            elif k % 2 == 0:
                cache['z'] = candidate
            else:
                cache['a'] = candidate
            cache['calls'] += 1
            if trace:
                states.append(dict(call=k+1, role=route[-1], z=cache['z'], a=cache['a']))
            return candidate  # final even call is answer; native suffix reads it

        try:
            handles.append(self.base.transformer.adapter.register_forward_pre_hook(before))
            handles.append(self.base.transformer.core_block[-1].register_forward_hook(after))
            result = self.base(tokens, labels=labels, return_logits=True, num_steps_pair=[0, depth])
            if cache['calls'] != depth:
                raise RuntimeError('wrong number of native calls')
            return dict(loss=result['loss'] if labels is not None else None,
                        logits=result['logits'], states=states if trace else None,
                        route=route if trace else None)
        finally:
            for handle in handles:
                handle.remove()
            self._busy = False


def independent_reference(base, tokens, labels=None, depth=4, arm='D1'):
    """Test-only explicit unroll using native modules, independent of hook routing."""
    from mechanisms import readout, answer_ce
    freqs = base.freqs_cis[:, :tokens.shape[1]]
    e = base.transformer.wte(tokens) * base.emb_scale
    base._current_input_ids = tokens
    for i, block in enumerate(base.transformer.prelude):
        key = str(i)
        ve = base.value_embeds[key](tokens) if key in base.value_embeds else None
        e = block(e, freqs, None, ve=ve)
    if base.config.prelude_norm:
        e = base.transformer.ln_prelude(e)
    z = a = base.initialize_state(e)
    total = torch.tensor(depth)
    for k in range(0, depth, 2):
        z = base.update_recurrent_state(z, e+a if arm == 'D1' else e, freqs, None,
                                       torch.tensor(k), total)
        a = base.update_recurrent_state(a, z, freqs, None, torch.tensor(k+1), total)
    logits = readout(base, a, tokens)
    return dict(logits=logits, loss=answer_ce(logits, labels) if labels is not None else None)
