# R1-A checkpoint — 2026-10-30

## Decision: return to measurable capability

Read PR17 and its checkpoint at36c21aaf245b4ed8999d2a6d070948e231605676. P1-R1 producer-path reconstruction and requested JSON audit are complete; Claude discrepancy root cause remains OPEN. Do not repeat either initializer tool. M2-L/D/T scientific negatives stay unchanged. User then asked to continue toward the original Mythos goal, not another bookkeeping loop.

This stage implements an elementary arithmetic capability pilot: first a native GPT positive-learning control, then native Parcae, then a prespecified same-Parcae depth2/4 accuracy-and-cost comparison. It is a NEW task, not another Shakespeare schedule sweep. It does NOT promote P1/P2/P3 as complete, establish complex/general reasoning, fix active-parameter mismatch, or change upstream architecture.

## Source and isolation

- Repository leotree2020/OpenMythos.
- One new branch only: mini-mythos-r1a-carry-addition-cpu-20261030; base36c21aaf245b4ed8999d2a6d070948e231605676, dependent on Draft PR17. No old PR merges/closures or duplicate implementation.
- Preregistration committed BEFORE any model result:82b70032423d7a87b6109ab2dc5b75470635cee5.
- Data/verdict code:64a94de5dae47c1f1a0cd5b0695583b24a253fae; runner:35ff6747345373c94db83975aeb7e8a16a3a5c88; tests:e7aeb29a482449a7d2e94ac08e6a34f00c0029cf; launcher:56320c8a7bf565be358fa267e603f557573dc29e.
- Unchanged native GPT/Parcae pin69284c13746e849104f738d6d1a347b1f457df76. Reuse existing verified factory/pair_io, no own Transformer implementation, no monkeypatch or layer-index repair.
- Task-format reference actually read: karpathy/minGPT@37baab71b9abea1b76ab957409a1cc2fbfba8a26/projects/adder/adder.py, blob55f03ee1caf4290e86f5ce02570553a87caeee23. Our independently implemented task adapts its reversed-sum/answer-only format with grouped splits, not its result or model. No external dataset/package download.

## Frozen inputs and expected acceptance

See PROTOCOL.md for the complete predeclared design. All5050 unordered pairs of operands0..99, grouped by carry count0/1/2 and hash-split70/15/15. Swapped operands cannot cross partitions. Generation sees4 operand digits only and predicts3 reversed answer digits; native256-way greedy argmax, invalid tokens wrong. Test is used once at fixed final checkpoints, never for selection.

Actual deterministic dataset preparation (not model results):

| Split | Represented problems | Canonical pairs | Carry0/1/2 |
|---|---:|---:|---|
|train|6993|3534|2117/3146/1730|
|validation|756|756|228/341/187|
|test|760|760|230/342/188|

Required runtime is existing Linux Python3.12.3/torch2.11.0+cpu/NumPy1.26.4/einops0.8.0, CPU FP32 one thread. Three seeds42/20261029/20261030; exactly3000 steps per trained arm, batch32, original AdamW settings. Repeated exposures288000 supervised targets per arm/seed. Native task-shape budgets are measured BEFORE training, not borrowed from old sequence32 counts; total-parameter and counted-compute ratios must both<=1.10. Known inactive parameters remain explicitly reported; no equal-active-capacity claim.

Run three GPT controls first. Each must reach validation overall>=95%, every carry category>=90%. Otherwise stop with baseline_learning FAIL, Parcae/test NOT TESTED and primary BLOCKED, without auto-retuning. If GPT passes, train Parcae once with same per-seed batches; require validation overall>=90%, each category>=80% before final test. Final primary is same-Parcae hard-test d4-minus-d2 accuracy gain:mean>=5 percentage points, every seed positive, easy loss<=1pp per seed. High d2 hard accuracy>95% mean gives prespecified ceiling BLOCKED, not an architecture failure or PASS. Cost reported separately. No significance/general reasoning/efficiency superiority claim.

## What actually ran in this preparation

| Check | Actual result | Boundary |
|---|---|---|
| Read latest checkpoint, original factory and minGPT task | PASS for source review | Not a native experiment |
| Python compilation / Bash syntax | PASS | Local Python3.13.5; not import/training acceptance |
| Task and evaluation unit tests |13/13 PASS|Exhaustive10000 ordered arithmetic labels; grouped leakage; mask/shift; exact/invalid outputs; learning/benefit/ceiling rules; spy-model confirms no target prefix passed during evaluation |
| Deterministic split construction |PASS|Counts and hashes above reproduced, no neural predictions |
| Existing-output launcher fixtures |5/5 PASS|PASS/FAIL/BLOCKED/wrong-experiment/partial cases; bytes preserved, no model run |
| Wrong local runtime rejection |Expected rejection PASS|Actual process exit2/execution BLOCKED before native construction; zero rows/weights. This is not a successful capability run |
| Uploaded runner identity |PASS|Git blob2429b7fa7791541ca4e4b6fbdd336658e8ff7504 equals locally compiled/tested bytes; task blobb4907d1c1d6edd41bf0e5bee67585b625963a2d9 also matches |
| Native GPT/Parcae arithmetic trainability |NOT TESTED|No native model run in this session |
| Actual task-shape parameter/FLOP budget |NOT TESTED|Runner will measure on native models |
| Held-out exact-answer accuracy / extra-depth gain |NOT TESTED|No benchmark scores available |
| Grok/Claude new independent review |NOT TESTED / DEFERRED|No reviewer execution invented |

Local preparation runtimePython3.13.5/torch2.10.0+cpu; no dependency installation, GPU rental or connection to the user's Codespaces terminal. The spy fixture deliberately predicts invalid tokens and is not a substitute for the native model. Expected version rejection is recorded in the local preparation bundle, not mixed with future user evidence.

## One next CPU execution

Use an isolated worktree of this branch at the delivered exact commit. Create only when absent; verify existing worktree path/HEAD and never force-reset. Then:

    bash research/mini_mythos/r1_addition/run_codespaces_cpu.sh

Defaults reuse /workspaces/mythos-m2-cpu312/bin/python and /workspaces/mythos-parcae-pinned. No corpus, package or weight download. New output:

    /workspaces/OpenMythos/mythos_evidence/r1_addition_v1/result.json

Also data.json, pip-freeze.txt, final model/AdamW/RNG states for actually trained arms and sibling .console.log. Existing result is READ ONLY with its saved status, not rerun. Incomplete output is preserved. A model may fail learning or the primary screen; do not delete the directory or increase budget to obtain PASS.

Next evidence is the bounded actual run summary and this NEW JSON. Do not request old M2-T/P1-R1 JSONs again. Stop after this stage; no automatic digits/depths/schedules/GPU follow-up.

## Focused independent-review request (not yet executed)

Review grouped commutative split isolation; answer-only mask and free generation; fixed task seeds and budget; no test-driven selection; difficulty/ceiling gate; counts cover all greedy forwards including last batch; A-M2L-01 prevents causal equal-capacity GPT claims. Return evidence-based PASS/FAIL/BLOCKED/NOT TESTED with actual run scope. Do not reopen completed initialization auditing or make a performance claim from fixture tests. A future positive result must be independently reviewed before promotion/merge.

Formal Oracle BLOCKED/NOT_READY and FORMAL_ACCEPTANCE_READY=False; no G2 REAL. J1/Bench/R3/model architecture and upstream unchanged. Old scientific FAILs and Claude root-cause OPEN remain. This bounded capability experiment is not permission for scale training, hardware spend or automatic PR merging.
