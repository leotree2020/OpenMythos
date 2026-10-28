# F3B-D1-A-CPU-003 E1-A G1 REAL-001 — final cross-review closeout checkpoint (2026-10-28)

**Status: G1 REAL-001 CROSS-REVIEW PASS / G1 CLOSED FOR THIS ONE RUN.** This is an evidence-review and document-only closeout, **not** a new experiment, retest, code change, or authorization for G2/G3/BV/E1-A.

## Provenance and immutable inputs

- Source branch before this documentation stage: `d1-r3-a-cpu-003-e1a-g1-impl-20261027`, verified remote HEAD `450914367c247231c51be02e13775cb001e69c5d`.
- Execution-time HEAD and authorization binding `git_head`: `3eef8d75d61fa6acad3b45a6e632c21ae1ee8f9d`.
- G1 tested-code SHA (same executable source, without subsequent evidence/docs commits): `d175a1ab89c521ec78de9fa39fb139a0e20b1788`.
- Raw evidence commit: `4a92106fc463b88f01b67521f787ec587271b1cb`; evidence-commit-record HEAD: `450914367c247231c51be02e13775cb001e69c5d`. The three SHA roles must not be conflated.
- Run ID: `g1_20261028_025922_68ac93`. One real `--execute` invocation, recorded UTC `2026-10-28T02:59:51.434637945Z` to `02:59:55.074352487Z`, external exit code 0, empty stderr.
- Frozen G1 criteria V1 SHA-256: `1992d75ded16aeedc6eb2d3bb99fe799fb64d514eb08b5e86b2decb68b811257`. Frozen G1 preregistration SHA-256: `3748723794b6742baa3a59e1cc8ebcb65471e3418d8c13328c8131e274e2cd69`. G0 V5 / Bench / R3 / Parcae / model architecture unchanged in source comparison.
- G1 CPU gate had previously passed 289 unique tests × 2 full runs, separately cross-reviewed. A pure CPU test pass is not a real gate pass.

## The real test evidence and acceptance

The original checkpoint is `docs/F3B_D1_A_CPU_003_E1A_G1_REAL_001_CHECKPOINT_20261028.md` (historically marked CROSS-REVIEW PENDING; preserved unchanged). Source files:

- `a_predicate_003/evidence/g1_20261028_025922_68ac93/registry.jsonl`
- `a_predicate_003/evidence/g1_20261028_025922_68ac93/g1_evidence.json`
- `a_predicate_003/evidence/g1_20261028_025922_68ac93/g1_summary.json`
- `a_predicate_003/evidence/g1_20261028_025922_68ac93/g1_closed.json`
- `a_predicate_003/g1_real_001_results/SHA256SUMS.txt`, `G1_REAL_001_REPORT.md`, `g1_exec.exit`, `g1_exec.stdout`, `g1_exec.stderr`.

The four cases were T1 ABORT (PID 312, `A`=65, exit 111), T2 EOF (PID 313, no byte, exit 111), T3 INVALID_BYTE (PID 314, `r`=114, exit 111), T4 TIMEOUT (PID 315, no byte, exit 112). Four forks, no release byte `R`, no `RELEASED`, `FIRST_ACTION`, `READY`, signal violation, descendant, or residual node. Each child was observed as `Z` before a specific-PID `waitpid` returned the same PID and a subsequent `/proc/<pid>` check found no entry; final observer FD count returned to four. T4 elapsed roughly 2.005 s from fork-before timestamp to pidfd-readable, inside the frozen 1.8–5.0 s window; last identity snapshot met the 0.5 s gate-deadline margin. Overall in-process duration 3.502 s (< 30 s).

All G1-C01…G1-C17 statuses were PASS for each of T1–T4 and the four run-level checks C01/C02/C16/C17 PASS; no FAIL/BLOCKED. The registry has 19 records, memory and persisted copies agree. The closure marker records PASS / exit 0 and is bound to the evidence/summary by their SHA-256 and byte length. Auth ID `g1_auth_20261028_025944_cc36f98a` was consumed once, its body and `authorization_used.json` intentionally excluded from Git. Post-run `--check` reports the auth consumed.

## Reviewer dispositions, independently distinguished

- **ChatGPT:** direct read-only retrieval of the pinned GitHub raw evidence, registry, summary and closeout; independent SHA-256 recomputation **18/18**, **60/60** additional source-grounded checks PASS; code/commit comparison verified only evidence/docs were added. Conclusion: `G1 REAL-001 CHATGPT REVIEW PASS`.
- **Grok:** project owner relayed a read-only raw-evidence assessment: 4 exits 111/111/111/112, four matched (PID,starttime), gate stimuli, Z → exact-PID waitpid → `/proc` gone, 19/19 registry fidelity, closure binding and no signals. Conclusion supplied: `G1 REAL-001 CROSS-REVIEW PASS`. **The original Grok report is not separately archived in this branch; this line faithfully records the owner-provided report, not an independently fetched Grok artifact.**
- **Consolidated disposition:** `G1 REAL-001 CROSS-REVIEW PASS`. This is an acceptance of the one recorded run and its evidentiary scope, not proof of universal kernel-level signal absence, statistical reliability, Parcae correctness, reasoning gains, or a G2/G3 result.

## Residual risk, scope, and safety

- Python-level instrumentation does not prove all possible kernel paths; one run does not establish statistical stability.
- The Git archive verifies the byte content of `g1_closed.json` and `g1_closed.json.tmp`, but not hard-link inode identity on the original VM. The original auth body is intentionally unarchived; its consumption and bindings are corroborated by saved evidence.
- `G2 / G3 / BV / E1-A / REAL D1: NOT AUTHORIZED`. No new processes, tests, signals, GPU use, upstream patches, or changes to the frozen G1 criteria are authorized by this document.
- **Git checkpoint:** documentation stage begins from `450914367c247231c51be02e13775cb001e69c5d`. Record final documentation branch SHA when pushed; the historical execution SHA must not be overwritten by that new SHA.

## Unique next instruction

**Only a document-level G2 source audit and design draft** may follow on a separate documentation branch after G1 closeout. The G2 design is NOT an approval of G2 criteria freezing, implementation, CPU tests, real runs, cleanup signals, G3, BV, or E1-A. Obtain ChatGPT and Grok design cross-review, resolve disagreements by designing a minimal controlled test (not running it), and request separate owner authorization for any later implementation.
