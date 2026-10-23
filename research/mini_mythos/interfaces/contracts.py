"""
Mini-Mythos baseline interface contracts aligned with pinned Parcae.

Pinned upstream: 69284c13746e849104f738d6d1a347b1f457df76

Two layers are provided:

1. INTERFACE STUB — MiniMythosInterfaceStub
   Linear-based toy for shape and sharing checks only.
   Must never be treated as a Mini-Mythos model or Parcae reproduction.

2. ParcaeBaselineAdapter
   Thin wrapper around an official Parcae instance.
   Reuses transformer.prelude, .adapter, .core_block, .C, .coda, .ln_f
   without re-implementing Block, DiagonalInjection, scheduling, or state init.

Neither performs language learning. Official Parcae remains the experimental baseline.
"""

from dataclasses import dataclass
from typing import Optional, Protocol, runtime_checkable, Any

try:
    import torch
    from torch import Tensor, nn
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    Tensor = Any  # type: ignore
    nn = None     # type: ignore


@dataclass(frozen=True)
class RecurrenceConfig:
    """Subset of ParcaeConfig fields relevant to the three-module contract."""

    n_layers_in_prelude: int = 2
    n_layers_in_recurrent_block: int = 2
    n_layers_in_coda: int = 2
    mean_recurrence: int = 8
    mean_backprop_depth: int = 4
    recurrent_embedding_dimension: int = 768
    injection_type: str = "diagonal"
    prelude_norm: bool = True
    recurrent_iteration_method: str = "per-sequence"
    tie_embeddings: bool = True


if TORCH_AVAILABLE:
    @runtime_checkable
    class PreludeContract(Protocol):
        def forward(self, embeds: Tensor, freqs_cis: Optional[Tensor] = None,
                    attention_mask: Optional[Tensor] = None) -> Tensor: ...

    @runtime_checkable
    class RecurrentCoreContract(Protocol):
        def forward(self, state: Tensor, input_embeds: Tensor,
                    freqs_cis: Optional[Tensor], attention_mask: Optional[Tensor],
                    step: Tensor, total_steps: Tensor) -> Tensor: ...

    @runtime_checkable
    class CodaContract(Protocol):
        def forward(self, hidden: Tensor, freqs_cis: Optional[Tensor] = None,
                    attention_mask: Optional[Tensor] = None) -> Tensor: ...

    class MiniMythosInterfaceStub(nn.Module):
        """
        INTERFACE STUB only.

        Linear layers stand in for real Blocks. Used exclusively for
        CPU contract tests of shapes, sharing, and return structure.
        Do not treat results as Mini-Mythos or Parcae reproduction.
        """

        def __init__(self, config: RecurrenceConfig, n_embd: int = 64, vocab: int = 128):
            super().__init__()
            self.config = config
            self.n_embd = n_embd
            self.recurrent_dim = config.recurrent_embedding_dimension
            self._core_call_count = 0

            self.wte = nn.Embedding(vocab, n_embd)
            self.prelude = nn.ModuleList(
                [nn.Linear(n_embd, n_embd) for _ in range(config.n_layers_in_prelude)]
            )
            self.ln_prelude = nn.LayerNorm(n_embd) if config.prelude_norm else None
            self.adapter = nn.Linear(n_embd, self.recurrent_dim)
            self.C = nn.Linear(self.recurrent_dim, n_embd)
            self.core_block = nn.ModuleList(
                [nn.Linear(self.recurrent_dim, self.recurrent_dim)
                 for _ in range(config.n_layers_in_recurrent_block)]
            )
            self.coda = nn.ModuleList(
                [nn.Linear(n_embd, n_embd) for _ in range(config.n_layers_in_coda)]
            )
            self.ln_f = nn.LayerNorm(n_embd)
            self.lm_head = nn.Linear(n_embd, vocab, bias=False)
            if config.tie_embeddings:
                self.lm_head.weight = self.wte.weight

        def prelude_forward(self, embeds: Tensor) -> Tensor:
            x = embeds
            for layer in self.prelude:
                x = layer(x)
            if self.ln_prelude is not None:
                x = self.ln_prelude(x)
            return x

        def core_forward(self, state: Tensor, input_embeds: Tensor,
                         step: Tensor, total_steps: Tensor) -> Tensor:
            self._core_call_count += 1
            x = state + self.adapter(input_embeds)
            for layer in self.core_block:
                x = layer(x)
            return x

        def coda_forward(self, hidden: Tensor) -> Tensor:
            x = hidden
            for layer in self.coda:
                x = layer(x)
            return self.ln_f(x)

        def forward(
            self,
            input_ids: Tensor,
            attention_mask: Optional[Tensor] = None,
            position_ids: Optional[Tensor] = None,
            labels: Optional[Tensor] = None,
            return_logits: bool = False,
            num_steps_pair: Optional[Tensor] = None,
        ) -> dict:
            """Aligned with native Parcae.forward signature and return semantics."""
            embeds = self.wte(input_ids)
            prelude_out = self.prelude_forward(embeds)

            state = torch.zeros(
                embeds.shape[0], embeds.shape[1], self.recurrent_dim,
                device=embeds.device, dtype=embeds.dtype,
            )
            num_steps = 2
            total = torch.tensor(num_steps)
            for s in range(num_steps):
                state = self.core_forward(state, prelude_out, torch.tensor(s), total)

            projected = self.C(state)
            hidden = self.coda_forward(projected)
            logits = self.lm_head(hidden)

            if labels is not None:
                loss = nn.functional.cross_entropy(
                    logits.view(-1, logits.size(-1)), labels.view(-1)
                )
                log_ppl = loss.detach()
                out_logits = logits if return_logits else None
            else:
                loss = torch.as_tensor(0.0)
                log_ppl = torch.as_tensor(0.0)
                out_logits = logits

            return {"loss": loss, "logits": out_logits, "log_ppl": log_ppl}

    class ParcaeBaselineAdapter(nn.Module):
        """
        Thin adapter that reuses an official Parcae instance.

        It does not re-implement Block, DiagonalInjection, iteration sampling,
        or state initialization. Those remain inside the wrapped Parcae model.
        """

        def __init__(self, parcae_model: nn.Module):
            super().__init__()
            self.parcae = parcae_model
            self.prelude = parcae_model.transformer.prelude
            self.adapter = parcae_model.transformer.adapter
            self.core_block = parcae_model.transformer.core_block
            self.C = parcae_model.transformer.C
            self.coda = parcae_model.transformer.coda
            self.ln_f = parcae_model.transformer.ln_f

        def forward(
            self,
            input_ids: Tensor,
            attention_mask: Optional[Tensor] = None,
            position_ids: Optional[Tensor] = None,
            labels: Optional[Tensor] = None,
            return_logits: bool = False,
            num_steps_pair: Optional[Tensor] = None,
        ) -> dict:
            return self.parcae(
                input_ids,
                attention_mask=attention_mask,
                position_ids=position_ids,
                labels=labels,
                return_logits=return_logits,
                num_steps_pair=num_steps_pair,
            )

        def core_parameters_shared(self) -> bool:
            return True
else:
    # Placeholders so the module can still be imported for static checks
    PreludeContract = None  # type: ignore
    RecurrentCoreContract = None  # type: ignore
    CodaContract = None  # type: ignore
    MiniMythosInterfaceStub = None  # type: ignore
    ParcaeBaselineAdapter = None  # type: ignore
