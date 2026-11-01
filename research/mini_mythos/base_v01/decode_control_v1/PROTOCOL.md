# MYTHOS-DECODE-CONTROL-V1

Purpose: determine whether changing only the token-selection policy can reduce
the observed repetitive continuation and meet the frozen local quality screen
for original Parcae 140M. This is a new CPU diagnostic based on final checkpoint
af796912afb4b01cb072ed382ccb840774b1f146. It is not B1 re-execution or a repair of A5.
User authorized direct implementation, review, freeze and execution without a
Claude handoff or another permission request. All scientific outcomes remain
NOT TESTED until the frozen execution supplies evidence.

## Scope and invariants

Only the designated Codespace bookish-pancake-vwqx7rr9x5w3wxjr. Reuse checkout
/workspaces/mythos-base-v01-rope-diag-v11 on new branch
mythos-base-v01-decode-control-v1. New files only under
research/mini_mythos/base_v01/decode_control_v1/. No upstream edits, original
checkpoint/config/tokenizer/RoPE edits, A5 threshold relaxation, package changes,
downloads, training, backward, optimizer, GPU, cache, B2, D2-A or PR24 mutation.
All earlier evidence stays immutable. No retry, repair, additional conditions or
seed selection after formal execution. Engineering BLOCKED/FAIL stops numerical
work immediately; read-only audits and evidence/checkpoint preservation continue.
Per-row quality failure is an outcome, not an engineering stop: complete the
entire predeclared matrix before assessing quality. No output selection.

## Frozen sources, environment and inputs

Upstream sandyresearch/parcae@69284c13746e849104f738d6d1a347b1f457df76 at
/workspaces/mythos-parcae-pinned is read-only. B1 checkout
/workspaces/mythos-base-v01-b1 remains d88be474ebb2529c5b095e3732b1f25509f9b824.
Original artifacts are from
/workspaces/mythos-evidence/base_v01/b1/b1-20261101T021657Z:

| Artifact | Bytes | SHA256 |
|---|---:|---|
| downloads/model/pytorch_model.bin | 578361537 | ed6eb306464dd0d694e9eacd58f7e06ac3e44b43cb7c5c79dbcb1543059c6621 |
| downloads/model/config.json | 1741 | 5c8fc785c2f6dba67d0370ad715034860e3b22bfce850da825c06baa03923c13 |
| downloads/tokenizer/tokenizer.json | 2326980 | e0021e26057088d68047dbe6e77e2ba1c9fe9ae45bae3df9d67d48c82405ea77 |

Use the exact 12 prompts and 32 tokenizer probes at base commit. Their SHA256s:
prompts f0c36e5e8c2f65a47f72ed81cdef20d464f750cc228873780aa546876befb8ca;
probes 0fc0681c4b9f8baa5012c076e5e457125d2622f6402eaccbe0a6c29efda54d15.
Do not reconstruct strings, add BOS/EOS, truncate, pad or change input tokens.
All 12 prompts are previously viewed development inputs, not a fresh test.

Historical greedy evidence is
/workspaces/mythos-evidence/base_v01/cpu_inference/inference-v1-20261101T062256Z,
FULL_MANIFEST.json SHA256
920d4c4b2fd8b6cc154f37c95d83b22a108ae5bc36787b28da8bf0cee62cbbd2.
Verify all manifest entries and directory membership of B1, RoPE, load and
inference histories before and after; protect all tracked upstream bytes.
Reuse only frozen state_checks.py and tokenizer_checks.py utilities, never old
experiment runners. Coordinator contains their exact size/hash pins.

