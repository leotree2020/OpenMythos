# E1-A Gate G2 — J1 pure CPU fixture pre-registration SPEC DRAFT V0

**Task:** `F3B-D1-A-CPU-003-E1A-G2-J1-CPU-SPEC-DRAFT-001` · 2026-10-28  
**Provenance:** based on `G2_V2_1_INDEPENDENT_DESIGN_REVIEW_001.md` at Git `672b20bc8091c42c31786c66b8ea28191584def7`, and reviewed V2.1 delta blob `c2ed7330e9f5e9f18ea6d9461d47aeeace2`. Frozen Bench source blobs: `observer.py=635e73b34203219a3687f86332d0e82362b89670`, `node.py=5bda87c6c9e98a91c32e3d4eadcd1ca94cb2bd8b`, `gate.py=7772c913828ea2184e6acf04cf5628c075dd5a57`, `registry.py=3f2179e132371dd323f865be8a4d41fa5e58786d`.  
**Status:** **DRAFT ONLY / NOT FROZEN / NO CODE / CPU NOT TESTED OR AUTHORIZED / REAL BLOCKED AND NOT AUTHORIZED**. Grok review is `DEFERRED / NOT PERFORMED`, not PASS. All owner decisions O-1…O-15 are UNDECIDED. **No experiments were run to create this document**; all numeric PIDs, times, records and statuses below are *synthetic examples proposed for future authoring*.

## 1. Single falsifiable research question and claim boundary

**Question J1-Q01:** Given *only* explicitly allowed, time-indexed synthetic observables attributed to the **unchanged B0 Observer** and hypothetical read-only witnesses, can a **pure, deterministic, no-side-effect J1 judge** distinguish (a) positive protocol violations, (b) evidence gaps requiring BLOCKED, and (c) a **narrow property supported by the supplied finite dataset**, without incorrectly promoting post-release claims or a ledger record into kernel truth?

The planned J1 tests are **detection-only**. They do not prevent any gate release, execute B0, evaluate a new P1 driver, prove live ancestry, verify Parcae, or assess model reasoning. Use B0 records as the target data model, but **J1 is the future SUT; B0 is not executed during these CPU fixtures**. The B0 model is pinned to source, not a live test result. An expected B0 defect being correctly detected yields **fixture test PASS but observed B0 behavior unsafe**.

**Disjoint assertions (one requested per fixture):**

| `assertion_id` | Allowed conclusion | Explicitly forbidden inference |
|---|---|---|
| `J1-A-ATTRIBUTION` | FAIL if independently observable positive child-vs-registered PID mismatch; otherwise BLOCKED if gate child identity unavailable | Same PPID/starttime/pipe-inode alone proves unique fork or malicious-creator-resistant provenance |
| `J1-A-UNIQUE-REGISTRY` | Over the **supplied finite set of REGISTERED records**, reject two node IDs sharing one (pid,starttime); otherwise PASS that narrow internal uniqueness assertion only | Unseen processes/short-lived children do not exist |
| `J1-A-PREVENT-PROOF` | Require evidence completed **before earliest possible** gate R write for a prevention assertion; otherwise BLOCKED | REGISTERED, RELEASED-intent or post-release READY retroactively proves prevention |
| `J1-A-LAWFUL-REAP` | Z/DEAD/ECHILD alone → BLOCKED for a reaping assertion | Reaped by rightful parent from a dead marker |
| `J1-A-ZOMBIE-AT-T` | PASS for only **Z observed at timestamp T and pinned identity**, with direct /proc snapshot | A zombie has been reaped |
| `J1-A-SIDECAR-INTEGRITY` | PASS only for an internally complete, read-back hash-consistent chain matching a separately supplied trusted final seal; missing prefix/suffix/tail → BLOCKED | Hash consistency authenticates kernel events or unseen events |
| `J1-A-DELIVERY` | Missing actual R-write/receipt evidence → BLOCKED for delivery | RELEASED ledger intent means byte delivered to correct reader |
| `J1-A-WRITE-COMPLETE` | PASS only for a separately declared *successful single-byte R write syscall* evidence | Successful write proves a particular child's identity or execution |

