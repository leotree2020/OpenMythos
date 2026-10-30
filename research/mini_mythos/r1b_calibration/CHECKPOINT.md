# R1-B-CAL checkpoint — 2026-10-30

## Goal and current status

Continue from R1-A's actual uploaded-result audit at PR18 HEAD84b594c3c96df5255eeb5312a3b281b4e4ea8bac, read live before changes. R1-A arithmetic learnability PASS is retained; its extra-depth screen remains BLOCKED/CEILING_LIMIT with observed average depth4 declines. The old result is already received/audited: do not request it again, lower its threshold, mine its test mistakes or rerun old training.

**R1-B native training: NOT TESTED. Development qualification: NOT TESTED. Final test and extra-depth benefit: NOT TESTED and outside this stage.** Current deliverable is runnable, tested preparation for ONE new task candidate, not a capability result or a completed cross-review.

Purpose: determine whether a strictly three-digit arithmetic development task is both learnable by existing native models and unsaturated enough to support a future meaningful compute-benefit experiment. Only GPT native and Parcae [0,2] are run. No depth4, early checkpoint selection, repeated candidate search or automatic final-test opening.

## Source / isolation

- Repository: leotree2020/OpenMythos.
- Single new branch: mini-mythos-r1b-difficulty-cpu-20261030.
- Base: 84b594c3c96df5255eeb5312a3b281b4e4ea8bac, dependent on Draft PR18.
- Protocol committed FIRST, before native execution: **5b60718a1e6388a91ee9f00a811f41265b92b548**.
- Task commit: d8508e0264421979f7b48a5a886fad4996ae30f5.
- Runner commit: 3fb81f0f92c6efbd74b23d337aca3eef78e04dd8.
- Launcher commit: 6a3b72e030dff5f87c8accc287e7bfa63ee4cf14.
- Tests commit: e142950acc3283c7576b7ddfbcfe5eec5af9b3ef.
- Untouched GPT/Parcae upstream: 69284c13746e849104f738d6d1a347b1f457df76. Existing m2_matched factory/pair_io reused, SHA25674f00c64448ddbc224a48ef83dc031a90c33448ccb92647666707f6b8f988967. No model implementation, upstream repair or initialization replay tool added.
- Remote full-file Git blobs re-read and equal the locally compiled/tested bytes: runner61e3d083f509b6dae95ecb324fa7ec20f245c785; task9dd0a29b673d9326096b816dbdb062c2c7e87d91; launcherc1b1c5c35da6d96dfaa5cd0268e51372b63859a4; tests5ccd77d3f50e354fac173cc0611c14cb1af3d627.

## Inputs, environment and acceptance

See PROTOCOL.md for complete frozen definitions. Operands100..999, six input digits, four reversed sum digits, shifted length9 and answer-only mask. No numerical pair overlaps old two-digit R1-A. Canonical operand pairs stay together; SHA role assignment reserves a future-test region that is not emitted or model-evaluated here. Exactly one development order per pair. Prediction receives only prompts, then its own full256-way greedy outputs; arithmetic reference is used only for labels/scoring.

Actual model-free dataset construction:

| Split | Ordered examples | Canonical pairs | Carry0/1/2/3 |
|---|---:|---:|---|
|train|19977|10000|4996/4991/4994/4996|
|development|1024|1024|256/256/256/256|

Train object SHA256 d2603d85dca18da104b6138e4513fd47be7c8f2063f447534807f86d68e3c458. Development SHA256 f232a8bc703e5aea07d89637f67110442a5d3882f560b05487c4462d31cd02cd. Balanced development accuracy is not comparable to the old naturally weighted test average. No final-test list is generated; the public role rule is not cryptographic secrecy.

Required producer: Linux Python3.12.3/torch2.11.0+cpu/NumPy1.26.4/einops0.8.0, FP32 CPU one thread, math SDPA. Same native configuration/seeds42,20261029,20261030. Exactly3000 AdamW steps/batch32 per executed arm; paired sample batches, fixed optimizer. 96000 repeated problems,384000 supervised tokens,864000 input positions per arm. This is NOT equal work to the old shorter task. Actual32x9 forward/backward counts measured before training, max/min registered/count ratio<=1.10 required; known active-parameter mismatch remains.

