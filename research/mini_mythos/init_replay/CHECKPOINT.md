# P1-R1 checkpoint — 2026-10-30

## Current decision

The M2-L/D/T tiny-model depth series is finished at its frozen scopes, with the negative results retained. The user explicitly authorized continued development after the project summary. This new stage addresses **A-M2L-02 original initialization provenance**, not another schedule, longer training, architecture repair or Guard expansion.

**Native P1-R1 execution: NOT TESTED. Root cause of the reviewer initialization mismatch: OPEN.** Code preparation is not scientific acceptance. Six historical initial hashes are the targets; no quality result can change in this stage.

## Actual reads and historical evidence

The latest PR #15 and `m2_trainmix/CHECKPOINT.md` were read at `4d1ecadc062e190a9bfc8b66b8e2d2962abb266a` before editing. The original M2-T JSON is already supplied/audited: do not ask for it again. Its intervention and extra-depth hypotheses remain FAIL. The current M2-L checkpoint at `bfbb5d01...` records six initialization mismatches and pending raw Claude files; no cause was established.

Original matched-run source was re-read: it constructs GPT then Parcae; applies `pair_io`; executes preflight and count per arm; and only then records `initial_weights_sha256`. Native GPT construction resets embedding/norm parameters. Merely reseeding and creating a standalone unpaired model is not definitionally the same measurement. This is a candidate distinction to measure, **not** an accusation that Claude used an incorrect procedure.

The original M2-L pilot bytes in the uploaded archive were read to extract the six `init_sha` values, IO digests and producer dependencies; its hash is still `c5be0f6da8eab77ab499ad97a3aaf318633d2d44f234083165ffcacc3b26d7bb`. This was not another 18-snapshot audit and no trained weights were loaded here.

## Git identities

- New branch: `mini-mythos-p1r-init-origin-20261030`.
- Base: `4d1ecadc062e190a9bfc8b66b8e2d2962abb266a` (PR #15).
- Preregistration committed first: `ce46fc2a7d053e609c94fed7ecf67ba3f6bc171d`.
- Native diagnostic code commit: `5287cfccada9802c123a3fdf3e8e583e2ab689fb`.
- Launcher commit: `a70ec9df0ab23a8532364d0750cff46e31215632`.
- Helper tests commit: `62e7e5256c6920825dabdb62bef46494f9caa698`.
- Diagnostic source Git blob `6d4e65424d52145d44a275a0012b56798aec913c`, SHA256 `d6bf602f2f714b9d232da927ebc49a684d40fe1289005dc4531970681b759070`; connector blob matches locally compiled/tested bytes.
- Untouched upstream: `69284c13746e849104f738d6d1a347b1f457df76`.

## Purpose / expected / actual

Purpose: recover a trustworthy model starting recipe before any future from-scratch causal comparison. See PROTOCOL.md for exact six-sequence bound and status rules. Required producer-equivalent dependencies are Linux Python3.12.3, torch2.11.0+cpu, NumPy1.26.4, einops0.8.0. Record hardware/build; do not claim different builds are bitwise identical.

| Item | Expected | Actual / status |
|---|---|---|
| Python compile | diagnostic compiles | PASS in local Python3.13.5 |
| Bash syntax | launcher parses | PASS (`bash -n`) |
| Helper unit tests | missing/duplicate rows rejected; mismatches/mutations not promoted; full-state hashing includes buffers | 8/8 PASS in local torch2.10.0+cpu; synthetic fixtures only |
| Source upload identity | GitHub diagnostic blob equals locally checked bytes | PASS |
| Original six initial states reconstructed | exact original hashes after original factory/pairing/preflight/count | NOT TESTED |
| Per-tensor stage localization | changed names and stage hashes recorded | NOT TESTED on native models |
| Original probes preserve model state and caller RNG | exact pre/post identities | NOT TESTED |
| Reviewer mismatch explained | original Claude method/output or controlled comparative evidence | OPEN; original files still missing |
| New Grok/Claude cross-review | actual review | NOT TESTED/DEFERRED |

No native GPT/Parcae import, forward/backward, optimizer construction/update, corpus metric, training, GPU or upstream modification occurred locally. Local environment is Python3.13.5/torch2.10.0+cpu/NumPy2.3.5/einops0.8.2, unlike the required producer. A network attempt from the container could not resolve upstream GitHub; actual repository reads/writes used the connector. No user's Codespaces terminal is exposed by that connector.

The runnable diagnostic intentionally replays the **original six synthetic preflights and six synthetic count forward/backward probes** to preserve the historical measurement point. That future native execution is not training and has zero optimizer steps. It is not a repeat parameter-coverage sweep; no additional native run has happened yet.

## Next one execution

In the existing user Codespace, fetch this branch and invoke the launcher FROM a pinned Git commit. It reuses `/workspaces/mythos-m2-cpu312/bin/python`, `/workspaces/mythos-parcae-pinned`, and existing `m2_long_v1/pilot.json`. It creates `/workspaces/mythos-p1r1-20261030` only when absent; a conflicting commit is never reset. Existing output is read, never rerun or overwritten.

Output: `/workspaces/OpenMythos/mythos_evidence/p1r_init_v1/result.json`, plus dependency list and sibling console log. No packages, corpora or new trained-weight files are downloaded. No M2-T result upload is needed for this stage.

On completion record separately: execution, historical hash reproduction, probe preservation and reviewer-root-cause status. If exact reproduction passes, only the producer-recipe subquestion closes; A-M2L-02's reviewer discrepancy remains OPEN until supported. If valid native execution mismatches, preserve all stage hashes and FAIL without adjusting seeds, input tensors or tolerances. An unavailable environment is BLOCKED.

## Boundaries

Old scientific results, frozen code/protocols, Parcae, J1, Bench, R3, model architecture and formal Oracle are unchanged. Formal Oracle remains BLOCKED/NOT_READY, FORMAL_ACCEPTANCE_READY=False; no G2 REAL. All prior PRs remain Draft/unmerged. New negative or positive initializer results do not authorize GPU scale-up, new training, automatic PR merge or an efficiency/ACT/reasoning claim.