For properties that require a witness unavailable to the unchanged B0, J1 must say BLOCKED. A synthetic witness is **not automatically a real available sensor**; future REAL use would need separate validation and authorization.

## 2. Two physically separate future data lanes — no answer leakage

**Lane S — J1 subject input, future `subject_observables`:** a serialized, finite sequence of **observed** B0 ledger rows, zero or more simulated read-only witness samples, claim messages, and available external-seal metadata. Every observation has a source role (`B0_LEDGER`, `KERNEL_SNAPSHOT_SIM`, `G2_WITNESS_SIM`, `G2_WRAP_SIM`, `SEAL_MANIFEST_SIM`, `NODE_CLAIM_SIM`), monotonic sequence/time, node id, kernel identity if applicable, and an optional read-failure reason. No field `expected_subject_verdict`, `correct_pid`, `oracle_truth`, `is_attack` or `test_acceptance_verdict` may occur in this lane. Any positive child identity must appear as **a source-qualified observation actually available to J1 in that fixture**; it is not the separate oracle's private answer.

**Lane O — private independent acceptance oracle (not passed to J1):** `fixture_id`, `assertion_id`, `truth_model`, `actual_gate_child_pid` if known, `expected_subject_verdict`, `expected_observed_behavior_label`, `expected_test_acceptance_verdict`, controlled-input provenance and independent data/hash manifest. Its producer must not call J1, import J1 output, derive its expected value from J1, or make oracle truth accessible to the SUT. `truth_model` may contain synthetic facts intentionally **not observable by J1**. Example: a private fact that G is the actual child, while only B0's claimed Q is visible, must lead to expected subject BLOCKED (insufficient evidence), not FAIL by telepathy.

**Acceptable witnessing:** `G2_WITNESS_SIM` may show direct synthetic positive facts such as `gate_child_event={pid:4102,creator:4100,gate_id:"gate-A"}`; this is subject input with an explicit simulated independent witness trust assumption. It must never contain a derived conclusion such as `wrong_pid:true` or `expected_verdict:"FAIL"`. Its underlying scenario can be cross-checked by the oracle, but the judge must reason from the **observation itself**. A test using this hypothetical witness can validate J1 logic; **it does not prove frozen B0 actually records the witness**.

**Future immutable fixture schema (document proposal, NOT a created JSON fixture):**

- `fixture_id` (one of exact IDs in §4); `canonical_card` (D01-B0 etc.); `sut="J1"`; `bench_mode="B0_FROZEN_RECORD_SIMULATION"`; `assertion_id`; `claim_scope="DETECT_ONLY"` except an explicitly *rejected* PREVENT assertion; `fixture_version="DRAFT_V0"`.
- `source_code_sha` (pinned commit), `source_blob_hashes` (as above); `subject_input_schema_version`; `oracle_schema_version`; `subject_observables_digest` and `oracle_truth_digest` **NOT_MATERIALIZED** until bytes actually exist. Never invent sha256 for prose examples.
- `input_records` (S), `allowed_witness_sources` (S), `source_trust_assumptions`, `time_order_rules`; `oracle_truth` (O only); `expected_subject_verdict` (O only), `expected_observed_behavior_label` (O only, optional), `expected_test_acceptance_verdict` (O only). Controlled input, expected outcome, FAIL witness, BLOCKED witness, positive-control scope and synthetic environment must be enumerated.
- **After a separately authorized future CPU test only:** `actual_subject_verdict`, `actual_behavior_label`, `test_acceptance_verdict`, raw input/evidence paths + hashes, and separate auditor result. All actual/result fields in this document are **NOT TESTED**.

**Verdict domains:** subject verdict exactly `PASS | FAIL | BLOCKED`; CPU acceptance exactly `PASS | FAIL | BLOCKED | NOT_RUN`. Behavior labels are descriptive only and never substitute for a subject verdict. For a *positive* protocol violation visible to J1: subject FAIL. If essential independent observation missing/unreadable: subject BLOCKED. PASS requires a **narrow claim** proven within its finite record set, not global absence of descendants. If the test instrument is itself broken, test BLOCKED; if J1 returns the wrong subject verdict, test FAIL. A future test of a known B0 bug that returns subject FAIL is a **CPU test PASS (defect successfully detected)**. A missing, skipped or extra unknown fixture ID blocks full-suite acceptance.

