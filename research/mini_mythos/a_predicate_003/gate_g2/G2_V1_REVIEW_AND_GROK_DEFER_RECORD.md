# G2 V1 — ChatGPT independent read-only review and temporary Grok deferral (2026-10-28)

## Provenance and authority boundary

- Reviewed pinned remote commit: `ee7e9d46bc46b8dc15cc66ca06569d32a677561d` (V1) based on frozen `bench/` at `450914367c247231c51be02e13775cb001e69c5d`. Remote GitHub HEAD and diff were checked directly, with only 7 documentation files changed from prior revision base `8f9e8b2c027b3f6c0b738650b57af62d52dce141`.
- Independent reviewer: **ChatGPT**. **Result: G2 V1 DESIGN CHANGES REQUIRED**; not BLOCKED (readable and reviewable), not a G2 test result.
- Grok: user reported that Grok reached usage limits and on 2026-10-28 authorized continuing in the meantime using ChatGPT's assessment. **GROK REVIEW: DEFERRED / NOT PERFORMED. OWNER TEMPORARY REVIEW-WORKFLOW EXCEPTION: documentation work may proceed.** This is neither a claimed Grok opinion nor automatic dual-review PASS; future design freeze, code implementation, CPU execution, REAL run and other phases require their own authorization.
- No G2/G3/BV/E1-A implementation, testing, authorization file, real process, signal, GPU, upstream modification or altered frozen criteria is covered by this record.

## Source-grounded V1 findings

| ID | Severity | Grounding and minimal concern | Required design disposition |
|---|---|---|---|
| **V1-R1** | HIGH | `bench/observer.py::_on_created` trusts creator `CREATED.pid`; `_register` verifies stable pid/starttime and `ppid == creator`, not gate-to-pid uniqueness. `/proc/<pid>/fd` pipe inode match does **not** prove exclusive receipt of gate `R`, directionality, trusted sender or actual unique fork relationship; shared gate fd with same-PPID sibling can satisfy partial checks. `READY` and `FIRST_ACTION` arrive after release and are socket-originated claims. | Separate **trusted-creator scenario** vs **adversarial process-attribution guarantee**; remove unsupported strong creation-lineage and pre-release preventive PASS claims. Negative fixture should document that frozen Observer may wrongly accept. Distinguish preventative G2 driver from baseline behavior, no equivalence claim. |
| **V1-R2** | HIGH | `bench/node.py::node_main` never calls `waitpid`; `Observer.reap_direct` only handles own children; `common.process_is_dead` counts Z as dead. Creator `WAIT_REPORT` + observer Z → /proc gone gives corroboration, not independent proof that creator made the exact wait call. | Use `REAP_CLAIMED` vs `REAP_CORROBORATED` vs `REAP_CONFIRMED` by direct trusted wait instrumentation; do not promote a creator claim to kernel-proven fact. Define trusted wait recorder, orphan/auto-reap, `SA_NOCLDWAIT`, SIGCHLD, other reapers and fail-closed classifications. |
| **V1-R3** | MEDIUM | V1 G2-D04/D05/D07 CPU fixtures describe expected *subject* BLOCKED but also use BLOCKED as though it were the *test's* verdict. | Record `expected_subject_verdict`, `actual_subject_verdict`, `test_acceptance_verdict` separately; e.g. damaged evidence fixture with expected subject BLOCKED is **test PASS** if judge outputs BLOCKED. |
| **V1-R4** | HIGH | V1 SX1–SX4 forbids SIGKILL, yet closing a control socket may not deliver EOF while another holder remains; `bench/common.py:T_NODE_MAX=120s` exceeds tentative total 60s; a creator crash may orphan descendants and cannot authorize observers to `waitpid` non-children. `MANUAL_DISPOSITION_REQUIRED` records uncertainty, not proof of cleanup. | Explicit lawful reaper, EOF descriptor-holder and bounded-deadline model; no guaranteed zero residual from a best-effort scan. A REAL plan remains blocked until a credible no-signal exit/settlement plan is independently reviewed and per-node residual responsibility is documented. |
| **V1-R5** | LOW | V1 §8 refers to O-1…O-14 as if decisions required for freeze but O-15 is relevant to plan B; D03a–e make 14 separately identifiable cards although D01–D10 are 10 groups. | Spell out card IDs, scope, exact blocking decisions. |

## Review result and next operation

**G2 V1 DESIGN: CHANGES REQUIRED**. The following V2 work is explicitly **DOCUMENTATION ONLY** under the temporary Grok review deferral. Preserve V1 byte-identically in `G2_IDENTITY_DESCENDANTS_DESIGN_V1_ee7e9d4.md` for provenance; modify the active design, note which claims were weakened and list decisions as *provisional proposals*, **not frozen owner choices**.

**Next:** prepare V2 and checkpoint without CPU tests, processes or signals; self-review V2 against all findings. Do not represent any review waiver as a completed Grok review or as authority to run G2.
