# D1 checkpoint — training phase complete and evidence audit PASS; evaluate NOT yet run

2026-10-31. Experiment MYTHOS-D1-DUAL-STATE-PROFILE-V1.

## Current decision

**D1 TRAINING EXECUTION = PASS. D1 TRAINING EVIDENCE AUDIT = PASS.** All twelve frozen CPU training jobs (GPT/P4/D0/D1 x seeds 2101/2202/2303) completed 3000 updates, with 36 SHA-bound snapshots, passing batch-index, P4/D0/D1 RNG and initial-model pairing checks and no observed R01 numerical-failure case. These results are the OWNER'S terminal report plus the owner-supplied independent read-only audit; this checkpoint-writing session had no access to the Codespaces filesystem and did not itself read, hash or re-audit `training.json` or any worker file.

**This does NOT record that D1 works.** No development scoring, learned-state measurement, exploratory screen or intervention has been run. Training completion is a necessary step, not a mechanism finding. No candidate superiority is claimed.

## 1. Purpose

Execute the frozen train phase only: 12 trajectories, 3000 updates each, batch 32, with 300/1500/3000 snapshots, so that a separate evaluate phase can later measure learned dual-state behaviour on the already-viewed development set. The study question remains: with a shared native transition, does separating a working latent z from an answer latent a change learning, correction/corruption, state trajectories and cost (PROTOCOL.md). Not candidate confirmation.

## 2. Environment and dependencies

Production environment declared in the retained preparation file and used by the unchanged launcher: Linux, Python 3.12.3, torch 2.11.0+cpu, NumPy 1.26.4, einops 0.8.0, CPU FP32, one thread, deterministic math SDPA; interpreter `/workspaces/mythos-m2-cpu312/bin/python`; read-only upstream `/workspaces/mythos-parcae-pinned` = sandyresearch/parcae@69284c13746e849104f738d6d1a347b1f457df76. No installation, GPU, source edit or runtime-gate relaxation. The run's `pip-freeze.txt` is part of the preparation output on the owner's side; it was not supplied to this session and is not re-verified here.

## 3. Frozen execution commit and handoff code

Repository leotree2020/OpenMythos; Draft PR24; branch mini-mythos-d1-dual-state-profile-cpu-20261031.

**Executed code stays `596af7f8997ca793e880a6e1d80c25c7b2043329`** in worktree `/workspaces/mythos-d1-20261031` (six own and eight inherited source files; aggregate source identity `7b7660c5c5ddcd3ca599f45f82c6e8567bfd00e4b968204d600855d8e483e481`). Later commits are documentation or handoff only and must not become the execution tree: `539310a54492cd219b4e37c252985ac75b73ed7a` (registered review transcript, SHA-256 `728d6960a88c997f5cea85d6fa1dcda57d3c5bfdc4378c6e319b9cffeaf57d0d`), `6b6272a165189f348ba63e47490c75ae6667fa97` (train-only launcher helper `evidence/train_after_claude_20261031.sh`, SHA-256 `1742783d53f7216068c7295ca57a488c1a9256aeace402b73aedd14146ebb059`), `2173da4a1d60fbc267062c29a2eda06f7218988c` (previous checkpoint). The helper is newer handoff code, recorded separately from the Claude-reviewed experiment code; it only invoked the unchanged parent `train` phase. Claude Code review of 596af7f: APPROVE (code), one LOW and four INFO findings, none blocking; it is permission to run the frozen study, not evidence D works.

## 4. Training input

- Preparation: `/workspaces/OpenMythos/mythos_evidence/dual_state_v1/prepared.json`, 21,440 bytes, SHA-256 `d7ce57ca11316d0ff892bf35b26ec9ed1ef2f04a2b8587dd4671c7eae8b5a1d1` (byte correspondence verified earlier by reviewer and owner). Its historical `review_status = PENDING Claude Code` is intentionally unchanged; the training record archives the actual report and acknowledgement separately.
- Data: the old R1-B training split (19,977 ordered rows / 10,000 canonical pairs) and 1,024 development questions (256 per carry stratum), `data.json` SHA-256 `9e3700d93bb1c30541e91bc60678a44ff898925f69e2f527f0050de96a0a8750`. Development data is already viewed; no H1/HC/H2/C1T was touched.
- Arms/seeds/budget: GPT, P4, D0, D1 x seeds 2101, 2202, 2303; 3000 updates each; AdamW lr 0.002, betas (0.9,0.999), eps 1e-8, weight decay 0; global gradient clip 1; seed+12000 batch indices, seed+2000 training RNG. Recorded per-update supported-op counts GPT 73,433,088 and P4/D0/D1 114,130,944 (projected 220,299,264,000 and 342,392,832,000 per seed; these are products of the registered counts, not hardware measurements). Same data/updates, NOT equal compute.
- Review input to the train phase: transcript at 539310a (hash above), reviewer string supplied by the owner, `--review-approved`.

## 5. Expected result and actual result

