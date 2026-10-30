# INIT-01 checkpoint — 2026-10-30

## Decision and goal

After reading PR #15 and its actual uploaded-JSON checkpoint at 4d1ecadc062e190a9bfc8b66b8e2d2962abb266a, stop automatically expanding the M2-L/D/T configuration. The user authorized continued progress after the project summary. This isolated step addresses A-M2L-02: reproduce the six historical initial states under the actual original procedure, and capture explicit reusable initial-state artifacts. It does not try another training schedule, change architecture, rerun A-M2L-01 coverage for sealing, or reopen the completed M2-T JSON handoff.

**Original-model initialization replay: NOT TESTED.** Prepared source and helper tests are not model acceptance. A-M2L-02 remains OPEN, M2-L/D/T scientific FAIL results remain unchanged, new Grok/Claude review is NOT TESTED/DEFERRED. No PR merge or GPU use.

## Source and scope

- Isolated branch: mini-mythos-init-replay-20261030; parent 4d1ecadc062e190a9bfc8b66b8e2d2962abb266a, dependent on Draft PR #15.
- Protocol committed before replay code/native execution: 366c80b7cf0b9d84b0720581f6e102a423b784bd.
- Runner commit: 3d06ddddeb660b20e3bf7ac76b22a762fe98ac78.
- Runner Git blob: 2dfdd689ad8c8a28cb24cd1609f80eed409be15c; SHA256 d3ede24ac178bcf76b9100e0032ffe8b8514caa01a6f1badb8108a9f5e99b76a. Remote blob matches locally compiled/tested bytes.
- Launcher commit: 0cc8af31ca00ef0e0c749fab56fb8f586137818f; SHA256 5efd632c42f7cecfd1868e158f66c5a9cacd47224013c4343e4269c675c54c44.
- Six helper tests committed at b80d68ead1f961107dd0cf0b1f8362e7a3c54d8e.
- Native upstream unchanged: sandyresearch/parcae@69284c13746e849104f738d6d1a347b1f457df76.

The source review confirmed that historical initial_weights_sha256 was recorded AFTER original make(GPT), make(Parcae), pair_io, per-arm preflight and count. INIT-01 preserves that ordering and records state/CPU-RNG and individual tensor fingerprints at all four boundaries. Same three seeds, native GPT FFN60 and native Parcae FFN64 configuration. No optimizer is created, no weight update, no text/Alice/validation-quality evaluation. Exactly one original synthetic count backward per model (six total) replays that recording boundary; not a new coverage diagnostic.

## Expected acceptance

Original Linux Python3.12.3/torch2.11.0+cpu/NumPy1.26.4/einops0.8.0 is required. Original helper, calibration and both historical pilot byte hashes must match. Both old records must agree on all six expected init hashes before construction. Full registered state, including persistent buffers, and shared-IO fingerprints must match exactly in all six rows. No relaxed floating-point tolerance or alternate environment attempt.

Save six reconstructed initial states and roundtrip-check their semantic hashes; they are initial-state replay artifacts, not trained models or automatic authorization for new training. A completed mismatch is FAIL, not BLOCKED; wrong runtime/source/data or incomplete execution is BLOCKED. If the original producer path matches, only producer-path reproducibility is supported: the reason Claude's different path/build mismatched remains OPEN until its underlying records support a cause.

## Actually executed preparation checks

Local runtime: Linux Python3.13.5, torch2.10.0+cpu, NumPy2.3.5, einops0.8.2. No native Parcae repository/runtime was available in this container; a read-only fetch attempt failed DNS resolution. The GitHub connector was used to read source and publish this isolated change. No claim of running inside the user's Codespace.

| Check | Actual status | Limit |
|---|---|---|
| Python compilation and Bash syntax | PASS | Syntax, not model imports |
| Helper fixture unit tests | 6/6 PASS | Six-row completeness, verdict classification, sorted/buffer-sensitive hashes, RNG-neutral capture, safe fixture serialization, no new optimizer/step or extra probe calls |
| Incompatible local runtime | Expected rejection PASS | Actual subprocess exit2, execution BLOCKED, replay NOT TESTED, no reconstructed .pt files; NOT a successful original replay |
| Repeated launcher invocation on synthetic existing result | 4/4 PASS | Preserves bytes; returns0/1/2 for the fixture statuses; missing result blocks; no native model invoked |
| Original six model constructions and count probes | NOT TESTED | Requires the existing pinned user CPU environment |
| Initial-hash mismatch root cause | OPEN | Stage-by-stage evidence pending; no automatic Torch-build explanation |
| New independent Claude/Grok review | NOT TESTED/DEFERRED | Earlier reports cover other work |

Local reproducible preparation files and logs are in Mythos_INIT01_Prepared_20261030.zip. The fixture models in helper tests are NOT native-model substitutes and their PASS results are not experimental outcomes.

## Next single action

In a clean isolated worktree of this branch, execute:

    bash research/mini_mythos/init_replay/run_codespaces_cpu.sh

Defaults reuse /workspaces/mythos-m2-cpu312/bin/python, /workspaces/mythos-parcae-pinned and /workspaces/OpenMythos/mythos_evidence/m2_long_v1/pilot.json. No dependencies/corpora/upstream clone downloaded. Output: NEW /workspaces/OpenMythos/mythos_evidence/init_replay_v1/result.json, six reconstructed initial .pt files, and pip-freeze.txt. Existing output is read-only or blocked; never delete/recreate it to conceal a mismatch.

Exit0=bounded execution and all-six exact replay PASS. Exit1=complete replay but one or more initial identities differ. Exit2=BLOCKED. Read execution_status and initialization_replay_status separately. Transfer the NEW result only when obtained; do not request the already-audited M2-T result again.

One completed run ends the task. No automatic new training, variants, build matrix, gradient-coverage repetitions, parameter patch or GPU allocation. Later stage decisions must distinguish a producer-path reproduction from a causal explanation of Claude's discrepancy. Keep original negative results, inactive parameters, binary/reviewer handoff limits and original PRs unchanged. Formal Oracle stays BLOCKED/NOT_READY, FORMAL_ACCEPTANCE_READY=False; J1/Bench/R3 and G2 REAL are untouched.