## 3. Synthetic values and source provenance (planned, not generated)

All PIDs are **fictional integer labels, never host PIDs**: creator `K=(pid=4100,starttime=100,boot="fake-boot-1",pidns="fake-ns-1")`, ordinary sibling `Q=(4101,101)`, actual gated child `G=(4102,102)`, independent node ids `nA`/`nB`, gate id `gate-A`, pipe inode `555`. `ppid(Q)=ppid(G)=4100`; this similarity is the adversarial ambiguity. The actual B0 serialized registry uses `RUN_START`, `INTENT`, `FORKED`, `REGISTERED`, `RELEASED`, `ABORTED`, `DEAD`, `RUN_END` only. **CREATED/WAIT/EXIT/REAPED are never fabricated as native registry kinds**; hypothetical extra samples exist solely in the separate witness lane. See frozen `bench/registry.py:9` and `bench/observer.py:276–302`.

If a future fixture uses lifecycle complete records, include `RUN_START`, necessary `INTENT`/creator registration chain, monotonic `seq` and required fields so a trivial missing-run parser defect does not mask the targeted variable. A fixture that deliberately lacks records must label the loss as controlled input and expect BLOCKED from the appropriate integrity assertion. `mono` ordering is synthetic; it cannot claim real elapsed milliseconds, CPU speed or kernel timings.

## 4. Complete **selected-scope** fixture matrix: 6 families, 12 exact IDs

**Expected results below are predeclared **design expectations**, not observed results or a frozen test suite.** The future implementation must materialize deterministic bytes and independent digests in a separate, authorized stage. All 12 IDs must be independently included once if this scope is subsequently frozen; omitted canonical cards are explicitly deferred in §5.

| Exact fixture ID | Canonical card / target assertion | Controlled S-lane input and allowed synthetic witness | Private O-lane ground truth (not given to J1) | Expected subject | Expected behavior label | Expected future test if correct |
|---|---|---|---|---|---|---|
| `J1-F01-A` | D03c / `J1-A-ATTRIBUTION` | B0 ledger REGISTERED nA→Q; pre-release kernel PPID Q→K; separate source-qualified simulated witnessed gate child G→K for same ticket/gate | G is actual gated child, Q is sibling; positive mismatch independently observable in S | **FAIL** | `B0_WRONG_PID_ATTRIBUTION_OBSERVED` | **PASS** |
| `J1-F01-B` | D03c / `J1-A-ATTRIBUTION` | Same nA→Q and Q PPID K, but **no** independent gate child observation; no invented exclusive pipe holder | Privately G is actual child, **not observable to J1** | **BLOCKED** | `GATE_CHILD_UNVERIFIED` | **PASS** |
| `J1-F02-A` | D03d / `J1-A-UNIQUE-REGISTRY` | Supplied ledger includes distinct node ids nA/nB each REGISTERED with identical (pid=4101,starttime=101); syntactically well-ordered | Two distinct records assign same pinned identity | **FAIL** | `DUPLICATE_REGISTERED_IDENTITY` | **PASS** |
| `J1-F02-B` | D03d / `J1-A-UNIQUE-REGISTRY` | Supplied **finite complete-for-this-assertion** ledger contains two node ids with different (pid,starttime); non-target records satisfy registry prerequisites | No duplicates in **provided** REGISTERED records only | **PASS**, finite ledger claim | `NO_DUPLICATE_IN_SUPPLIED_SET` | **PASS** |
| `J1-F03-A` | D01-B0 / `J1-A-PREVENT-PROOF` | B0 REGISTERED then RELEASED-intent; no time-completed PRE_RELEASE gate sample; query whether prevention was proved | B0 has no held-release witness in the supplied record | **BLOCKED** | `B0_NO_PRE_RELEASE_WITNESS` | **PASS** |
| `J1-F03-B` | D01-B0 / `J1-A-PREVENT-PROOF` | Same B0 sequence, plus **post-release** READY claim with matching `fp.pid`; still no pre-R witness | READY occurs only after gate write possibility and is socket-originated claim | **BLOCKED** | `POST_RELEASE_READY_NOT_PREVENTION` | **PASS** |
| `J1-F04-A` | D07 / `J1-A-LAWFUL-REAP` | Pinned Z /proc sample + B0 DEAD row + hypothetical creator report `ECHILD`; no trusted wait wrapper | Identity remains zombie at observation, no demonstrable lawful wait | **BLOCKED** | `Z_DEAD_ECHILD_NOT_REAP` | **PASS** |
| `J1-F04-B` | D07 / `J1-A-ZOMBIE-AT-T` | Time T /proc state Z + matching pid/starttime/PPID, source=`KERNEL_SNAPSHOT_SIM`; *claim only Z at T* | Z correctly observed at T, reaping not claimed | **PASS**, Z-at-T only | `ZOMBIE_OBSERVED_ONLY` | **PASS** |
| `J1-F05-A` | D05 / `J1-A-SIDECAR-INTEGRITY` | A 2-record hash-consistent JSONL chain, but separately trusted seal for same run says final_seq=3 and different file byte length/head | Expected third record missing, valid-prefix truncation | **BLOCKED** | `SIDECAR_SEALED_SUFFIX_MISSING` | **PASS** |
| `J1-F05-B` | D05 / `J1-A-SIDECAR-INTEGRITY` | Three canonical records seq=1…3, genesis and prev-hash valid, full file readback, independent seal with matching byte length/sha/head | Sealed contents match **only recorded-data integrity**; event truth remains unverified | **PASS**, archive-integrity only | `SIDECAR_CHAIN_MATCHES_SEAL` | **PASS** |
| `J1-F06-A` | D09 / `J1-A-DELIVERY` | B0 REGISTERED→RELEASED *intent* only; neither R write result nor any independently evidenced recipient | Actual R outcome unspecified/unknown (no private assumption of success) | **BLOCKED** | `RELEASED_INTENT_NOT_DELIVERY` | **PASS** |
| `J1-F06-B` | D09 / `J1-A-WRITE-COMPLETE` | B0 RELEASED intent **plus** `G2_WRAP_SIM` raw `R_WRITE_RESULT(bytes=1,write_error=null)` for gate-A, with matching node and ordered times | Hypothetical wrapper's single-byte R write succeeded, **receipt not established** | **PASS**, write-syscall result only | `R_WRITE_COMPLETED_NOT_RECIPIENT_PROOF` | **PASS** |

