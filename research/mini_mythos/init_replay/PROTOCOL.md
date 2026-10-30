# INIT-01: original initialization replay and reusable starting-state capture

Date: 2026-10-30. Status at protocol commit: native execution NOT TESTED.
Base: 4d1ecadc062e190a9bfc8b66b8e2d2962abb266a (PR #15).

## Stage decision

M2-L/M2-D/M2-T are retained as scoped negative results. Do not add more schedules, longer continuations, GPU scale-up or architecture changes merely to obtain PASS. The user authorized continued development after the progress review. The next bounded task addresses A-M2L-02 (six whole-model initialization mismatches reported by Claude), which limits subsequent reproducible baseline comparisons. It does NOT repeat the already performed A-M2L-01 gradient-coverage diagnostic or require missing reviewer files before code preparation.

## Single question

Using the original producer CPU environment and the EXACT original constructor/helper bytes, can all six historical initial model-state hashes be reproduced? Capture stage-by-stage state fingerprints and the reconstructed initial state files for subsequent comparisons. Do not reset to trained weights or substitute a trained-state hash for an initial-state hash.

## Frozen inputs and operations

- Unmodified sandyresearch/parcae@69284c13746e849104f738d6d1a347b1f457df76.
- Existing research/mini_mythos/m2_matched/experiment.py SHA256 74f00c64448ddbc224a48ef83dc031a90c33448ccb92647666707f6b8f988967.
- Existing frozen_config.json SHA256 a49b38521a45e716b1cb5f2c2b55d317d06ca7542d02623349c5331e9fe26447.
- Historical matched pilot SHA256 4960841f1f685326cf8a4c7d1198718346ef38b8ce0a3d0fb8d48d70daa0637d. Expected initial hashes and shared-IO fingerprints must come from that original record, not new reconstructed data.
- Existing M2-L pilot SHA256 c5be0f6da8eab77ab499ad97a3aaf318633d2d44f234083165ffcacc3b26d7bb. Require its six init_sha and shared-IO records to agree with the historical matched pilot before model construction.
- Seeds 42/20261029/20261030; GPT FFN60 and unchanged native Parcae FFN64/[0,2] configurations. No alternate seeds, model variants, Python/Torch builds, tolerance search or dependency installs in this task.
- Linux Python3.12.3, torch2.11.0+cpu, NumPy1.26.4, einops0.8.0, CPU FP32, one thread, deterministic algorithms, original math SDPA helper behavior. Wrong runtime/source/input is BLOCKED; do not bypass version checks.
- Per seed, preserve original order: make GPT, make Parcae, pair_io; per arm in GPT/Parcae order: original preflight, original count, then original weights_sha. Record registered-state and named tensor fingerprints after construction, after pair_io, after preflight, after count. Record CPU RNG digest at each stage without consuming RNG.
- preflight uses only original synthetic inputs. count uses one original synthetic forward/backward per model, for a maximum of six backward probes in the complete run. This replays a historical initialization recording boundary, not another gradient-coverage study. No optimizer construction/step, clipping, training, natural-language evaluation, corpora, Alice, new FLOP calibration or benchmark.
- Save six reconstructed initial state_dicts, configs and CPU RNG states into a NEW output directory. They are replay observations, not automatically approved training inputs. Do not overwrite any M1/M2 artifacts. Re-running the launcher with an existing output prints the existing result or stops; it must not retrain, delete, reset Git or replace files.

## Acceptance before execution

1. Input identity PASS only if all pinned bytes and clean Git/source checks match; source/producer environment failures are BLOCKED.
2. Historical-record agreement PASS only if six unique seed/arm pairs exist in both original records, expected initial hashes agree, and shared IO data agree.
3. Execution PASS means all six bounded replays complete, stage manifests and six initial snapshots are saved, synthetic preflight/count results meet original recorded values, and sources remain clean. Merely exiting is not sufficient.
4. Initial-state replay PASS requires exact equality of all six final initial-state hashes, including persistent buffers, plus exact shared-IO fingerprints and total parameters. No float tolerance. Any completed mismatch is FAIL; retain all actual/expected values.
5. Record whether each stage changed the registered state; do NOT require probes to be state-preserving in advance, because identifying that boundary is part of this task. Any observed state change is evidence to examine, not permission to patch upstream.
6. Saving and restricted reloading a reconstructed initial state must preserve its semantic state hash. This does not test full training or interrupted-resume equivalence.
7. Cross-review remains NOT TESTED/DEFERRED without an actual new reviewer report. Same-environment replay PASS does not establish why Claude's different reproduction failed. Claude's exact scripts/outputs remain unavailable, so that causal attribution remains OPEN even after a positive replay.

Exit 0: bounded execution and all-six exact replay PASS. Exit 1: completed replay with historical initial mismatch. Exit 2: BLOCKED/input/runtime/numerical execution failure. Separate execution_status from initialization_replay_status.

## Stop rules and project value

A complete run ends this task: no training, alternate build comparison, parameter repairs, depth sweeps or second automatic probe stage. If PASS, preserve the exact reconstructed initial states to remove ambiguity in future separately authorized comparisons; narrow A-M2L-02 to reviewer-path/build attribution still OPEN. If FAIL, retain the first phase where expected equality is absent, known IO checks and per-tensor manifests; choose one later controlled cause test instead of rerunning training. Historical per-tensor initial hashes are not available for every tensor, so do not claim to identify an exact historical tensor mismatch solely from an aggregate digest.

The original M2-T JSON is already received and audited; do not request it again. Six M2-T final binary states, M2-D original JSON and Claude's raw review files stay separate evidence items, not prerequisites for this constructor replay. All prior scientific FAIL results remain unchanged. Formal Oracle stays BLOCKED/NOT_READY, FORMAL_ACCEPTANCE_READY=False; no J1/Bench/R3/model/upstream edit, no G2 REAL and no automatic PR merge.