Learning floor for EACH seed in BOTH arms: overall>=80%, no-carry>=90%, each carry category>=60%. Train GPT controls first, stop before Parcae if controls fail. After both learn, require EACH Parcae three-carry development score<=90%. Thus qualifying hard scores lie in60%..90%; these are NEW task-readiness design thresholds, not changes to R1-A or evidence of general competence.

Learning failure -> qualification FAIL with reason. Too-high hard score -> qualification BLOCKED/DEVELOPMENT_CEILING. Both pass -> qualification PASS only, extra-depth/final-test NOT TESTED. One fixed endpoint; no checkpoint picking, budget extension, alternative task/depth sweep or automatic continuation. Future final-test comparison needs its own frozen protocol and review and may still fail or saturate.

## Actual preparation checks this turn

| Check | Actual result | Boundary |
|---|---|---|
| Latest PR18 and checkpoint read | DONE | No repeated artifact audit |
| Python compile and Bash syntax | PASS | Syntax, not native execution |
| Task/helper unit tests |18/18 PASS|All405450 canonical sums plus swapped symmetry; exact quotas/hashes; masks; invalid outputs; gate boundaries; no test split; fake spy outputs prove prompt-only unconstrained decoding |
| Existing-output launcher fixtures |6/6 PASS|PASS/FAIL/ceiling/partial/wrong-experiment/empty-directory behavior; input bytes retained; no native model |
| Actual incompatible local runtime rejection |Expected rejection PASS|Subprocess exits2 with execution BLOCKED before factory/native construction, rows empty, no .pt files |
| Remote source identities |PASS|All four published code blobs equal locally tested byte identities |
| Native32x9 loss/count probe |NOT TESTED|Requires existing pinned user runtime |
| Native GPT/Parcae training and development scores |NOT TESTED|No neural training occurred in this preparation |
| Final test, depth4 benefit |NOT TESTED|Intentionally absent; no PASS promotion |
| New Grok/Claude review |NOT TESTED / DEFERRED|No actual report supplied or invented |

Actual local preparation environment: Python3.13.5/torch2.10.0+cpu/NumPy2.3.5/einops0.8.2; only helper/spy checks ran. Current environment was not waived into producer compatibility. No packages, corpora or model weights downloaded; no GPU. A raw GitHub byte download attempt from the container failed DNS; repository reads/writes used the live connector, and source identity was compared by Git blob against actual local bytes. No user's Codespaces shell execution is claimed.

## One next action

In the existing OpenMythos Codespace, fetch this branch, create an isolated pinned worktree only if absent, and run:

    bash research/mini_mythos/r1b_calibration/run_codespaces_cpu.sh

Defaults: /workspaces/mythos-m2-cpu312/bin/python; /workspaces/mythos-parcae-pinned. New output:

    /workspaces/OpenMythos/mythos_evidence/r1b_calibration_v1/result.json

Other files: train/development data, pip-freeze, final states for actually trained arms and sibling .console.log. Existing result is read-only; partial evidence is preserved. Exit0=qualification PASS,1=completed learning-floor FAIL,2=BLOCKED. Inspect reason to separate headroom from operational block. No automatic retry/resume and no rerequest for old JSONs.

After one complete run, review actual per-stratum correctness and stop. If qualification passes, independently review the development-only selection before proposing a separate sealed-test comparison. If it fails, preserve the failure and explicitly decide the route rather than auto-expanding this experiment.

## Boundaries and focused reviewer request

R1-A cross-review remains pending; new development work does not convert it to PASS. Reviewers should check numerical-pair isolation from R1-A, reserved-role exclusion, full-answer generation, new thresholds versus unchanged old criteria, no depth4-based selection, exact update cap and fairness caveats. Do not reopen initialization auditing or add a Guard framework.

All prior results and limits preserved: A-M2L-01 inactive native paths; A-M2L-02 producer recipe reconstructed but Claude root cause OPEN; old model-quality negatives. Keep Draft/unmerged. Upstream Parcae, J1, Bench, R3, existing protocols/runners and model architecture unchanged. Formal Oracle BLOCKED/NOT_READY, FORMAL_ACCEPTANCE_READY=False; no G2 REAL or GPU scale-up.
