# Decode-control launcher review

**Verdict: APPROVE the corrected launcher for the separately registered attempt using unchanged implementation A.** This approval is limited to orchestration; the decoding experiment is still NOT TESTED at review time.

| Field | Record |
|---|---|
| Purpose | Review the external-launch repair and actual stdlib-only subprocess smoke evidence before numerical execution. |
| Environment | Local Windows read-only source/JSON/byte-hash review. Smoke evidence was produced on Codespace `bookish-pancake-vwqx7rr9x5w3wxjr` with the CPU Python 3.12.3 interpreter. |
| Input | `mythos_launch.py`; 25 files under `DEVELOPMENT_SMOKE/`, including raw child outputs, claims, completions, duplicate record and timeout observation. |
| Expected | No standard-library shadowing; exact output capture; correct exit classification; duplicate refusal without overwrite; timeout cleanup of a TERM-resistant descendant. |
| Actual | All six declared smoke checks agree with their raw records. Source copies match; seven success-case files retain their pre-duplicate hashes. No review mismatches. |
| Status | Launcher development verification **PASS**; formal coordinator/model experiment **NOT TESTED**. |

Reviewed source: **4,374 bytes**, SHA-256 `8083b948eebdf08c2d14a79d940ccead72db5f10c6bac8d9061816b6c9ea05c3`.

The new helper uses an independent directory and `-I -B`, checks that `operator` originates in the standard library, exclusively claims its output directory, and opens logs/completion without overwrite. The downloaded source is byte-identical to the reviewed local copy. Runtime claims resolve `operator` to `/usr/lib/python3.12/operator.py`, report isolated mode, and record no imported numerical libraries.

The six development checks are supported as follows:

1. Success: launcher return code 0, completion `COMPLETED`, child return code 0.
2. Exact stdout/stderr: `MYTHOS_SMOKE_OUT\n` and `MYTHOS_SMOKE_ERR\n`.
3. Correct source identity, isolated imports and standard-library origin match the claim.
4. Duplicate launch: `FileExistsError`, return code 1; all seven original files match both recorded before/after hashes and current local bytes.
5. Negative child exit: launcher return code 2, `CHILD_FAILED`, child return code 7, exact exit-fixture output lines.
6. Timeout fixture: `BLOCKED` with `TimeoutExpired`; TERM then KILL sent, cleanup errors empty. The direct child's recorded return code is -15. The resistant grandchild PID matches its output and the subsequent `/proc` observation is **absent**. The earlier immediate `group_still_exists=true` is retained; it is not misrepresented as a guaranteed instant group disappearance.

These expected negative fixtures are successful tests of failure handling, not formal experiment failures. The wrapper's external SIGTERM handler was statically reviewed but not separately dynamically triggered. Smoke children used `-I -B`; the formal coordinator intentionally omits `-I` to permit its sibling-module imports. The actual coordinator was not exercised by these harmless children.

The prior failed attempt must remain intact. Register a fresh attempt, use this exact reviewed helper and unchanged A `e2605841d7eb21c7d8ecbc07aa55ebe6c76f05b7`, and retain the original stopping and sealing rules. On an abnormal formal child exit, verify that no worker remains before claiming execution has stopped; a leader exit alone does not establish that.

This reviewer performed no launcher/model execution and changed only this review document. No numerical outcomes, model-quality improvements, or B1/B2/D2-A/PR #24 changes are established by these development tests.
