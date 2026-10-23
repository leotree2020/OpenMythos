"""
Mini-Mythos baseline interface contracts.

These contracts mirror the data-flow of pinned Parcae
(commit 69284c13746e849104f738d6d1a347b1f457df76):

  tokens → Embedding → Prelude → [Recurrent Core × sampled steps] → Coda → LM Head

Key facts taken from parcae_lm/models/parcae/parcae.py and config.py:
- Prelude, Core, and Coda are ModuleLists of the same Block class (or a dimension-adjusted
  recurrent config for the Core).
- The Core is shared across recurrence steps (same parameters applied repeatedly).
- Injection (adapter) mixes the current recurrent state with the Prelude output.
- A linear projection C maps the recurrent embedding dim back to the model dim before Coda.
- Sampling decides how many steps run without gradient vs with gradient.
- This is an interface definition only. It does not train language models and does not
  claim any language-learning success.
"""

from dataclasses import dataclass
from typing import Optional, Protocol, runtime_checkable

import torch
from torch import Tensor, nn


@dataclass(frozen=True)
class RecurrenceConfig:
    """Sampling and depth parameters taken from ParcaeConfig."""

    n_layers_in_prelude: int = 2
    n_layers_in_recurrent_block: int = 2
    n_layers_in_coda: int = 2
    mean_recurrence: int = 8
    mean_backprop_depth: int = 4
    recurrent_embedding_dimension: int = 768
    injection_type: str = "diagonal"
    prelude_norm: bool = True
    recurrent_iteration_method: str = "per-sequence"


@runtime_checkable
class PreludeContract(Protocol):
    """
    Input:  token embeddings (B, T, n_embd) + RoPE freqs + optional mask
    Output: same shape embeddings after the prelude stack
    Side:   may apply optional prelude_norm
    """

    def forward(
        self,
        embeds: Tensor,
        freqs_cis: Optional[Tensor] = None,
        attention_mask: Optional[Tensor] = None,
    ) -> Tensor: ...


@runtime_checkable
class RecurrentCoreContract(Protocol):
    """
    Shared recurrent block applied repeatedly.

    Input:  current state x (B, T, recurrent_dim),
            original prelude embeds (for injection),
            step index, total steps
    Output: updated state of the same shape
    Note:   parameters are shared across all recurrence steps.
    """

    def forward(
        self,
        state: Tensor,
        input_embeds: Tensor,
        freqs_cis: Optional[Tensor],
        attention_mask: Optional[Tensor],
        step: Tensor,
        total_steps: Tensor,
    ) -> Tensor: ...


@runtime_checkable
class CodaContract(Protocol):
    """
    Input:  projected recurrent output (B, T, n_embd)
    Output: final hidden states ready for the LM head
    """

    def forward(
        self,
        hidden: Tensor,
        freqs_cis: Optional[Tensor] = None,
        attention_mask: Optional[Tensor] = None,
    ) -> Tensor: ...


class MiniMythosBaseline(nn.Module):
    """
    Minimal, CPU-runnable skeleton that implements the three contracts
    with identity-style stubs. Used only for interface verification.

    It reuses the structural names from Parcae (prelude, core_block, coda, adapter, C)
    but does not re-implement Parcae mathematics or introduce new attention.
    """

    def __init__(self, config: RecurrenceConfig, n_embd: int = 64, vocab: int = 128):
        super().__init__()
        self.config = config
        self.n_embd = n_embd
        self.recurrent_dim = config.recurrent_embedding_dimension

        # Shared embedding (tied later if desired)
        self.wte = nn.Embedding(vocab, n_embd)

        # Prelude: independent parameters
        self.prelude = nn.ModuleList(
            [nn.Linear(n_embd, n_embd) for _ in range(config.n_layers_in_prelude)]
        )
        self.ln_prelude = nn.LayerNorm(n_embd) if config.prelude_norm else None

        # Projection into recurrent space (Parcae uses adapter + C)
        self.adapter = nn.Linear(n_embd, self.recurrent_dim)  # simplified stand-in
        self.C = nn.Linear(self.recurrent_dim, n_embd)         # back-projection

        # Recurrent Core: shared across steps
        self.core_block = nn.ModuleList(
            [nn.Linear(self.recurrent_dim, self.recurrent_dim)
             for _ in range(config.n_layers_in_recurrent_block)]
        )

        # Coda: independent parameters
        self.coda = nn.ModuleList(
            [nn.Linear(n_embd, n_embd) for _ in range(config.n_layers_in_coda)]
        )
        self.ln_f = nn.LayerNorm(n_embd)

        # LM head (tied by default, matching Parcae tie_embeddings=True option)
        self.lm_head = nn.Linear(n_embd, vocab, bias=False)
        self.lm_head.weight = self.wte.weight  # parameter sharing

    def prelude_forward(self, embeds: Tensor) -> Tensor:
        x = embeds
        for layer in self.prelude:
            x = layer(x)
        if self.ln_prelude is not None:
            x = self.ln_prelude(x)
        return x

    def core_forward(
        self,
        state: Tensor,
        input_embeds: Tensor,
        step: Tensor,
        total_steps: Tensor,
    ) -> Tensor:
        # Injection: mix state with projected input (simplified diagonal-style stand-in)
        injected = state + self.adapter(input_embeds)
        for layer in self.core_block:
            injected = layer(injected)
        return injected

    def coda_forward(self, hidden: Tensor) -> Tensor:
        x = hidden
        for layer in self.coda:
            x = layer(x)
        return self.ln_f(x)

    def forward(self, input_ids: Tensor, labels: Optional[Tensor] = None) -> dict:
        """
        Full forward matching Parcae return contract: dict with loss / logits / log_ppl.
        Uses a fixed small number of recurrence steps for interface testing only.
        """
        embeds = self.wte(input_ids)
        prelude_out = self.prelude_forward(embeds)

        # Initialize recurrent state (Parcae has initialize_state; we use zeros for the stub)
        state = torch.zeros(
            embeds.shape[0], embeds.shape[1], self.recurrent_dim,
            device=embeds.device, dtype=embeds.dtype,
        )

        # Fixed steps for the contract test (not the full sampler)
        num_steps = 2
        total = torch.tensor(num_steps)
        for s in range(num_steps):
            state = self.core_forward(state, prelude_out, torch.tensor(s), total)

        projected = self.C(state)
        hidden = self.coda_forward(projected)

        logits = self.lm_head(hidden)

        loss = None
        log_ppl = None
        if labels is not None:
            loss = nn.functional.cross_entropy(
                logits.view(-1, logits.size(-1)), labels.view(-1)
            )
            log_ppl = loss.detach()

        return {"loss": loss, "logits": logits, "log_ppl": log_ppl}