|Item|Expected (frozen acceptance)|Actual (owner terminal + independent read-only audit, as reported)|
|---|---|---|
|Jobs|12 arm/seed combinations, none missing, duplicated or substituted|12/12 training jobs PASS|
|Coverage|GPT/P4/D0/D1 x 2101/2202/2303|complete|
|Length|3000 steps per trajectory|3000/3000 for every trajectory|
|Snapshots|300/1500/3000 for each job = 36|36/36 present, all files SHA-bound|
|Batch-index pairing|identical per-seed batch indices across arms|PASS, all three seeds|
|RNG pairing|P4 = D0 = D1 RNG trace per seed|PASS, all three seeds|
|Initial-model pairing|P4/D0/D1 identical initial base per seed|PASS, all three seeds|
|Numerical failure|none; if any, record worker FAIL and parent R01|none observed|
|Parent vs worker records|summary matches each worker `row.json`|reported consistent by the audit|

Status: TRAINING EXECUTION = PASS; TRAINING EVIDENCE AUDIT = PASS (as reported above). Per-trajectory loss, gradient-norm, time and memory values were not supplied to this session and are not reproduced or interpreted here; no training-loss ranking of arms is claimed.

## 6. Training evidence file

`/workspaces/OpenMythos/mythos_evidence/dual_state_v1/training.json`: **4,800,251 bytes**, SHA-256 **`11e380b075912b4542cdbc39ccb1ec98d5de92658ed21316187e2a64357864af`** (owner-reported; not independently read by the checkpoint author). Do not modify, delete, move, rerun over or resume this file or `jobs/`; the 12 job directories, 36 snapshot files, `review.md`, console log and `train.started` are retained evidence. Resume replay from these snapshots remains NOT TESTED.

## 7. Unresolved findings (carried forward, none patched)

|ID|Status|
|---|---|
|R01 LOW|OPEN. Worker numerical failure is stored FAIL but the unchanged parent summary would report BLOCKED/exit 2. Not triggered in this run (no numerical failure observed); the defect remains in the frozen source and was not patched. Any fix needs its own source identity.|
|R02 INFO|OPEN caveat. zero_a clears only the carried answer state in D0 but also removes the feedback in e+a for D1; zero is out-of-distribution. Cross-arm zero_a sensitivity is a joint perturbation, not answer-state importance. The 1.429 vs 0.403 values are untrained diagnostics, not learned results.|
|R03 INFO|OPEN caveat. State profiles read only the six-digit prompt; call-2 confidence/entropy use an unsupervised intermediate readout; some relative-change fields are zero by construction. Confidence or closeness is not correctness.|
|R04 INFO|OPEN audit caveat. Profile/trace cardinalities are not asserted by the runner; the evaluate audit must count 21 final conditions, 36 learning profiles, 27 latent profiles, six sensitivity groups and the actual traces. Missing measurements are missing evidence.|
|R05 INFO|OPEN interpretation caveat. Exit 0 means execution complete even if all exploratory screens fail. D-vs-P4 changes routing and state together; three seeds, old development data, GPT lower counted compute, 8,320 inactive Parcae parameters.|

## 8. Git status

Branch mini-mythos-d1-dual-state-profile-cpu-20261031; before this update the remote head was `2173da4a1d60fbc267062c29a2eda06f7218988c`. This checkpoint commit changes only this file. Code execution pin remains 596af7f; no upstream, D0/D1 architecture, protocol, threshold, data, seed or budget change. The owner's Codespaces Git state, worktree cleanliness and any untracked files were not supplied and are not claimed. PR24 remains Draft/unmerged.

## 9. Stage state

|Item|Status|
|---|---|
|Native preparation|PASS (owner execution; prior byte audit)|
|Claude D code review|APPROVE for 596af7f; owner-supplied report|
|D1 training execution (12 jobs)|PASS (owner terminal + audit report)|
|D1 training evidence audit|PASS (as reported)|
|Evaluate phase|NOT RUN|
|Learned D quality|NOT TESTED|
|Learned-state measurements|NOT TESTED|
|Exploratory screens|NOT TESTED|
|Candidate selection|NOT ASSESSED|
|Equal-compute superiority|NOT TESTED|
|Fresh-test generalization|NOT TESTED|
|Hardware efficiency|NOT TESTED|
|Resume replay|NOT TESTED|
|R01|OPEN/LOW|
|Formal Oracle|BLOCKED/NOT_READY; FORMAL_ACCEPTANCE_READY=False|

## 10. Next experiment instruction

Run the frozen D1 `evaluate` phase ONLY AFTER this checkpoint is committed (and, if you wish, fetched into Codespaces without changing the execution worktree from 596af7f).

- Use the existing reviewed parent `evaluate` phase and the existing `training.json`/snapshots; read-only inputs.
- Do NOT run `prepare`, `train` or any optimizer step again.
- Do NOT modify upstream Parcae, the D0/D1 architecture, thresholds, data, seeds or budget; no retuning; no new seeds.
- No GPU. No new held-out data (no H1/HC/H2/C1T).
- Do not start evaluate as part of this checkpoint update.
- If evaluate stops or finds partial evidence, preserve all files and report; no automatic retry or resume.

Exit 0 from evaluate will only mean measurements were completed; exploratory screens (D0-P4, D1-P4, D1-D0 at depth 4) are read separately, and candidate selection stays NOT ASSESSED. Evaluate results require their own review before any interpretation (R02-R05 apply).

Claude Code replaces Grok by owner policy. Preserve old negative results and reviewer attributions. Keep PR24 Draft/unmerged. No G2 REAL, GPU expansion, upstream/J1/Bench/R3/old-experiment changes, automatic merge, hyperparameter search or E.