Interpreter /workspaces/mythos-base-v01-cpu312/bin/python, Python3.12.3,
torch2.11.0+cpu, numpy1.26.4, tokenizers0.23.2; the entire distribution inventory
must equal B1 env_check.json. requirements.lock SHA256
84440f8945041ed314c29b205c5244e074116ede023d5aae0b11b633b4d6a51e.
Before import: OMP_NUM_THREADS=1, MKL_NUM_THREADS=1, OPENBLAS_NUM_THREADS=1,
RAYON_NUM_THREADS=1,
TOKENIZERS_PARALLELISM=false, CUDA_VISIBLE_DEVICES="", PYTHONDONTWRITEBYTECODE=1,
HF_HUB_OFFLINE=1, TRANSFORMERS_OFFLINE=1; -B and private pycache redirection.
Actual torch intra/inter-op1, deterministic algorithms=True, FP32/CPU default,
CPU/CUDA autocast disabled, CUDA uninitialized; save actual before/after import,
CPU lscpu, torch build, module origins and warnings/stdout/stderr.
Single sequential worker, 5400s maximum, at least2GiB disk and2.5GiB MemAvailable.
This resource floor is for one worker and is not a numerical tolerance; it is
above the prior random-architecture smoke RSS1.44GiB plus a source-checkpoint
copy (~0.54GiB). This is a resource estimate, not a guaranteed peak bound;
the official loader can temporarily hold another checkpoint copy. OOM or lack
of resources is BLOCKED; no retry. No throughput/efficiency claim is intended.

## Model and controlled randomness

Import the pinned receval/models/parcae.py and call its exact
ModelingParcae.from_pretrained(local_model_dir, device='cpu', dtype=None) once.
Constructor CPU seed0. No config filtering or overrides. Original like-init,
depth8, FP32, batch1, eval, no_grad, no monitoring/gradient checkpointing.
Retain attn_impl=flash config and force CPU SDPA MATH context, as in the previous
accepted inference run. Stored freqs_cis is loaded, never regenerated/replaced.
All63 state entries must equal original tensor bytes before/after; verify tied
embedding/head object, storage, offset, shape, stride; no gradient exists.

Minimal local scheduling adapter calls official forward_for_generation at each
step with the entire growing prefix, num_steps=8 and past_key_values=None.
Exactly64 raw new tokens, including steps after an EOS, match official loop
length semantics. Reset global CPU RNG to731000+prompt_id ONCE before each
complete generation. Never reset per token or alter stochastic h0.
Each sampled generation gets a separate CPU torch.Generator seeded
841000+100*panel+prompt_id, panel1,2,3. S and P share this seed table.
Pass this generator directly to torch.multinomial; model.generate(generator=...)
would ignore it upstream and is prohibited here. Record default/model RNG and
sampler RNG hashes before/after every forward and selection. Forward may consume
only default RNG; selection/metrics may not consume default RNG. Every condition
must match G's model RNG trajectory for that prompt and step. This controls h0
randomness consumption while preserving content-dependent prediction changes.

## Conditions and ordering (84 outputs; 5376 forward calls)

| Policy | Panels | Inputs each | Selection |
|---|---|---:|---|
| G, historical bridge | 0 |12|argmax, T1, no filtering |
| S, primary candidate |1,2,3|12|categorical softmax, T1, no top-k/top-p |
| P, secondary candidate |1,2,3|12|categorical softmax, T0.8, top-p0.9, no top-k |

Order G prompts1..12, then S panels1..3 each prompts1..12, then P in same order.
Finish and accept all12 G before any S/P. P filtering follows official ordering:
divide temperature, sort descending, softmax/cumsum, >top_p mask shifted right
one position retaining first token, restore mask positions, set masked logits
to negative infinity, softmax over full vocabulary, sample. Raw model logits
must be finite; legal masked negative infinities are allowed. Probabilities must
be finite/nonnegative/nonempty with a valid selected token. Their final FP32
values, summed after exact expansion to FP64, must satisfy abs(sum-1)<=1e-6.
This new probability-normalization guard is independent of historical A5.
P simultaneously
changes temperature and nucleus: compare policies, not isolated factor effects.
S matches official conditional probability semantics; separate token RNG and
no-cache mean this is NOT full official-default generate sequence reproduction.
No repetition penalty/no-repeat-ngram constraint, best-of sampling or EOS cleanup.

## Gates and explicit acceptance

Every check records Purpose, Environment, Input, Expected, Actual and
PASS/FAIL/BLOCKED/NOT TESTED. Exit code alone is insufficient.

