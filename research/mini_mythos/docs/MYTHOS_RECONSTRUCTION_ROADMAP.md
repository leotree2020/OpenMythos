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
- ACT-001 through ACT-004: CPU diagnostics and toy synthetic experiments; these
  do **not** establish actual Mythos architecture fidelity or language-model ability.
- R0 Gate A (2026-10-16): 67/67 tests PASS in Codespaces; a 6-token cached
  prefix plus 2-token chunk fails under unchanged upstream GQA/MLA, while
  an isolated research-only mask correction PASSes with max absolute logit
  difference 2.9802322387695312e-08 for each attention mode. See
  [R0 Gate A](R0_GATE_A_RESULT.md). GPU/FSDP remains unverified.
- R1 Gate A (2026-10-16): user ran 60-step GQA depth-2 byte-tokenized
  WikiText-2 pilot; heldout NLL 5.51615 -> 3.37635, PPL 248.675 ->
  29.264 (1024 validation byte targets). The local checkpoint was saved;
  generated output was 24 spaces, so no demonstrated coherent language ability.
  See [R1 Gate A](R1_GATE_A_RESULT.md).
- R1 Gate B rechecked (2026-10-16): 82/82 unit tests PASS. The 60-step
  model heldout PPL 29.264 was worse than train-fitted Unigram 26.919 and
  Bigram 12.597; argmax always predicted spaces. Reversing history order
  changed next-byte predicted probability TV by just 2.17e-5. See
  [R1 Gate B](R1_GATE_B_RESULT.md).
- R1 Gate C at 200 steps (2026-10-16): checkpoint resume succeeded;
  heldout PPL improved to 25.167, history-order TV 0.002449; greedy output
  remains all spaces. **86/86 tests PASS**. Exact SGD offset replays matched
  checkpoint RNG states at steps 60 and 200, with respectively 15360/51200
  observed supervised targets. Same-exposure unigram/bigram PPL at 60 were
  27.513/19.158 versus model 29.264; at 200 were 26.951/14.812 versus model
  25.167. The 200-step model beats the matched unigram but not the matched
  bigram. See [R1 Gate C](R1_GATE_C_RESULT.md).
- R1 Gate D (planned): a final bounded tiny-model continuation 200→600 steps,
  with strict 60/200/600 comparability checks; stop long-running CPU Toy
  research afterwards and plan proper tokenizer/capacity/GPU training.
  See [Gate D plan](R1_GATE_D_PLAN.md).
- Community training proposal:
  <https://github.com/kyegomez/OpenMythos/pull/27>. Proposed ~117.8M
  MLA+MoE FineWeb-Edu experiment and loop-depth PPL tests; external reports
  are leads to reproduce, not verified project results. Review tokenizer
  consistency and bf16 issues before reuse.

## Milestone R0 — Architecture and training readiness audit (IN PROGRESS)

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

1. Run all unit tests, preserve the 60/200-step checkpoint evidence, then
   resume an independent copy from 200→600 steps using identical configuration,
   seeds and training data; capture exact heldout and generation results.
2. Run Gate D diagnostics and exact data-exposure ngrams at 600; verify the
   entire checkpoint resume chain and plot an apples-to-apples learning curve.
3. **Stop this tiny CPU training line at 600 steps**; if no basic language
   modeling emerges, investigate gradients, attention learning, capacity and
   tokenizer instead of indefinitely tweaking ACT probabilities.
4. Plan a reproducible 100M+ GPU pretraining pilot with a pinned real tokenizer,
   train/heldout provenance, checkpoint/optimizer recovery and baseline tests.
5. Preserve ACT-001–004 as mechanism studies only; never claim reconstructed
   proprietary architecture without independent public evidence.

## References

- Community implementation: <https://github.com/kyegomez/OpenMythos>
- Community loop-scaling experiment PR (independent report):
  <https://github.com/kyegomez/OpenMythos/pull/27>
- Anthropic model reports: <https://www.anthropic.com/transparency>
- Anthropic Mythos 5.1 documentation:
  <https://platform.claude.com/docs/en/models/mythos-5-1/overview>
