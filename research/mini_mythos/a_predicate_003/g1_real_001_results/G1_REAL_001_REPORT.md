# G1 REAL-001 — first real G1 execution (F3B-D1-A-CPU-003-E1A-G1-REAL-001)

**Result: G1 REAL EXECUTED — CROSS-REVIEW PENDING.** Recorded verdict of the single execution: **PASS** (runner exit code 0, `g1_closed.json` published, 4 tests × 17 checks PASS, 4 run-level checks PASS). The verdict is not final until ChatGPT and Grok have independently reviewed the raw evidence. G2/G3, BV and E1-A: **NOT AUTHORIZED**.

## Purpose, environment, code
* Purpose: one real, controlled negative-gate run (T1 ABORT → T2 EOF → T3 INVALID_BYTE → T4 TIMEOUT): an unreleased gated child (never sent `b"R"`) must perform no experiment action. Scope: G1 only; not evidence for G0 (already closed), G2/G3, BV or E1-A.
* Environment: Linux 6.18.44-fc-v180 x86_64 (VM), 4 CPUs, uid 0, Python 3.13.16 (`python3 -B`), no GPU.
* **Execution-time Git SHA: `3eef8d75d61fa6acad3b45a6e632c21ae1ee8f9d`** (branch `d1-r3-a-cpu-003-e1a-g1-impl-20261027`, local = remote, clean tree; tested code SHA `d175a1ab89c521ec78de9fa39fb139a0e20b1788`, docs/evidence only on top). The evidence-commit SHA is different and is recorded separately in `EVIDENCE_COMMIT_RECORD.md`.
* Frozen inputs unchanged: G1 criteria V1 `1992d75d…1257`, G1 prereg `37487237…cd69`, E1-A prereg `e6b7ca5c…ec39`, G0 criteria V5 `d36da0c0…b821`, G0 prereg `8338f4a0…e25c`, Bench `b6f52a8c…d3b0`, g0_code `1a2d71e3…586f`, g1_code `b7ab2a44…062c`, G0 REAL-001 reference (closure marker) `de96e1be…9736`. All ten authorization bindings equal the actual values at start and end of the run (`bindings_start` = `bindings_end` = `auth_expected` in the evidence).

## Pre-execution checks (nothing was started before they passed)
See `pre_execution_state.txt`: HEAD = remote HEAD, clean tree; no existing G0/G1 residue, observer children or unclosed historical runs; no MANUAL_DISPOSITION_REQUIRED.json; /proc enumeration complete; G0 REAL-001 reference verification PASS; `safe_preflight()` for the chosen run_id returned ok / no problems (read-only, no child process); the run directory did not exist.

## Authorization (body not committed, not logged)
* id `g1_auth_20261028_025944_cc36f98a`, schema `e1a-gate-auth-g1-1`, stage G1, expires `2026-10-28T03:59:44Z`; created exclusively, mode 0600, excluded via `.git/info/exclude`, never committed; `--check --auth` showed `authorization_valid: true` before execution. No commit was made between creation and execution.
* Consumed exactly once before the first fork: `evidence/_g1_consumed/g1_auth_20261028_025944_cc36f98a.json` (id, bindings, consumed_utc, run_id — no authorization body). A post-run `--check --auth` reports the authorization as already consumed (`g1_check_post_run.json`) — single use confirmed.
* `authorization_used.json` (in the run directory) and the authorization file stay local and are not committed.

## The single execution
* run_id `g1_20261028_025922_68ac93`; command (exactly one call): `python3 -B research/mini_mythos/a_predicate_003/gate_g1/g1_run.py --execute --auth research/mini_mythos/a_predicate_003/AUTHORIZATION_E1A_GATE_G1.json --run-id g1_20261028_025922_68ac93`
* start 2026-10-28T02:59:51.434637945Z, end 2026-10-28T02:59:55.074352487Z (`g1_exec.start_utc/.end_utc`); exit code 0 (`g1_exec.exit`); stdout `{"run_id": "g1_20261028_025922_68ac93", "exit_code": 0}`; stderr empty. No retry, no loop, no timeout wrapper, no second `--execute`.

## Independent judgement (C01–C17; `independent_verify.py`, `independent_verification.txt`, `g1_checks_table.md`)
Exit code 0 alone was not accepted: the evidence and summary were hash-verified against `g1_closed.json` and every point below was re-asserted from the saved evidence without using `g1_judge`.
* Order T1 → T2 → T3 → T4; 4 forks (pids 312, 313, 314, 315; starttimes 20097, 20139, 20181, 20223), one per test, never more than one child, zero grandchildren/descendants; the registry is the exact sequence RUN_START, 4 × (INTENT, FORKED, REGISTERED), ABORTED (T1 only), 4 × DEAD, RUN_END — no RELEASED, FIRST_ACTION or READY; `b"R"` never written; guard gate writes exactly [65] (T1) and [114] (T3), closes one per test; messages received by the observer from any child: 0.
* Exit statuses: T1 111, T2 111, T3 111, T4 112 (as designed); each `waitpid(pid, WNOHANG)` was on the specific pid and returned that pid; the pidfd became readable and the child was seen in state Z **before** any wait in all four tests; `/proc/<pid>` gone after reap; per-test PID/starttime consistent across fork event, registry, snapshots and node record.
* T4: exit 2.004 s after fork (required 1.8–5.0 s); last identity sample 1.698 s before the exit (≥ 0.5 s required). T1–T3 exits 0.31 s after fork (gate action 0.3 s hold + stimulus).
* Zero signals (guard violations [], no kill entries other than `already_exited`); total run time 3.502 s (≤ 30 s); cleanup ok in all tests, residue 0, final snapshot S9: no children, no token residue, observer descriptor baseline restored (4 fds).
* Result: all 17 checks PASS for each of T1–T4, G1-C01/C02/C16/C17 PASS at run level; summary verdict PASS, `g1_closed.json` recorded_verdict PASS / exit 0 with evidence and summary SHA-256 bound and verified (`g1_closed.json.tmp` is the identical hard link left by the atomic publication, as in G0).
* `process_exit_proof` in `g1_closed.json` is `false` by design (a marker cannot prove its own process exit); the exit code 0 observed from outside is recorded in `g1_exec.exit`.

## SHA-256 of the evidence
See `SHA256SUMS.txt` (covers this directory and the run directory's committed files). Run directory: `a_predicate_003/evidence/g1_20261028_025922_68ac93/` (registry.jsonl `30acd639…a258`, g1_evidence.json `52b59584…a8a0`, g1_summary.json `b0b96d5d…381f`, g1_closed.json `894740d3…3fc9`).

## Git state, unresolved issues, next step
* Git state after the experiment: no tracked file changed by the run; new untracked evidence only (committed in the evidence commit; authorization files remain excluded).
* Limits (honest scope): a Python-level guard is not proof that no kernel path exists; G1 covers only the negative gate, not any released/positive path, process trees, or signals (those belong to G2/G3, not authorized). A single run demonstrates behaviour once, not statistical stability.
* Unresolved: none observed. No FAIL, no BLOCKED, no manual disposition.
* **Next, only: hand the raw evidence to ChatGPT and Grok for cross-review.** No second real execution; no automatic entry into G2, G3, BV or E1-A.
