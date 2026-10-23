# P1-C Gate 2A — MuonAdamW Parameter Grouping (Corrected)

**Source**: `recpre/optim/muon_adamw.py` `get_muon_param_groups` (pinned 69284c1)  
**Status**: Static code analysis only. Runtime grouping **NOT TESTED**.

## Decision logic (verbatim summary)

A parameter goes to **AdamW** if any of:
- `p.ndim < 2`
- name contains `wte` / `embedding` / `embed` / `lm_head`
- name contains `norm` / `ln_` / `bias`
- name contains any of: `a_log`, `dt_bias`, `adapter.b`, `adapter.adapter`, `transformer.c.`

Otherwise (typically ordinary 2D Core weights) → **Muon** (grouped by shape).

## Accurate grouping table

| Category | Examples | Optimizer | Static certainty |
|----------|----------|-----------|------------------|
| Embedding | `transformer.wte` | AdamW | High |
| LM Head | `lm_head` | AdamW | High |
| Norm / Bias | `ln_f`, `*norm*`, `*bias*` | AdamW | High |
| 1D params | any ndim < 2 | AdamW | High |
| Recurrent mechanism | `A_log`, `dt_bias`, `adapter.B`, `adapter.adapter`, `transformer.C` | AdamW | High (explicit) |
| Ordinary 2D Core weights | core_block Linear / proj / qkv / mlp (no special name) | Muon | High |
| Other 2D Injection not matching special names | depends on exact name | Muon if 2D and not listed | Medium |

**Do not claim** that all Core / Injection weights enter Muon. The special recurrent parameters listed above are forced to AdamW for stability.

## Verification levels

- **Static**: logic above is confirmed from source.
- **Runtime**: actual parameter names in a constructed `parcae-small-140m` and resulting group sizes are **NOT TESTED**.
