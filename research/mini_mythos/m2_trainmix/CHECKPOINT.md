# M2-T checkpoint — 2026-10-29

**Native model training and all scientific outcomes: NOT TESTED.** This stage prepares one new controlled training-depth intervention; it does not convert M2-L/M2-D failures to PASS, repeat coverage diagnostics or expand Guard. No model source or previous experiment was edited and no GPU used.

## Read before continuing

The current M2-D checkpoint was read at `1887dc3d65f77bd204a7cf2548fc283070af364c`. PR #14 remains Draft; user terminal output reports execution/baseline PASS but primary depth4 benefit FAIL. The original new `result.json` (expected SHA256 `f9f3d42ef69241ee9b511154e65b1b7754294e83240763cfe29c8002956115dd`) is still absent from current attachments/runtime and PR evidence; no independent raw-byte audit claimed. Claude's six original diagnostic files also remain pending.

The direct inputs for this new experiment are the already uploaded/audited M2-L final model/optimizer/RNG snapshots, not a synthetic replacement for missing M2-D JSON. The existing M2-L archive was independently rehashed this turn as `0f14ef97493c86f04b02c2d62b381142599fe0640e8729d215a723753172a257` and stayed unchanged.

## Git and scientific scope

- New isolated branch: `mini-mythos-m2t-mixed-depth-control-20261029`, parent `1887dc3d65f77bd204a7cf2548fc283070af364c` (Draft PR #14).
- Protocol committed FIRST: `a28cd9026d1074d059d2402cd172e8c9e6d32fa6`.
- Native-model runner: `6bc752c560b3c3f69097e88888747b4bc1797507`; Git blob `e9391b9728768da37b4171c03e74284616915221`; SHA256 `50f2b407b43e8d6db742609c760b431df5a912c2111bc8a8ee5ea13e079c921f`. Remote blob matches locally compiled/tested bytes.
- CPU launcher: `96e7bb25a5590af0720aa3b9b1c9aca05f9136e3`; local Git blob `52b96d1a7943ad519f0060714eb415de400bbff6`.
- Untouched native Parcae pin remains `69284c13746e849104f738d6d1a347b1f457df76`.

Question: does training across two depths improve depth4 validation quality beyond equally budgeted fixed2 training? For each of three seeds, reload independent copies of the SAME original step1920 model, AdamW and CPU RNG state. Control uses depth2 for480 updates; intervention uses balanced depths1/3 for480 updates (240 each). Both have960 core calls,122880 new input/target tokens and identical batches. Count actual supported forward/backward operators first and require C1+C3=2*C2; otherwise stop before training. Compare pre-forward RNG hashes between arms. Registered model and native inactive paths remain unchanged.

Load saved state rather than reconstruct initial weights, preserving A-M2L-02 as OPEN. Parameter ordering and optimizer IDs/moment shapes are checked before restoring. This is not evidence that interrupted/resumed original training equals continuous training.

## Preregistered outcomes

See PROTOCOL.md for full frozen design. Evaluate final validation depths2/4 only, no old test/Alice, no corpus or package download, no quality-based early stopping.

- Execution/integrity and equal-counted-budget gates must pass first.
- Primary: mean[MIXED d4 NLL - FIXED d4 NLL] <= -.01 AND each seed <0.
- Quality safeguard: mean[MIXED d2 - FIXED d2] <=+.02 AND each <=+.05.
- Combined intervention success requires primary AND safeguard.
- Separate extra-inference benefit: mean[MIXED d4 - MIXED d2] <=-.01 AND each<0. Primary success alone cannot establish this.
- This is a validation-only mechanism pilot using an already explored interval, not a statistical noninferiority or unseen-test claim. Counted FLOPs exclude unsupported/scalar/optimizer effects; no actual hardware efficiency, ACT or reasoning superiority claim.

## This turn's actual checks, not model results

Local runtime: Python3.13.5 / torch2.10.0+cpu, Linux CPU, one thread. Formal experiment requires original Python3.12.3/torch2.11.0+cpu/NumPy1.26.4/einops0.8.0. Local network cannot resolve upstream GitHub; available GitHub connector exposes repo actions, not a Codespaces execution terminal. No native forward/backward/training was executed locally.

| Purpose/input | Expected | Actual/status |
|---|---|---|
| Python compile/AST and Bash syntax | valid executable syntax | PASS |
| Fixed/mixed schedule controller |480 updates,240 each depth1/3,960 calls; deterministic and no global RNG consumption|PASS |
| Frozen verdict classifier and invalid inputs |separate primary/safeguard/extra-depth; reject duplicate/missing/nonfinite rows|PASS |
| Optimizer digest/copy mechanics | independent copies and detectable changes | PASS on fixture, not native training |
| Actual supplied M2-L seed42 checkpoint and batch prefixes |hashes, step1920, RNG and first1920 window IDs match|PASS; no model forward |
| Actual checkpoint -> parameter-inventory/AdamW restore interface |60224 parameters,42 existing states, matching serialized state digest|PASS; inventory has no forward implementation, not a substitute model |
| Local mechanics unittest suite |6/6 |6/6 PASS after one retained test-only false positive: negative scope text contained the word Alice; corrected test checked actual input option/constant instead. No scientific criterion changed.|
| Exact native baseline, C1+C3=2*C2 and six continuations |runtime actual evidence |NOT TESTED |
| M2-T Claude/Grok review | actual independent report |NOT TESTED |

Local preparation files, logs and tests are delivered in `Mythos_M2T_Prepared_20261029.zip`. The small test suite is code readiness only; do not count it as an experiment outcome.

## Next execution only

Use a new worktree of this branch in the existing user Codespace, then run:

    bash research/mini_mythos/m2_trainmix/run_codespaces_cpu.sh

Existing paths are reused: `/workspaces/mythos-m2-cpu312/bin/python`, `/workspaces/mythos-parcae-pinned`, `/workspaces/OpenMythos/mythos_evidence/m2_long_v1`, and the frozen text under `/workspaces/mythos-m2long-20261029`. Overrides are explicit in the launcher. No clone, install, destructive reset or removal of old files.

Output: NEW `/workspaces/OpenMythos/mythos_evidence/m2_trainmix_v1/result.json`, six final snapshots plus per-arm reports, full dependency list, sibling `.console.log`. Existing paths are rejected rather than reused; this bounded pilot has no auto-resume. Read every component outcome: exit0=combined primary/safeguard PASS, exit1=combined screen FAIL, exit2=BLOCKED/numerical/execution error. Extra-inference benefit is a separate status and may FAIL even with exit0.

No automatic extension beyond480 new updates, larger depth sweep, GPU scaling or merge. Preserve all new results (including negative ones), source/env/batch/RNG identities and next decision in the checkpoint. The next stage must not hide either old failure or pending raw evidence/reviewer files. Formal Oracle and G2 REAL remain gated.