**Explicit discriminatory controls:** J1-F02-B, F04-B, F05-B, F06-B are carefully limited PASS cases. J1-F01-A/F02-A provide positive FAIL cases. J1-F01-B/F03-A/F03-B/F04-A/F05-A/F06-A provide BLOCKED cases. Thus always returning BLOCKED, always returning FAIL, or merely parroting a label **cannot pass the whole selected suite**. A future model could still overfit this synthetic set: the test is a narrow correctness gate, not a generalization guarantee.

**Assertion-specific epistemic ceilings:**
- `J1-F01-A` requires **observed contradictory identities from two distinct allowed sources**; without the G2_WITNESS_SIM sample, `J1-F01-B` is BLOCKED despite the oracle privately knowing G.
- `J1-F02-B` PASS means only “no duplicate among the supplied records,” never “no invisible PID/descendants.”
- `J1-F04-B` PASS means only “this process was observed Z at T,” never “reap confirmed.”
- `J1-F05-B` PASS means only “log bytes match an independently trusted seal,” never sender authenticity.
- `J1-F06-B` PASS means only “an observed write syscall returned one byte,” never that a specific process read R.
- The synthetic trust tier on an external witness or seal **must be displayed** in results; no synthetic fixture can certify that real-world instrumenting exists.

## 5. Complete canonical inventory — no silent scope inflation

The upstream V2.1 design enumerates **14 historical canonical cards**, and splits D01 into **D01-B0** and **D01-P1**, hence **15 arm-qualified candidates**. This SPEC DRAFT selects exactly **six** arm-qualified targets: `D01-B0`, `D03c`, `D03d`, `D05`, `D07`, `D09`.

The other **nine** are explicitly `DEFERRED_BY_SCOPE`, **NOT TESTED / NOT AUTHORIZED / not implicit PASS**: `D01-P1`, `D02`, `D03a`, `D03b`, `D03e`, `D04`, `D06`, `D08`, `D10`.

