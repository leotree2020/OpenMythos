# MYTHOS M2-L — preregistered long-run CPU comparison (v1)

**Freeze date:** 2026-10-29. **Status before execution:** NOT TESTED. This protocol is frozen on an isolated research branch **before** any M2-L training. No claims about eventual outcomes. The earlier matched M2 result and any negative results are immutable reference evidence.

## Question and predeclared hypothesis

Does the previously observed small test-NLL gap (Parcae worse in all three 120-step seeds) shrink, remain, or widen when **the exact official-model pair** is trained continuously to 480 and 1920 optimizer steps? This is a learning-trajectory pilot, **not** a demonstration of P2 efficiency, statistical noninferiority, ACT, or downstream reasoning.

Primary interpretation uses held-out **Tiny Shakespeare validation NLL** at steps 120/480/1920. No corpus/optimizer/model retuning. The original Tiny Shakespeare test interval has already been viewed in M2, therefore **do not evaluate, optimize, select, or claim a fresh confirmatory result on it** in M2-L.

At step 1920 the **independent, frozen, out-of-domain** Alice text is evaluated **once only**, after all six models have finished. It is not used for training, early stopping, model selection, hyperparameters, or intermediate plots. This OOD diagnostic cannot be interpreted as an in-domain noninferiority test.

## Source identity

- OpenMythos base PR #12 at `934bc12c2f5737cd233cf8076d820435b95280a8`; do not alter M1/M2 reference results.
- Official native GPT and Parcae from **untouched** `sandyresearch/parcae@69284c13746e849104f738d6d1a347b1f457df76`.
- Reuse `research/mini_mythos/m2_matched/experiment.py` model construction, input/output/final-LN matched initialization, native loss and evaluation, without monkeypatch or upstream source edit.
- Reuse unchanged `research/mini_mythos/m2_matched/frozen_config.json`: GPT width 32, 4 heads, 4 blocks, FFN 60; Parcae width 32, FFN 64, 1 prelude + 2 shared recurrent passes + 1 coda, `num_steps_pair=[0,2]`. The remaining native initialization and state-architecture differences are explicit confounders.

## Frozen inputs and environment

- In-domain training/validation: Tiny Shakespeare raw SHA-256 `86c4e6aa9db7c042ec79f339dcb96d42b0075e16b8fc2e86bf0ca57e2dc565ed`, same contiguous 80/10/10 byte splits as M2; train on first 80%, validate on next 10%; **never consult last 10% in M2-L**.
- OOD test text: public-domain Lewis Carroll *Alice's Adventures in Wonderland*, `dakrone/corpus` commit `f25de55809404f0173504d6853b7b6df93d51ae0`, path `data/alice-in-wonderland.txt`, Git blob SHA1 `6c89ee6db335fcd14ff756e5841aba7b9cd708d0`, byte length 167497, independently computed SHA-256 **`146e69455b17fac23bee136d0121ced326e0b99caf206df0281cb67241963875`**. Fetch raw bytes from that immutable Git commit; fail closed on mismatch. No copyrighted output is included in experiment repository.
- Tokenizer: exact UTF-8 **bytes as 0–255 token IDs**; sequence length 32; batch 8; AdamW lr=0.002, betas=(0.9,0.999), eps=1e-8, weight decay 0, gradient clipping max-norm 1.
- Seeds **42, 20261029, 20261030**, identical precomputed sampled training window starts per paired arm; continuous 1920 steps, validation checkpoints after exactly **120, 480, 1920** steps; target-token budgets 30,720 / 122,880 / 491,520 per arm.
- Linux Python 3.12, torch **2.11.0+cpu**, NumPy 1.26.4, einops 0.8.0, FP32, `CUDA_VISIBLE_DEVICES=`, deterministic algorithms, one CPU thread, math SDPA. Do not install GPU or rent GPU.
- Validation: all nonoverlapping complete sequence-32 windows in the fixed validation interval, 111,520 next-token targets, 18 unused tail targets; no boundary crossing. OOD evaluation: same window rule on Alice, complete windows only, and record exact evaluated target count and unused tail.
- Run from a clean, isolated OpenMythos Git worktree and independently clean upstream checkout. Put outputs under persistent `/workspaces/OpenMythos/mythos_evidence/m2_long_v1`; never overwrite M1 or M2.
- Model weights, **AdamW optimizer state, CPU RNG state, data-start hash, seed/arm/step and config/source identities** must be saved at each checkpoint. Atomic writes; independently distinguish resumption from fresh-process deterministic replay. GPU/MPS RNG state is irrelevant to CPU-only runs.

