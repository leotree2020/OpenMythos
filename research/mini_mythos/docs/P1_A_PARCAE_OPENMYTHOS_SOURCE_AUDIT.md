# P1-A — Parcae vs OpenMythos: source-level architecture audit (2026-10-22)

**Status:** preliminary source audit; no training/evaluation claim. **Change policy:** documentation only; do not modify upstream model or merge without review.

## Scope and provenance

Compared:
- Parcae: https://github.com/sandyresearch/parcae (public source viewed 2026-10-22)
  - `parcae_lm/models/parcae/parcae.py`
  - `parcae_lm/models/parcae/config.py`
  - `parcae_lm/modules/injection.py`
  - `launch_configs/parcae-small-140m.yaml`
  - paper: https://arxiv.org/abs/2604.12946
- Local fork: https://github.com/leotree2020/OpenMythos, branch `mini-mythos-research`, starting base commit `98a80dd6fa29fb6c3562ccdfe90ad2e3698c0ace`:
  - `open_mythos/main.py`
  - `research/mini_mythos/README.md`
  - `.github/workflows/mini-mythos-smoke.yml`

Before executable replication, pin a Parcae **full commit SHA**, verify license/requirements and capture dependency lockfile, source/dataset/tokenizer fingerprints and exact run args. This document does not imply a reproduced paper result.

## Verified architectural differences

| Topic | Parcae source | OpenMythos source | Consequence |
|---|---|---|---|
| Framework | Prelude, **multiple shared core layers**, Coda | Prelude, **one shared TransformerBlock**, Coda | Architectural capacity and per-iteration FLOPs differ |
| Recurrent state injection | `DiagonalInjection`: `decay=exp(-softplus(dt_bias)*exp(A_log))`; output `x*decay + softplus(dt_bias)*(e @ B.T)` | `LTIInjection`: `A=exp(-exp(clamp(log_dt+log_A)))`; output `A*h + B*e + transformer_out` | Not a drop-in equivalent: different placement of Transformer residual, parameterization, and input projection |
| Input injection capacity | `B` learned matrix (state_dim × input_dim), initialized close to identity | `B` learned vector (dim) for channel-wise scaling | Parcae permits cross-channel input mixing at injection; FLOPs/parameter tradeoff |
| Gradient flow | `iterate_forward` supports `num_steps_no_grad` + `num_steps_with_grad`, recurrence sampling, selective checkpointing | `RecurrentBlock.forward` directly loops and uses ACT weighted accumulation | Different training-memory/credit-assignment mechanisms; compare separately |
| Depth policy | `mean_recurrence`, `mean_backprop_depth`, `sampling_scheme`, per-batch/sequence/token options | `max_loop_iters`, `act_threshold`, ACT halt probabilities | Different notions of adaptive depth; Parcae's sampling is not the same as learned ACT |
| Transformer/FFN | `config.Block` / `recurrent_config.Block` configured in Parcae | recurrent `TransformerBlock(use_moe=True)`; GQA/MLA switch | Do not attribute performance differences to recursion without matching other modules |
| Output states | last recurrent state projected by `C`, then coda | ACT-weighted state mixture, then coda | Output readout varies independently from recurrence |
| Precision/training | 140M YAML uses `bf16-mixed`, `MuonAdamW`, `grad_clip=1.0`, depth partial eval | OpenMythos overlay has CPU smoke/unit tests and other training experiments | Training algorithms/precision/data controls must be matched before quality comparison |

### Important stability qualification

Both diagonal injection implementations can constrain the **linear decay factor** below one for finite well-behaved parameters; **neither fact alone proves that the full nonlinear recurrent network (Transformer residual, attention, MoE, optimizer) is contractive or globally stable**. OpenMythos's existing `LTIInjection` is already *Parcae-inspired* in code comments, so calling this a missing feature would be incorrect.

### Important implementation qualification

Parcae's core path calls the injection adapter **before** applying core transformer layers; OpenMythos calls its injection module **after** computing `trans_out`. Thus matching only the numerical formula for decay will not reproduce Parcae's update rule. A faithful baseline must preserve exact operation order.

## P1 gates (no change to research strategy)

**P1-A (this report):** source comparison only; check input injection, gradient handling, output readout, precision, loop depth, architecture, and provenance.

**P1-B:** CPU numerical correctness smoke for an *unaltered, pinned Parcae checkout* with a minimum model: finite forward/backward, gradients on injection, per-loop state norms, spectral/decay factors. Never label this a model-quality result. Separate P1-B environment from OpenMythos fixed `torch` requirements.

**P1-C:** fresh-weights small-scale Parcae training replication in approved GPU/cloud environment, with pinned tokenizer/dataset split and saved config/commit/checkpoint/metrics. Scaling to paper-level 140M reproduction requires a separately budgeted run.

**P1-D:** only after baseline reproduction, implement **one controlled change at a time** in OpenMythos on separate PRs: (a) injection order and full-B variant; (b) partial backprop depth; (c) shared core layer count; (d) optional fixed-depth state readout. Preserve the Prelude → shared Recurrent Core → Coda direction.

**P1-E:** parameter-matched and FLOP-matched comparisons separately; report train FLOPs, tokens, evaluation FLOPs, and memory footprint. Use held-out genuine text/tasks and multiple seeds before making architectural superiority claims.

## Decision

Retain recurrent architecture and upstream-first methodology. **Do not duplicate existing LTIInjection or expand ACT ablations yet.** Prioritize faithful Parcae baseline replication and controlled study of injection **placement**, full-matrix **B**, gradient truncation, depth sampling, and state readout.

## Known limitations

- This audit is a source reading, not runtime testing.
- Only named inspected files are treated as audited; additional training and initialization code may affect conclusions.
- Parcae's published parameter/data/FLOP comparisons are authors' reported outcomes, **not** outcomes independently reproduced by Mini-Mythos.
- Proprietary Claude Mythos internals are not established by these repositories.
