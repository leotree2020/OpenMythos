# Mini-Mythos — Public-Evidence Reconstruction Roadmap

## Project objective (corrected 2026-10-16)

**Primary objective:** Reverse-engineer, as far as public evidence and authorized
black-box observations permit, a functionally useful independent reconstruction
of Anthropic Claude Mythos **starting from the open-source kyegomez/OpenMythos
codebase**. Train weights, measure model quality on real heldout text/tasks,
and evaluate how closely observable behavior approaches a named Mythos target.

This is **not** primarily a program to optimize ACT, maximize synthetic-loss
scores, or prove that the community's guessed recurrent architecture is real.

## Evidence and honesty rules

1. **Verified public facts**: attributable to official Anthropic docs, model
   reports, or published primary research; keep version/date and URL.
2. **Community implementation/hypothesis**: design in
   `kyegomez/OpenMythos` (Prelude/Recurrent/Coda, ACT, injection, MLA/GQA,
   MoE, per-depth LoRA), **not proof that Claude Mythos uses that design**.
3. **Measured reconstruction behavior**: checkpoints, real evaluation sets,
   training logs, computed metrics and exact code/environment provenance.
4. **Unknown**: undisclosed proprietary weight values, training mix,
   detailed target topology, training recipe; don't invent these.

A publicly accessible model interface (when authorized and available) can support
black-box behavioral comparisons, **not exact architecture or weight recovery**.
Use published and lawfully acquired materials only. Do not imply Anthropic
affiliation or claim model/weight equivalence.

## Where the project stands

- Base repository: `leotree2020/OpenMythos` fork,
  `mini-mythos-research` research branch.
- Implemented upstream: candidate recurrent-depth architecture, token generation,
  GQA/MLA, MoE, ACT and training entry points. Upstream code needs independent
  engineering verification before large GPU runs.
- ACT-001 through ACT-004: working CPU diagnostics, 55 passing tests as of
  user-provided ACT-004 Phase 2 log, tiny initialized models, synthetic tokens,
  30-step A/B runs. **These do not establish actual Mythos architecture fidelity
  or usable language-model ability.**
- Community training proposal:
  <https://github.com/kyegomez/OpenMythos/pull/27>. Proposed ~117.8M
  MLA+MoE FineWeb-Edu experiment and loop-depth PPL tests; external reports
  are leads to reproduce, not verified project results. Review tokenizer
  consistency and bf16 issues before reuse.

## Milestone R0 — Architecture and training readiness audit (NEXT)

Deliver one evidence matrix with columns `feature`, `implementation path`,
`source classification`, `test`, `status`, `risk`.
Audit:
- model config and parameter accounting; attention / KV cache / causal mask;
- recurrent shared parameters, position/depth injections, ACT,
  depth-specific LoRA, MoE routing, residual/numerical stability;
- tokenizer, training labels, sequence packing, optimizer, dtype/mixed
  precision, gradient accumulation, gradient clipping and resume checkpoint;
- generation correctness vs full recomputation, depth extrapolation,
  deterministic heldout evaluation and training/evaluation data leakage;
- reproducible torch/environment dependencies.

**Gate R0**: trainable end-to-end pipeline with checkpoint save/resume,
heldout text evaluation, generation and explicit audit findings.
Maintain upstream `open_mythos/main.py` unchanged on research branch until a
reviewed, evidence-justified patch is separately proposed.

## Milestone R1 — Actual small language model training

- Start with manageable ~100–200M parameter class, or smaller as necessary for
  available GPU memory, trained on licensed/publicly usable text.
- Record tokenizer ID, dataset revision, data cutoff, dedup/splits,
  token count, batch/sequence, optimizer schedule, precision, seeds,
  parameter counts, FLOPs estimates, wall-clock, hardware, checkpoints.
- Report real heldout token-level NLL/PPL, nonmemorized task performance,
  and grounded sample generation.
- Reproduce community PR #27 only after confirming code quality and compute
  feasibility, including potential bf16 and tokenizer consistency pitfalls.

**Gate R1**: independently rerunnable real-data checkpoint and PPL result;
a CPU synthetic experiment is not a substitute.

## Milestone R2 — Architectural hypothesis testing

Compare, at equivalent training-token and measured/estimated compute budgets:
- non-recurrent baseline;
- fixed-depth recurrent version;
- ACT/adaptive recurrence;
- optionally GQA/MLA, MoE and injection ablations after baseline is stable.

Record full train/eval cost and inferenced latency, actual loop counts,
quality against budgets and multiple seeds. Seek evidence for or against
the hypothesized recurrent architecture rather than treating it as confirmed.

**Gate R2**: a repeatable cost-quality curve that identifies which features
are valuable in the independent reconstruction.

## Milestone R3 — Behavior-targeted replication

Define a **named target version** (e.g. an available Claude Mythos model) and
an authorized testing interface. Establish public or permissioned evaluation
sets across reasoning, coding, long-context retrieval and instruction following.
Keep prompts/dataset versions fixed; score blind where feasible.
Public model-level benchmark scores compare capabilities; they are not evidence
of matching hidden activations or architecture.

**Gate R3**: documented capability-gap report on tasks accessible to both
the independent reconstruction and the target.

## Milestone R4 — Scaling decision

Only scale to 1B+ parameters once training correctness, inference correctness,
real-data evaluation and an actual hardware budget are known. Continue with
distillation or fine-tuning **only within applicable terms and permissions**;
avoid unsupported claims of proprietary model extraction.

## Immediate work queue

1. Create R0 architecture/training readiness matrix from repository source.
2. Identify smallest GPU pretraining run that yields a real checkpoint and
   a credible heldout PPL; expose resource requirements and blockers.
3. Implement data and checkpoint provenance, real validation and smoke tests.
4. Preserve ACT-001–004 as completed mechanism studies; **do not pursue
   forced-final remainder optimization unless new evidence justifies it**.

## References

- Community implementation: <https://github.com/kyegomez/OpenMythos>
- Community loop-scaling experiment PR (independent report):
  <https://github.com/kyegomez/OpenMythos/pull/27>
- Anthropic model reports: <https://www.anthropic.com/transparency>
- Anthropic Mythos 5.1 documentation:
  <https://platform.claude.com/docs/en/models/mythos-5-1/overview>