| Gate | Acceptance |
|---|---|
| D0 recovery/protection | designated target/interpreter; clean pinned trees; source/input/dependency/hash and full historical manifests exact; resources; source frozen in commit A |
| D1 model/tokenizer | exact official loader/type/runtime; all63 state entries byte-equal; aliases;32 tokenizer roundtrips and12 exact encodings pass |
| D2 G bridge | all12x64 full-logit SHA and last-logit ACTUAL BYTES match historical pass1; prefix tokens/length/hash, selected IDs, raw/effective text and EOS exactly match; logits finite CPU FP32, correct shape, no grad, no cache |
| D3 S/P execution | complete72 sampled generations and all84 total;64steps each; full logits finite; valid token distributions/IDs; RNG isolation and G trajectory agreement at each step; state unchanged afterward |
| D4 sealing | protected file bytes, old directory membership and Git state unchanged; worker completed post-generation state check; complete manifest and retained evidence |

Missing preconditions are BLOCKED; established computation/invariant violations
are FAIL. Either stops, all later gates NOT TESTED. Preserve partial outputs and
exception trace. No third attempt or fallback backend. Unexpected exceptions
are BLOCKED unless an explicit invariant has failed. No new fresh-process
sampling replay is included; report it NOT TESTED, not inherited from old greedy.

Quality is a separate result. QUALITY_RUBRIC.md is frozen with this protocol.
Reuse exact original automatic rules: >=16 tokens strictly before firstEOS,
no token4gram3x, no same-tokenrun6, decode succeeds, no U+FFFD. No cleaning.
Two AI reviewers independently rate anonymous prompt/continuation pairs without
policy/seed/auto labels; retain both labels and rationale. Final coherence means
BOTH true. This is AI-assisted review, not independent human validation.
For each S/P panel, joint_count is number of12 passing auto AND coherence.
A policy passes only if EACH of three panels has joint_count>=9; report every
panel plus min_joint_count. No averaging or bestseed. S is primary; do not
silently promote P after seeing results. If only P passes, label secondary
exploratory candidate. G is a bridge/control and descriptive quality reference.
Perprompt3-repeat stability is descriptive, not an alternate majority rule.

## Competing explanations and decisions

- Greedy collapse: S/P may reduce repeated4grams and increase joint quality.
- Underlying weak distribution: randomness may break loops but add incoherence.
- Prompt/domain mismatch or inadequate learned weights: remain possible; this
  experiment does not separate them. Conditional no-BOS agrees with upstream;
  it is not established as a bug. Base model is not instruction-tuned.
- Implementation inconsistency: G bridge or model/RNG protection fails; stop
  and investigate engineering under another protocol, no quality inference.

If a candidate passes, it is a local development candidate only, not usable
general-purpose Mythos or confirmed generalization; propose independent prompts
next. Reduced repetition with joint gate failure is partial improvement only.
If both fail, these two frozen policies are insufficient, not proof of an
architecture/weight/RoPE cause. Mixed panels fail the stability screen. Worse
outputs are retained; no training/architecture change follows automatically.
No p-values, statistical confirmation or equal-compute superiority claims.

## Freeze, evidence and exit

Implement and statically cross-review before A. AST/stdlib development checks
are allowed and labeled development-only; no pre-freeze model or torch execution.
Commit A contains source, protocol, reviews and exact runbook. Commit B records A
and run command before one execution. New run under
/workspaces/mythos-evidence/base_v01/decode_control/decode-v1-UTC;
operator logs outside run. Save every output/token/step, raw last-logit vectors,
full-logit hashes, RNG hashes, all check rows and state audit. Raw vectors stay
on target; commit public evidence and full private-file manifest. Read-only
postrun recomputation must verify bytes/hashes/counts/screens/RNG assertions.
Commit C includes all public evidence, AI review, result and checkpoint, then
push normally and verify remote HEAD/clean status. Stop after this phase.

Original B1 A5 remains BLOCKED at1e-6; training/resume NOT TESTED;
Formal Oracle BLOCKED/NOT_READY; FORMAL_ACCEPTANCE_READY=False.
