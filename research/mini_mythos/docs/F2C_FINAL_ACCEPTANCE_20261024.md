# Mini-Mythos — F2-C Final CPU Numerical Gradient Acceptance

Date: 2026-10-24 (Asia/Tokyo)
Reviewer: ChatGPT, independently from Grok
Decision: **PASS — CLOSED, LIMITED TO THE THREE PRESELECTED CORE SCALAR GRADIENT TESTS.**
Not a whole-model derivative proof, a training proof, or a CUDA/GPU result.

## 1. Scope, provenance and Git checkpoint

- Repo: `leotree2020/OpenMythos`
- Branch: `mini-mythos-p1c-gate22c-readiness`
- Previous accepted F2-B checkpoint: `b15ed92255876b75233a813f5486d58abda239e8`
- F2-C A-R1 frozen gate: `2efc70a0dedef9bf2d501c8ecba4ae312d3c858e`
- F2-C B1 accepted and B2 frozen gate: `d875d601117ea044ef366a58cd183fe1b956890c`
- B2 first implementation: `3ddbef0a5fd5fe048430b1f1ee56f04aed224391`
- Independent B2 review: `97cb88c96091df14337f4400df8b9f1a1aef7d23`
- Final reviewed B2-R1: `aee8f55622eff5e905f03e37ea3977def338cb1a`
- Pinned native upstream Parcae commit: `69284c13746e849104f738d6d1a347b1f457df76`
- AxoNN pin tracked separately: `c5ef65d3d4f329c20292a2d26681e8d9cbcccecf`
- **Actual B1 manifest**: `research/mini_mythos/gate2_2/evidence/f2c/F2C_DISCOVERY_MANIFEST.json`, unchanged Git blob `918e49ef06c31083245259feb4fa2d13eab96cad`.
- B2-R1 adds six new artifacts and modifies only the B2 test script, 7 changed files total; previous B1/B2 evidence unmodified. The GitHub branch HEAD was verified at the reviewed commit before acceptance.
- Grok reports an unrelated uncommitted `research/mini_mythos/gate2_1/TEST_RESULTS.json` modification; preserve it. ChatGPT did not independently access Grok's local worktree.

## 2. Purpose, environment, input, expected behavior

Purpose: For a fixed native Parcae 2/2/2 Prelude/Core/Coda CPU micro-model, test whether selected shared-core parameter gradients agree with a numerical finite-difference derivative of the **same mathematical graph**, separately for full backpropagation (0,2) and the truncated-backpropagation suffix (1,1).

Recorded Grok runtime:
- Python 3.11.2, PyTorch 2.14.1+cpu, x86_64, two CPU threads.
- Parcae original commit and reported clean upstream worktree; source import under `/tmp/parcae-src`.
- Model has 247,936 parameters, native SDPA attention, float32, seed 42, batch 1 and sequence length 8, randomly generated but fixed token IDs and matching labels, `state_init=like-init`.
- Input SHA-256: `be681f780b08da931155937a8c88c0adcef587778ce838b1504a9ae7c2e6648a`.
- Native pure float64 is unavailable due original `.float()` conversions in head and RoPE; no upstream edits authorized.

Frozen, zero-based flattened scalar selection, unchanged since B1:
1. `transformer.core_block.1.attn.c_proj.weight[1424]`
2. `transformer.core_block.0.attn.c_proj.weight[1440]`
3. `transformer.core_block.0.mlp.proj.weight[2934]`

Predeclared acceptance criteria:
- Two central-difference h values `1e-3` and `1e-2`; record effective h± and verify asymmetry <=1%.
- Two loss values differ by at least 16 float32 ULPs.
- `abs(g_autograd-g_fd) <= 1e-3 + 1e-2*max(abs(g_autograd),abs(g_fd))`.
- FD must be consistent across both h within predeclared bounds; no non-finite numbers.
- For TBPTT, freeze `x1` after first no-grad core update at baseline parameters; reconstruct exact suffix and require native-vs-suffix logits, loss and selected AD gradients to agree before suffix FD.
- Negative control `|g_full-g_tbptt| > 1e-2` on these frozen exact scalars.
- Fixed manifest must be validated by actual on-disk Git blob; hard FAIL/BLOCKED/INCONCLUSIVE propagation and restoration guards required.

## 3. Results and independent verification

Grok B2-R1 evidence states local PASS with `EXIT:0` and empty stderr. Independently reviewed full B2-R1 test script and GitHub JSON, recomputed all 12 central-difference derivatives, FP32 ULP signal margins and frozen tolerance checks. All 12 points meet their defined criteria; minimum signal resolution was 54 times the 16-ULP floor.

