"""C: independent loop LoRA versus a parameter-matched shared correction.

No native method or source replacement. Scoped hooks affect ONLY the two
registered core projection calls and are removed on every exit path.
"""
from __future__ import annotations
import math
import torch
from torch import nn
from torch.nn import functional as F

MODES = ('P4', 'S16', 'C4')
TARGET_DIMS = {'attn_out': (32, 32), 'ffn_out': (64, 32)}


class LowRankBank(nn.Module):
    def __init__(self, input_dim: int, output_dim: int, mode: str, generator: torch.Generator):
        super().__init__()
        if mode not in ('S16', 'C4'):
            raise ValueError('adapter mode must be S16 or C4')
        # Same canonical random numbers across adapted arms, no global RNG use.
        bank = torch.randn(4, 4, input_dim, generator=generator, dtype=torch.float32)
        bank = bank / math.sqrt(input_dim)
        self.mode = mode
        self.down = nn.Parameter(bank if mode == 'C4' else bank.reshape(1, 16, input_dim))
        groups, rank = (4, 4) if mode == 'C4' else (1, 16)
        self.up = nn.Parameter(torch.zeros(groups, output_dim, rank, dtype=torch.float32))

    def forward(self, x: torch.Tensor, iteration: int) -> torch.Tensor:
        if type(iteration) is not int or not 0 <= iteration < 4:
            raise ValueError('only iterations0..3 are registered')
        if x.shape[-1] != self.down.shape[-1]:
            raise ValueError('projection input dimension changed')
        slot = iteration if self.mode == 'C4' else 0
        return F.linear(F.linear(x, self.down[slot]), self.up[slot])


class LoopLoRA(nn.Module):
    """All backbone parameters train; adapter-only fine-tuning is NOT used."""
    def __init__(self, base: nn.Module, mode: str, seed: int):
        super().__init__()
        if mode not in MODES:
            raise ValueError('unregistered intervention')
        cfg = base.config
        if (cfg.use_fused_head != 'pytorch' or cfg.randomize_positions_from is not None
                or base.gradient_checkpointing or base.recurrent_iteration_method != 'per-batch'
                or len(base.transformer.core_block) != 1):
            raise ValueError('unsupported native configuration; do not silently repair')
        if any(isinstance(m, nn.Dropout) and m.p for m in base.modules()):
            raise ValueError('dropout outside protocol')
        if any(p.dtype != torch.float32 or p.device.type != 'cpu' for p in base.parameters()):
            raise ValueError('base must be CPU FP32')
        self.base, self.mode = base, mode
        self.adapters = nn.ModuleDict()
        self._busy = False
        core = base.transformer.core_block[0]
        targets = {'attn_out': core.attn.c_proj, 'ffn_out': core.mlp.proj}
        for name, module in targets.items():
            inp, out = TARGET_DIMS[name]
            if tuple(module.weight.shape) not in ((out, inp), (inp, out)):
                raise ValueError(f'unexpected projection shape: {name}')
        if mode != 'P4':
            generator = torch.Generator(device='cpu').manual_seed(seed + 31000)
            for name, (inp, out) in TARGET_DIMS.items():
                self.adapters[name] = LowRankBank(inp, out, mode, generator)

    def forward(self, tokens: torch.Tensor, labels: torch.Tensor | None = None,
                depth: int = 4, trace: bool = False) -> dict:
        if type(depth) is not int or depth not in (2, 4):
            raise ValueError('only registered evaluation depths2/4')
        if (tokens.device.type != 'cpu' or tokens.dtype != torch.long or tokens.ndim != 2
                or tokens.shape[0] <= 0 or not 0 < tokens.shape[1] <= self.base.config.block_size):
            raise ValueError('nonempty CPU int64 BxT tokens required')
        if labels is not None and (labels.device.type != 'cpu' or labels.dtype != torch.long
                or labels.shape != tokens.shape or not bool((labels != -100).any())):
            raise ValueError('aligned supervised labels required')
        if self._busy:
            raise RuntimeError('concurrent/reentrant calls unsupported')
        if self.mode == 'P4':
            native = self.base(tokens, labels=labels, return_logits=True, num_steps_pair=[0, depth])
            loss = native['loss'] if labels is not None else None
            return dict(logits=native['logits'], loss=loss, final_loss=loss, aux_loss=None,
                        route=None if not trace else [])
        self._busy = True
        core = self.base.transformer.core_block[0]
        count = {'iteration': -1, 'attn_out': 0, 'ffn_out': 0}
        route, handles = [], []

        def before_core(module, inputs):
            count['iteration'] += 1
            if count['iteration'] >= depth:
                raise RuntimeError('unexpected extra core invocation')

        def make_hook(name):
            def after_projection(module, inputs, output):
                iteration = count['iteration']
                if not 0 <= iteration < depth or count[name] != iteration:
                    raise RuntimeError('projection called outside one-per-iteration contract')
                count[name] += 1
                correction = self.adapters[name](inputs[0], iteration)
                if correction.shape != output.shape:
                    raise RuntimeError('projection output shape changed')
                if trace:
                    route.append((name, iteration, iteration if self.mode == 'C4' else 0))
                return output + correction
            return after_projection

        try:
            handles.append(core.register_forward_pre_hook(before_core))
            handles.append(core.attn.c_proj.register_forward_hook(make_hook('attn_out')))
            handles.append(core.mlp.proj.register_forward_hook(make_hook('ffn_out')))
            native = self.base(tokens, labels=labels, return_logits=True, num_steps_pair=[0, depth])
            if count != {'iteration': depth-1, 'attn_out': depth, 'ffn_out': depth}:
                raise RuntimeError('incomplete native projection routing')
        finally:
            for handle in handles:
                handle.remove()
            self._busy = False
        loss = native['loss'] if labels is not None else None
        return dict(logits=native['logits'], loss=loss, final_loss=loss, aux_loss=None,
                    route=route if trace else None)

    def added_parameters(self) -> int:
        return sum(p.numel() for p in self.adapters.parameters())
