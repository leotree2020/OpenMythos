# User-approved mechanism research sequence

Research objective: improve a usable small Parcae-based research model using isolated, measured mechanisms inspired by OpenMythos. This is not evidence that proprietary Claude Mythos architecture or capabilities have been reproduced. The user requests all four directions be tested in order, retaining negative results and then testing justified combinations.

## 1. Adaptive recursive control

First finish the frozen routing feasibility probe. A positive early-exit count alone is insufficient. A separate quality/cost protocol must compare fixed8, fixed16, fixed32 and adaptive using identical prefixes, paired actual initialization, held-out labels, and full readout overhead. Also compare a label-blind routing allocation with the same depth counts, so easy-example selection is not confused with average depth. Freeze article-level aggregation, practical quality-loss margin and cost criterion before reading labels. Quality non-inferiority needs uncertainty sufficiently narrow to exclude the chosen degradation margin; a nonsignificant difference is not equivalence. Report NLL/perplexity and task-appropriate correctness separately from generated-text examples. Measure CPU latency without instrumentation in a separate paired benchmark; operation counts alone do not prove acceleration.

Current status before this continuation: implemented core and engineering smoke PASS; normal-length new-source routing NOT TESTED after V1 path BLOCKED. No quality or practical speed benefit established.

## 2. Depth-specific LoRA

Before training, freeze exactly which native matrices receive W x + scale B_d A_d x and how d maps to adapters; keep original base weights immutable. Begin with CPU mathematical and tiny-model tests: zero-B identity, explicit dense-update agreement, correct depth selection, gradients for selected adapters, no unintended base gradients, deterministic serialization/reload and continuous-versus-resumed optimizer equivalence. At zero-B initialization, zero A gradient is expected initially and must not be misclassified as broken training; B should receive the appropriate gradient.

Quality pilot requires original base, shared LoRA and depth-specific LoRA. Compare the latter two at equal trainable parameter budget as well as a clearly labelled equal-rank diagnostic; more parameters must not masquerade as depth specialization. Fix train/validation/test article separation, token and optimizer-step budgets, recurrent depth distribution, optimizer settings and multiple paired training seeds before training. Log all training failures, original-weight hashes, validation curves and held-out per-article NLL. Small CPU runs test learning and correctness; claims about 140M-scale gains require that scale to be measured. A negative or uncertain pilot is retained, not relabelled as success.

## 3. Iteration-number encoding

Define the injection point and encoding explicitly, without altering token-position RoPE. Use a zero-initialized gated encoding for the no-op identity control. Compare correctly indexed iteration code, no code, and a constant/shared code with matched parameter budget; a permutation control must have its index assignment frozen before training. Keep the training budget and native computation route fixed. Test gradient paths, causal prefix invariance, serialization and unseen-depth behavior separately. Test first independently, then a four-cell base/LoRA/code/LoRA+code comparison. Single-mechanism non-improvement does not rule out interaction, but any claimed interaction needs direct measurement and independent confirmation.

## 4. MoDA and MoE, separately

Do not treat these names as one executable mechanism. Before implementation, fix the specific paper/source commit, exact routing or information-path definition, parameter count and active computation. Test MoDA and MoE independently before combining them. Controls must distinguish extra capacity from routing: report total/trainable/active parameters, tokens, optimizer steps, FLOPs estimate with limitations, measured time/memory, routing utilization and quality. Include a dense or fixed-route control at the relevant active-compute budget. Larger changes need a separate resource estimate; no GPU purchase or unbounded training is part of this CPU continuation.

## How combinations and tuning are judged

Always retain the unmodified base and earlier frozen checkpoints. For A+B use base, A, B and A+B under a stated common budget. The interaction contrast is (AB-A)-(B-base), computed on paired article outcomes; do not infer synergy merely because AB is best. Freeze a limited tuning budget on training/validation data, reserve final evaluation from tuning, retain all configurations and negative results, and replicate promising combinations. A single negative small pilot is evidence about that setting, not proof of universal ineffectiveness. Conversely, lack of statistical significance does not justify claiming maintained quality.

Engineering and scientific acceptance remain separate. Every stage has Purpose/Environment/Input/Expected/Actual/Status plus a checkpoint, unresolved issues and one next instruction. On engineering FAIL/BLOCKED stop dependent execution and preserve evidence. New mechanisms, their combinations, training benefits and hardware efficiency remain NOT TESTED until measured. Upstream remains read-only; no A5 relaxation, B1 rerun, B2/D2-A or PR24 merge. Formal Oracle BLOCKED/NOT_READY, FORMAL_ACCEPTANCE_READY=False.