Each selected target maps to two fixture IDs (12 total); the matrix in §4 is the complete selected inventory, not a claim of covering all G2 cards. **Case-level coverage** = 6/15 arm-qualified candidates planned, not tests run. **Actual test coverage** = 0/12, NOT TESTED. No frozen acceptance percentage and no model-ability inference.

## 6. Proposed future CPU-only acceptance (not active)

For a separately approved future implementation/CPU run:

1. Before code import, validate an approved **no-process/no-signal guard** against forbidden operations on both import and runtime paths: os.fork/forkpty/posix_spawn/exec family, subprocess, multiprocessing workers, wait*/kill*/killpg/pidfd_send_signal, janitor, shell invocation, GPU. Guard must record attempted call and stop; a Python guard is not a kernel proof. The guard strategy itself is OPEN and may require separate review.
2. The J1 SUT is a **pure function** receiving only Lane S. No /proc reads, no direct clock sampling, no import of native B0 runtime objects, no machine environment dependence, no external files/network, no irreversible action. The independent oracle receives J1 result and Lane O, and only it compares expected outcome.
3. Each fixture must have a unique ID and exact frozen `assertion_id`, source hash, input digest, truth digest, precommitted expected subject, behavior label and expected acceptance. No discovery/change of expectations after observing J1 output. For this draft, fixture bytes and hashes are `NOT_MATERIALIZED`, all actual results `NOT TESTED`.
4. Enforce 12/12 selected IDs exactly once with no skip/unknown and independently validated oracle isolation; test-level expected PASS is **conditional on correct implementation**, not a current status. Contradictory fixture construction => SPEC NOT_READY or test BLOCKED, not PASS.
5. At test level: **FAIL on deterministic output mismatch or proven guard violation; BLOCKED on oracle corruption or missing required input/evidence; PASS only on matching predeclared expected subject + valid guard + verified records**. Apply test aggregation FAIL > BLOCKED > PASS; a missing fixture or skipped fixture makes full run BLOCKED, and no CPU PASS is transferable to REAL.
6. Preserve complete raw input, oracle manifests, J1 output, guard logs, independent check table, Git/sha/env, durations, file hashes, closure and one next-step checkpoint. Only after separately authorized CPU execution may such artifacts exist or be labeled actual PASS.
7. Do not alter frozen Bench, G0/G1/R3, Parcae upstream or Recursive Transformer architecture. This J1 suite is **about detecting experimental infrastructure defects**, not evaluating model gradients, recursion quality, performance or inference.

**Design-document acceptance proposal:** a future design reviewer may accept this **SPEC DRAFT** for later fixture materialization only if every selected assertion has a source-grounded claim bound and two-lane separation; if any witness assumed real is actually synthetic, it stays labeled hypothetical. The seal custodian and witness trust remain OPEN for real use. Do not freeze without owner decision and design review.

## 7. Open decisions, prerequisites and unique next instruction

- O-1…O-15: **owner_decision UNDECIDED**; reviewer suggestions only. Grok: **DEFERRED / NOT PERFORMED**, not PASS. The user-authorized temporary exception allows writing documents, not a fictitious second reviewer.
- **Design issues to review before future freeze:** exact canonical bytes, selected 12 fixture input JSON and sealed manifests, finite source completeness, any unseen-source proof, choice of J1 function API, input guards, oracle/truth separation implementation and whether behavior labels are output by the SUT or computed externally. These are specifications, **not coded yet**.
- **REAL remains BLOCKED**: lawful creator wait (plan A still only recommended), no-signal anomalies, orphan/FD uncertainty, independently authorized disposable environment and external manual liability have not been established.
- **No G2 code, no CPU tests or process tests, no authorization file, no signals, no GPU and no next G3/BV/E1-A stage.**

**Single next instruction:** Submit this J1 CPU-only SPEC DRAFT to an **independent source-grounded document reviewer**. Check that the observed-vs-oracle split is implementably strict, every fixture has a non-circular assertion and expected verdict, and the four limited PASS controls cannot inflate native B0 security. Record source-grounded disagreement/corrections and a new checkpoint. **Do not implement, freeze or execute without subsequent separate owner authorization.**
