# MYTHOS-B1-ROPE-DIAG-V1 (protocol v1.1 + C1–C3) — checkpoint: BLOCKED at target-machine access; nothing executed

2026-11-01. Branch `mythos-base-v01-rope-diag-v11`, created from B1 result checkpoint `d88be474ebb2529c5b095e3732b1f25509f9b824`.

## Decision

**Diagnostic execution: BLOCKED. Scientific conclusion: UNRESOLVED (nothing was computed).**
The authorization requires execution only on the named target (Codespace `bookish-pancake-vwqx7rr9x5w3wxjr`, env `/workspaces/mythos-base-v01-cpu312`, upstream `/workspaces/mythos-parcae-pinned`,
original B1 evidence `/workspaces/mythos-evidence/base_v01/b1/b1-20261101T021657Z`) and forbids running elsewhere, installing substitute dependencies, or changing the protocol.
This session has no access to that machine: `/workspaces` does not exist in this container, and `list_computer_folders` returned no connected computers (`folders: []`, `cannot_be_used: []`).
The original weights, `config.json`, the frozen environment and the original B1 run directory are therefore unreachable. The weights are not on any GitHub branch and must not be.
Per the stop rule I did not substitute another environment, did not download the weights, and did not change the protocol.

## What was and was not done

| Item | Status |
|---|---|
| Recover state from repository and checkpoint | DONE (read-only, see below) |
| Frozen protocol text committed (`PROTOCOL.md`, commit `b0dbc7c7272645a7b7ba125372e507e92868cb4a`) | DONE — a transcription of the owner's messages; their originals govern |
| Diagnostic implementation (I32, N, T, P, R, Q, metrics, sealing) | **NOT DONE** (not written: it could not be run, and untested single-shot numerical code would put the one permitted protocol run at risk; no frozen execution commit exists) |
| G0 identity / derivations / runtime | NOT TESTED |
| G1 N1/N2/N3/I32 controls | NOT TESTED |
| G2a/G2b historical environment comparison and scalar reproduction | NOT TESTED |
| G3 paths T/P/R/Q with two independent evaluations each | NOT TESTED |
| G4 structure | NOT TESTED |
| G5 invariance and sealing of numeric evidence | NOT TESTED (no numeric evidence exists) |
| Metrics, `diagnostic_match`, `bitwise_match` for N/T/P/R/Q | NOT TESTED |
| Formal run / run-id | none created; **no run directory exists** |

No numerical computation of any kind was run (no torch import, no S read, no candidate, no fixture, no helper suite). The only commands were Git, file listing and reading.

## State recovered (read-only)

- Remote `mythos-base-v01-b1` = `d88be474ebb2529c5b095e3732b1f25509f9b824` (unchanged); no branch `mythos-base-v01-rope-diag-v11` and no `rope_diag_v11` directory existed before this checkpoint; no earlier diagnostic run or checkpoint exists.
- B1 execution HEAD `f0541330…` (adds only `requirements.lock`, sha256 `84440f8945041ed314c29b205c5244e074116ede023d5aae0b11b633b4d6a51e`); implementation origin `d39eabb0…`.
- Read at `d88be474`: `CHECKPOINT.md`, `verify_load.json`, `env_check.json`, `summary.json`, `manifest.json`, `evidence_bundle_manifest.json` (36 entries, listing checked), `operator/source_preflight.json`, `operator/post_stop_audit.json`;
  `base_v01.py` from the frozen implementation (hash equal to the value recorded on the target) and its A5 code; pinned upstream RoPE helper, Parcae construction, config derivation, block and receval constructor. `run_base.py` was checked by hash only. `requirements.lock` presence confirmed, content not re-read.
- Historical comparison value (from the committed `verify_load.json`): `0.00012207025429233909`, threshold `1e-6`, shape `[1,2048,1,64,2]`, A5 BLOCKED before `load_state_dict(strict=True)`.
- Upstream local copy (not the target's): `69284c13746e849104f738d6d1a347b1f457df76`, clean. The target's `/workspaces/mythos-parcae-pinned` was NOT inspected.
- PR #24: open, draft, not merged, head `4308099bfc90d9398f54a47f9272b6bd4582f7b9` (read-only observation; no write).

## Not verified here

Original `pytorch_model.bin` / `config.json` bytes and hashes on the target, the S tensor, the target environment and CPU capability, the target's current runtime state, and every item above marked NOT TESTED.

## Boundaries kept

Upstream, A5 threshold, the original B1 result and run directory were not changed; B1 was not re-run; B2/D2-A not entered; PR #24 not touched; no PR created; no force push.
B1 remains: A5 BLOCKED; A3 overall and A8–A11 NOT TESTED; language quality NOT TESTED; Formal Oracle BLOCKED/NOT_READY; `FORMAL_ACCEPTANCE_READY=False`.

## Git identity

- Branch `mythos-base-v01-rope-diag-v11`. Protocol commit `b0dbc7c7272645a7b7ba125372e507e92868cb4a`. There is no frozen execution commit (no implementation). The commit containing this file is the checkpoint commit (its id is given in the final reply).

## Unresolved

1. Access to the target machine. 2. The diagnostic program does not exist and has never been run, so its first run will be its first execution.
3. The single-shot rule (no fix-and-rerun after seeing results) means an untested program carries real risk of a stop caused by a program defect rather than a numerical finding; this should be decided by the owner (see next instruction).

## Next single instruction

Provide an authorized path to the target Codespace (for example Remote Control for that machine, or a session started inside it) and say whether the diagnostic code may first receive a static review and a fixture-only dry run that touches neither S nor the real weights before the one formal run; if no such pre-run check is allowed, accept that a program defect will end the single run as BLOCKED/FAIL.
This checkpoint authorizes no computation, buffer replacement, threshold change or B1 re-run.