| Core parameter flattened index | FULL max abs AD/FD error | TBPTT max abs AD/FD error | Native vs suffix selected AD |
|---|---:|---:|---:|
| 1424 | 0.0004269954274145338 | 0.000029982629238700653 | 0 |
| 1440 | 0.00008456293683639649 | 0.0001599232245952653 | 0 |
| 2934 | 0.00005487212500898675 | 0.0001686126533463339 | 0 |

- Six FULL checks, six TBPTT checks: all PASS for predeclared h and native float32 precision envelope.
- Suffix reconstruction: native-vs-suffix logits maximum delta 0, loss delta 0; selected gradients equal.
- Negative gaps `0.29848015308380127`, `0.24144262075424194`, `0.16473227739334106`, all >0.01.
- Baseline repeat, pinned source/worktree, input hash, scalar values, 247936 parameters, independent parameter storage, import source, mutated-manifest digest detection and perturbation restoration checks: all recorded PASS.
- `aggregate()` and `exit_code()` logic were independently transcribed and directly exercised in a local Python-only isolated check by the reviewer for five scenarios: FAIL+INCONCLUSIVE -> FAIL/1; FAIL+unstable -> FAIL/1; BLOCKED+INCONCLUSIVE -> BLOCKED/2; unstable-only -> INCONCLUSIVE/3; all-PASS -> PASS/0. These passed. Caveat: the Grok script's embedded `synthetic_guards()` self-check uses a hardcoded `exits` map rather than directly invoking `exit_code()`; future harness work should fix this, but the reviewed functional exit logic is correct and it does not invalidate the current CPU numeric acceptance.
- Manifest mutation negative computes a distinct hash on a copied file; the actual precheck code compares the real `--manifest` file against pinned SHA and returns BLOCKED if it differs. The copied manifest was not passed to a second full CLI invocation in Grok evidence.

Evidence directory:
`research/mini_mythos/gate2_2/evidence/f2c/b2r1/`

Independent SHA-256 re-computation from GitHub-hosted contents (all 4 matched `RUN_META.json`):
- `F2C_B2R1_RESULTS.json`: `d56b43eb9b04969bb02fe7d53eeb91f916f76435ff80ae4ba43b8eb648004dae`
- `stdout.txt`: `79e7aac507606b5e6ec532689e934f3c0f453247b21005cd80d85588d5b338e2`
- `stderr.txt` (empty): `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- `exit_code.txt` (`EXIT:0`): `194ff5bca66278888f0f00be5c7ca523d15098ece958b14952533811089f6106`

## 4. Acceptance status, limitations and remaining research

- **PASS/CLOSED:** F2-C's defined 3-scalar, 2-step-size, native-CPU full and TBPTT finite-difference gradient correctness scope.
- **PASS/CLOSED:** F2-B's previously accepted CPU recurrence mechanism probe.
- **NOT TESTED:** independent full Parcae CPU rerun by ChatGPT; full parameter-gradient coverage via numerical FD; other inputs/seeds/configurations; actual optimization convergence or language-model learning; native training entrypoint; CUDA; GPU MuonAdamW; Gate 2.2-C and distributed/large-scale execution.
- **BLOCKED as a pure-fp64 claim:** unmodified native Parcae contains float32 casts in head and RoPE.
- This review is based on source/artifact/arithmetic/hash audits and isolated functional guard rechecks, not a fresh native model execution by ChatGPT. Recorded CPU runs are Grok's.
- The same deterministic sample and selected scalars were used in B1 discovery and B2 confirmation. This is a pinned controlled confirmation, **not an independent held-out seed or data generalization experiment**.

## 5. Next exact phase instruction (CPU first)

**Do not launch GPU or edit upstream.** First conduct a design-only CPU audit for the next native Parcae correctness dependency: verify deterministic RNG/state behavior under activation checkpointing and state restoration, or native training-entrypoint lifecycle as a separate, explicitly named experiment. Read THIS checkpoint and pinned upstream source before coding. Define immutable input, acceptance matrix, dependency and Git hygiene, and whether existing F2-A/B/C findings are affected. Have Grok propose the minimal design, then request independent ChatGPT approval before writing/running next-stage code. Preserve the previous B1/B2 artifacts and isolated `gate2_1` local state; do not bulk merge the 73+ prior commits into `mini-mythos-research` without review. Keep `Gate 2.2-C`, native `train.py`, optimizer and GPU outcomes as NOT TESTED until independently exercised.