## Preconditions and mandatory 120-step continuity gate

The original `m2_matched/evidence/linux_e533fbe/pilot.json` is an immutable reference (not training input or quality-selection data). Before proceeding beyond step 120, demand for each seed/arm **exact equality** of:
- seed-specific first-120 sampled-start SHA, initial model-weight SHA, after-120 weight SHA,
- all 120 loss values and gradient norm values,
- initial and step-120 validation NLL,
- counted forward/backward FLOPs and parameter count.

A mismatch is **BLOCKED / REF REPLAY FAIL** and stops that pair; do **not** silently adjust implementation or loosen tolerance. A Torch CPU-wheel or RNG mismatch is a possible environmental blocker, not a reason to claim continuation.

## Predeclared acceptance and interpretation

1. **Execution PASS** iff all six native models complete 1920 finite-loss/finite-gradient steps, update weights, produce exactly the stated 3 validation checkpoints, and final validation NLL is at least .01 below its initial value. All input, config, Python dependency and source-pin checks must pass. A negative-quality outcome is still a valid executed experiment.
2. **Continuity PASS** iff all six 120-step comparisons match the preserved original pilot **exactly**. No rerun can be classified as the same trajectory without this result.
3. **Budget/data PASS** iff GPT/Parcae each seed share starts/target counts and frozen parameter + supported-operator training FLOP ratios stay `max/min <= 1.10`. Counted FLOPs **exclude unsupported elementwise, optimizer and hardware effects**; no end-to-end throughput claim.
4. **Exploratory validation tolerance PASS** at step 1920 iff `mean(Parcae_val_NLL-GPT_val_NLL) <= +0.02` and **every** seed delta `<= +0.05`. Report every seed at all three checkpoints, including negative outcomes; these thresholds **are not statistical noninferiority**. Do not tune to validation curve.
5. **OOD Alice diagnostic**: evaluate once at the end, record per-seed NLL/PPL/deltas and token counts. **No positive PASS/superiority gate** is assigned to the OOD performance; it is descriptive domain-transfer evidence and must not be consulted before training completes.
6. **Real efficiency/P2 gate NOT TESTED**: per-step supported-op counts and descriptive wall time/CPU high-water RSS are recorded, but no stable throughput, inference latency, peak activation memory or hardware FLOP benchmark. Dynamic-depth ACT and reasoning remain NOT TESTED.
7. **Cross-review**: Grok's full report was supplied by user on 2026-10-29 and must remain attributable to the user-provided report, not claimed as a connected tool execution. Disagreements are preserved. Record purpose, environment, inputs, expected/actual, four-way status, branch/HEAD, dependencies, blockers and next instruction in CHECKPOINT.md.
8. Do not merge PR #12 or M2-L on the strength of exploratory quality tolerance. Keep upstream and research PRs isolated.

## Explicit negative outcomes

- If 120-step replay fails: stop. Record the measured mismatch and environment `BLOCKED` rather than fabricating later checkpoints.
- If 1920-step quality tolerance fails: record **FAIL** without changing the official recurrence, learning rate, heldout data or model configuration.
- If CPU code or data source is unreachable: record **BLOCKED**, not PASS; do not use toy substitutes.
- Avoid viewing the OOD corpus metrics before final training completion and do not retune on that set.

## How to execute

The branch-local `run_codespaces_cpu.sh` will validate the pinned CPU Python, fetch only frozen corpora when needed, verify the clean original Parcae checkout, then call `experiment.py`. An uninterrupted run or a resumed run writes actual `pilot.json`, checkpoints and evidence logs; the existence of this protocol, code or PR is **NOT** a passed model experiment.
