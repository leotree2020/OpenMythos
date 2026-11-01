# MYTHOS-DECODE-CONTROL-V1: pre-run evidence review

**Verdict: APPROVE the BLOCKED classification and evidence preservation.** This is not an experiment PASS.

| Field | Record |
|---|---|
| Purpose | Check the external-launch failure, whether the frozen runner started, and preservation of sources and historical evidence. |
| Environment | Local Windows; standard-library file/JSON/SHA-256 checks only. No target access, launcher execution, torch import, model computation, or retry by this reviewer. |
| Input | EXECUTION.json; operator launch, source, stdout/stderr and post-stop audits; EVIDENCE_MANIFEST.json; 11 frozen local files; retained historical manifests. |
| Expected | Traceable pre-run failure; no formal outputs; unchanged protected evidence; integrity PASS kept separate from experiment status. |
| Actual | External helper failed before subprocess invocation; target reports no formal run directory/artifacts. Local hashes, manifest membership and recorded protection results are consistent. |
| Status | Review/integrity **PASS**; launch **BLOCKED**; D0-D4 and language quality **NOT TESTED**. |

## Identity and cause

- Attempt: `decode-v1-20261101T071421Z`.
- Branch: `mythos-base-v01-decode-control-v1`.
- Implementation A: `e2605841d7eb21c7d8ecbc07aa55ebe6c76f05b7`.
- Execution B: `a7ca603bbb5035250a3807f6f82b69d1b14160ad`.

The recorded child command matches EXECUTION.json. The raw traceback proves that the external `operator.py` shadowed the standard-library module: `json -> re -> functools -> collections -> operator` resolved back to the helper, then `pathlib -> glob -> contextlib` attempted to import `deque` from partially initialized `collections`. The error occurs at helper line 1, before its only `subprocess.run` call. The repeated helper frame is a recursive import, not a retry.

This is the root agent's external-launcher defect, outside A and outside the frozen static-review scope. The wrapper used system Python 3.14; the intended, uninvoked child used the separate CPU environment. These records do not establish a model or model-environment failure. No completion record supplies an exact wrapper return code.

`formal_run_started=false`; D0-D4 remain **NOT TESTED**; new generation is **0/84**, new steps **0/5,376**, and new quality evidence is absent. One failed launch is recorded; the operator reports no retry. The failure-before-subprocess plus the target's absent run directory support this classification. Prior results receive no status upgrade.

## Preservation and review limits

All eight final operator-evidence manifest files were locally rehashed: **8/8 matched**. All 11 frozen local files match EXECUTION.json and target expected/actual hashes: **11/11 matched**.

| Historical run | Target-rehashed entries | Mismatches | Complete member count |
|---|---:|---:|---:|
| B1 | 8 | 0 | 10 |
| RoPE | 230 | 0 | 232 |
| Complete load | 723 | 0 | 725 |
| CPU inference | 2,526 | 0 | 2,528 |
| Total | **3,487** | **0** | **3,495** |

The three retained FULL_MANIFEST byte hashes match the target report. All four manifest-plus-exclusions member sets match the recorded directory sets; B1 membership uses its previously retained parsed manifest. The supplemental target audit reports the same directory membership and **106/106 upstream files unchanged** against the prior protection baseline. Its 106 rows all report unchanged.

The target performed the full historical/upstream byte comparisons; this reviewer checked local evidence hashes, original manifests where available, counts and membership, and did not independently reread target private artifacts. The post-stop record reports clean execution checkout B, clean B1 at `d88be474ebb2529c5b095e3732b1f25509f9b824`, and clean upstream at `69284c13746e849104f738d6d1a347b1f457df76`. No new remote/PR query is claimed. The post-stop **PASS** means protection passed, not decoding passed.

## Sole proposed next action

Prepare a separately recorded attempt using a project-specific launcher name in a **fresh directory without the old operator.py on its import path**. Preserve the failed directory unchanged. Review the helper and run a harmless, real **stdlib-only subprocess smoke check** through the actual interpreter and launch/import context before any model invocation. Record the helper/smoke provenance and a new attempt identifier, then use unchanged A under the existing protocol. Merely renaming the entry point while retaining the colliding file on its import path is insufficient.

This review only wrote this document. It did not repair, smoke-test, retry, or modify frozen code, upstream, historical thresholds/evidence, B1/B2/D2-A, or PR #24.
