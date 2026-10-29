# M2-D preparation checkpoint — 2026-10-29

## Read this first

**Native model evaluation: NOT TESTED.** This branch prepares one new scientific question after the user said to continue: with existing trained weights frozen, is increasing native inference depth useful on the validation interval? It does NOT repeat training, the A-M2L-01 gradient-coverage diagnostic, or the old archive audit. Original upstream, M2-L code/results/thresholds and PR #12/#13 are unchanged.

The predecessor checkpoint was actually read at bfbb5d01a205025836f46cff067d065b8d2d99d2. Claude's six raw review files are still absent from the current conversation/runtime; repository checkpoint and pasted report are available. Their archival check remains BLOCKED_MISSING_REVIEWER_FILES. The existing Claude report is user-supplied, not a connected execution. No claim that the six initialization mismatches were resolved or that Grok reviewed M2-D.

## Scientific scope and provenance

- Branch: mini-mythos-m2d-fixed-weight-depth-20261029, base bfbb5d01a205025836f46cff067d065b8d2d99d2.
- Pre-execution protocol: 72b070722d09c3eb2ab2aac1591d3a164b655f95, m2_depth/PROTOCOL.md.
- CPU harness commit: 6da5fb879aac8ad3b80a40bc3584dd3126e74239.
- Harness Git blob: 7077353054bfb515b7712e8befc98960fb1cc60d; SHA256 64a168b5b1dd94179171606ba74a4939febedc8fd857a80d730ed3f66eb78a88. Local tested file and GitHub blob match exactly.
- Launcher commit: 9d96e6edbb4e05d57c1b2efe8ee7b647ab67d38a; local Git blob 1ab2666d1b17f3f19986512deb9524857ef8ada2; Bash syntax checked.
- Untouched Parcae/GPT upstream pinned at 69284c13746e849104f738d6d1a347b1f457df76. Reuse original model constructor, then strictly load and hash each complete final Parcae model state.
- Existing user archive SHA256 0f14ef97493c86f04b02c2d62b381142599fe0640e8729d215a723753172a257; pinned pilot SHA256 c5be0f6da8eab77ab499ad97a3aaf318633d2d44f234083165ffcacc3b26d7bb.

Primary contrast: depth 4 versus depth 2. Secondary: depths 1 and 8. Three existing training seeds; fixed final 1920-step weights; exactly the same validation byte interval, 111520 next-token targets, CPU RNG1212 and batching. No backward, optimizer, Alice evaluation, data download, package installation or GPU use. All three d2 native evaluations must first exactly reproduce the historical validation records before any off-depth scores are examined.

New exploratory benefit screen: mean[d4 NLL - d2 NLL] <= -0.01 AND every seed delta < 0. The screen is preregistered before off-depth outputs; this is not a statistical test or an unseen-test-set claim. Failure is retained, never replaced by the best secondary depth. Report supported forward-operator cost and ratios; no equal-compute superiority claim.

## This turn's actual checks

Purpose: ensure prepared experiment code is syntactically valid, classifies its frozen primary criterion correctly and can read a genuine supplied final snapshot; **not a native inference execution**.

Local preparation runtime: Python 3.13.5, torch 2.10.0+cpu, NumPy 2.3.5, einops 0.8.2. It differs from the producer Python3.12.3/torch2.11.0+cpu/NumPy1.26.4/einops0.8.0, so formal native evaluation was NOT attempted. No environment waiver or silent installation.

| Check | Actual | Status / limit |
|---|---|---|
| Python py_compile and AST parse | run_depth.py compiled successfully | PASS, syntax only |
| No backward/step invocation | AST has no such calls in new harness | PASS, source check |
| Primary result classification | synthetic success/failure/zero-improvement rows classified as prescribed; depth8 cannot replace primary depth4 | PASS, no model metrics |
| Missing evaluation rows | rejected instead of scoring | PASS, preparation only |
| Actual uploaded seed42 Parcae snapshot | restricted weights_only CPU load; file hash and whole-state hash matched pinned report | PASS, no forward run |
| Original archive unchanged | pre/post SHA256 equal | PASS |
| Bash launcher | bash -n completed | PASS, syntax only |
| All three depth2 native validation reproductions | not run | NOT TESTED |
| Depth1/4/8 native model scores and FLOPs | not run | NOT TESTED |
| Primary d4-versus-d2 benefit | no scores | NOT TESTED |
| Claude/Grok M2-D review | none | NOT TESTED |

Local reproducible preparation files are supplied in the conversation under mythos_m2d_prepare_20261029 (run_depth.py, preparation_checks.py/json/log, launcher). These local checks are not official acceptance of the model hypothesis.

## Next single execution

In the existing authorized OpenMythos Codespace, make a separate clean worktree of THIS branch and run:

    bash research/mini_mythos/m2_depth/run_codespaces_cpu.sh

Launcher defaults reuse /workspaces/mythos-m2-cpu312/bin/python, /workspaces/mythos-parcae-pinned, /workspaces/OpenMythos/mythos_evidence/m2_long_v1 and the frozen Tiny Shakespeare file under the existing /workspaces/mythos-m2long-20261029 worktree. Environment overrides are explicit in the script. Missing files cause BLOCKED, never reconstruction, retraining or deletion.

Outputs go to a NEW /workspaces/OpenMythos/mythos_evidence/m2_depth_v1 directory and sibling .console.log; preexisting output is rejected. Exit 0 = all execution plus primary benefit PASS; exit 1 = executed primary benefit FAIL; exit 2 = BLOCKED/error. Always read result.json; do not infer model success from the shell completing.

## Preserved open decisions

M2-L evidence audit remains PASS at its scoped level and its quality criterion remains FAIL. A-M2L-01 inactive paths remain; no source fix or equal-effective-capacity claim. A-M2L-02 remains OPEN; loading complete saved state avoids reliance on reconstruction only for this within-model evaluation, not as a general resolution. No automatic PR merge. A result at unseen inference depth for a depth2-trained model is not retraining-at-depth evidence, ACT, general reasoning improvement, or overall Mythos success.
