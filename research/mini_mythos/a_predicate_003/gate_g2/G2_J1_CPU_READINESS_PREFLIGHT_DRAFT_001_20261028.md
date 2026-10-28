# OpenMythos E1-A G2 J1 — CPU-readiness / independent fixture-and-Oracle preflight DRAFT 001

**Stage:** `F3B-D1-A-CPU-003-E1A-G2-J1-CPU-READINESS-PREFLIGHT-001` · 2026-10-28 · **Author:** ChatGPT · **Work mode: DOCUMENTATION ONLY**.  
**Verdict of THIS document stage:** `PREFLIGHT DESIGN PREPARED`, not actual CPU readiness. **NO TEST RUN / NO PYTHON / NO CODE EDIT / NO FIXTURE BYTES OR HASHES / NO CRITERIA FREEZE / NO REAL**.  
**Reviewed source checkpoint:** `docs/F3B_D1_A_CPU_003_E1A_G2_J1_IMPL_CORRECTION_003_STATIC_REVIEW_001_CHECKPOINT_20261028.md`, Git Blob `61650f512aef2030d7afc2ab3d8cd8d85f934559`; review branch `d1-r3-a-cpu-003-e1a-g2-j1-fix3-static-review-20261028` @ `f51f77842c1eed88c2f7f9771b712cd969604321` (verified live before creating this document branch).  
**Latest independent static review:** `a_predicate_003/gate_g2/G2_J1_IMPL_CORRECTION_003_INDEPENDENT_STATIC_REVIEW_001.md`, Git Blob `6acf1bef20613a346d7a39282d455f16c6c8ed13`; **`J1-FIX2-REVIEW-F05 PASS (SCOPED SOURCE-STATIC)`**, not runtime PASS.  
**J1 source:** developer `d1-r3-a-cpu-003-e1a-g2-j1-impl-fix3-20261028` @ `38e8a9141ebd738a34628acc928adb28cd8c54cf`; `schema.py=551c4a01ed37f73c809776e123f98f6d055ac998`, `judge.py=8aef00cb1b66ee107c91086cd537c759858940cd`, `oracle.py=0df6e5da8e8d08b39f19ff4188f34d33a44a2282`, `codec.py=bb486c922b945dd30edb003a11fe7758bd13c2fb`, `tests/test_j1_static_and_unit.py=ab71b1dca8e90cc63f2763ed5391a492200f6dc8`.  
**Normative INPUT for inventory only:** `a_predicate_003/gate_g2/G2_J1_CPU_ONLY_FIXTURE_PREREG_DRAFT_V0_1_20261028.md`, Git Blob `9574f90687b632f35c419a14963437c49dd35f58`; **V0.1 remains a DRAFT, not a frozen specification.**  
**Frozen Bench reference:** `observer.py=635e73b34203219a3687f86332d0e82362b89670`; `registry.py=3f2179e132371dd323f865be8a4d41fa5e58786d`. This document never calls or alters those native processes.

## 1. Exact research question and proof ceiling

**Future possible J1 question:** given *independently prepared, finite, hand-authored synthetic B0-shaped observable records* and **predeclared hypothetical source trust**, does J1 compute the **predeclared narrow subject verdict** for exactly the 18 V0.1 case identifiers, **without Lane O leakage or invalid-instrument false acceptance**?

A later **CPU execution** may establish only that synthetic detector outputs match independently pinned expected results under a recorded pure-Python environment, guard and evidence protocol. It **cannot** prove native B0 gate delivery, unique kernel child provenance, lawful reaping, timeout-safe cleanup, Parcae mathematics/gradients, recursive Transformer quality or Mythos efficiency. **`native_B0_safety_status=NOT_EVALUATED_BY_J1`** MUST survive every report, including a future run PASS.

**Status definitions (never interchange):**
- **Subject** `PASS / FAIL / BLOCKED`: a narrow *assertion about the supplied synthetic evidence*. A subject FAIL may be a successful detector test.
- **Instrument** `VALID / INPUT_INVALID / UNVERIFIED`: whether observation sources, schema, readback and boundaries satisfy their proposed contract. `INPUT_INVALID` is **not** an ordinary expected subject BLOCKED.
- **Individual formal test** `PASS / FAIL / BLOCKED / NOT_RUN`: what an **independent acceptance verifier** determines after verifying fixture S/O custody, guard/runner, full output and exact expected subject. **Currently ALL = NOT_RUN.**
- **Run** `PASS / FAIL / BLOCKED / NOT_RUN`: depends on all 18 required cases and attestation, not on J1's subject PASS counts or CLI exit codes. Treat missing/unverified case as BLOCKED; do not claim a RUN PASS unless exact approved full suite and independent evidence closure pass.
- **This stage:** `DESIGN ONLY`. Source-static-scoped PASS does not transitively become preflight PASS or CPU PASS.

## 2. Current code reality and the acceptance deadlock

`j1/oracle.py` has the **18 versioned expected tuples** in `SPEC_V0_1_INVENTORY`, with expected counts `PASS=5,FAIL=5,BLOCKED=8`. This is a *draft document inventory*, **not independent proof** that any specific S input or sealed truth O exists. `grade_case` exposes `inline_check_verdict` for **NON_FORMAL_DEMONSTRATION** only; `test_acceptance_verdict` is **unconditionally BLOCKED**, and `aggregate` **unconditionally returns BLOCKED/NOT_READY**. `verify_fixture_attestation` is an intentionally rejecting stub. `FORMAL_ACCEPTANCE_READY=False` and `NOT_READY_REASONS` explicitly include no sealed S/O, no verifier, no reviewed guard/runner, criteria not frozen and unauthenticated trust-map origin.

Therefore **no current function call can produce an authorized formal J1 CPU PASS**. The correct way forward is to **design and obtain explicit approval for the missing artifacts, develop them on a separate Claude Code code stage, independently audit and then separately authorize execution**—not switch `FORMAL_ACCEPTANCE_READY` to True, bypass the stub, trust caller-submitted rows, or call an inline check a formal PASS.

**Structural security assumption:** `schema.validate_trust_model` checks kind/role ceilings but **does not authenticate who authored the map**. A Python module boundary by itself also is not an independent custodian. Both limitations must remain visible in later preflight decisions.

## 3. Proposed full 18-case preflight matrix — S observations vs private O truth

The following are **DESIGN INTENTS**, not fixture files, exact canonical byte payloads or fresh results. `S` means **only subject-visible raw observations**, never expected labels. `O` means **independently authored private truth/expected labels and provenance**, joined only by an isolated runner/oracle after J1 output. Every fixture must later include exact intended source handles, source roles, read statuses, relevant ordinals, required lifecycle/sidecar preconditions and raw data versions. **Never pass the case ID in an S record or source-handle name**.

| Planned ID (O ONLY) | Assertion | Lane S draft observable / critical prerequisite | Private O expected subject | Instrument/test-design caveat |
|---|---|---|---|---|
| `J1-F01-A` | ATTRIBUTION | B0-shaped REGISTERED Q and *separately harness-declared hypothetical* same-gate child witness G, explicit matching trusted ticket/gate association | **FAIL** | Q≠G positive contradiction; distinguish native B0 absence of such witness |
| `J1-F01-B` | ATTRIBUTION | REGISTERED Q, no independent gate-child witness | **BLOCKED** | O may privately know G; subject must never see hidden truth |
| `J1-F01-C` | ATTRIBUTION | REGISTERED G and same-gate simulated witness G | **PASS** | Limited observational consistency, **not** kernel fork proof |
| `J1-F01-D` | ATTRIBUTION | REGISTERED Q, untrusted NODE_CLAIM_SIM alleges G, no authenticated simulated witness | **BLOCKED** | Role ceilings prevent self-declared witness authority |
| `J1-F02-A` | UNIQUE_REGISTRY | Complete-for-supplied-scope RUN_START/INTENT/REGISTERED ledger with nA,nB sharing (pid,starttime) | **FAIL** | Positive duplicate first; not disguised by boot_id/pidns |
| `J1-F02-B` | UNIQUE_REGISTRY | Finite internally sound lifecycle, distinct registered pairs; no orphan or malformed FORKED pid, complete READ_STATUS scope | **PASS** | No proof that an external native B0 log has no missing rows |
| `J1-F03-A` | PREVENT_PROOF | B0 REGISTERED then RELEASED intent, no trusted PRE_RELEASE preventing witness | **BLOCKED** | SMOKE_ONLY; release ledger precedes write; no prevention PASS |
| `J1-F03-B` | PREVENT_PROOF | As F03-A plus *post-release* untrusted READY | **BLOCKED** | SMOKE_ONLY; later READY cannot substitute missing pre-R observation |
| `J1-F04-A` | LAWFUL_REAP | Pinned Z, DEAD, ECHILD claim; no independently trusted lawful wait | **BLOCKED** | SMOKE_ONLY; distinguish ECHILD source, parent and observation time |
| `J1-F04-B` | ZOMBIE_AT_T | Single declared simulated snapshot for exact pid/starttime at specified ordinal T; state Z | **PASS** | Time-T state alone, not reaped; multiple T unresolved OQ-1 |
| `J1-F04-C` | ZOMBIE_AT_T | Same identity and T conditions but state S | **FAIL** | State contrast; no global process-lifetime claim |
| `J1-F05-A` | LOG_MATCHES_SEAL | Canonical finite sidecar log and *separately* trusted simulated manifest with positive seq/head/byte mismatch | **FAIL** | Seal must be internally valid and from O-controlled custody; mismatch ≠ forged event |
| `J1-F05-B` | LOG_MATCHES_SEAL | Canonical full log, terminated lines and independent manifest with exact byte length/seq/head/run match | **PASS** | Integrity of **bytes** only; no real independent B0 seal |
| `J1-F05-C` | EVIDENCE_USABLE | Mismatched log/manifest as F05-A, but asks downstream usability | **BLOCKED** | SMOKE_ONLY; distinct assertion from positive integrity FAIL |
| `J1-F06-A` | DELIVERY | B0 REGISTERED→RELEASED intent, no authenticated byte receipt | **BLOCKED** | SMOKE_ONLY; intent precedes `os.write` |
| `J1-F06-B` | WRITE_COMPLETE | REGISTERED/RELEASED and trusted hypothetical wrapper result bytes=1, errno=null | **PASS** | Only simulated write syscall completion, not reader identity |
| `J1-F06-C` | WRITE_COMPLETE | Same as B with bytes=0 or EPIPE under trusted simulated wrapper | **FAIL** | Positive non-completion contradiction; consistent wrapper schema needed |
| `J1-F06-D` | WRITE_COMPLETE | Untrusted node message claims successful R; no trusted wrapper outcome | **BLOCKED** | Source-trust contrast; untrusted claims do not make a syscall PASS |

**Inventory invariant:** exactly **18 unique IDs**, **5 expected subject PASS, 5 expected FAIL, 8 expected BLOCKED**; five discriminative assertion names `ATTRIBUTION,UNIQUE_REGISTRY,ZOMBIE_AT_T,LOG_MATCHES_SEAL,WRITE_COMPLETE`; four `SMOKE_ONLY` names `PREVENT_PROOF,LAWFUL_REAP,EVIDENCE_USABLE,DELIVERY`. No subject `NOT_RUN` is legitimate. Do not silently add, drop, rename or retarget IDs. The nine unselected arm-qualified cards `D01-P1,D02,D03a,D03b,D03e,D04,D06,D08,D10` stay **`DEFERRED_BY_SCOPE / NOT TESTED`**, not PASS. This proposed matrix does **not** claim all 18 exact S bytes or all O truth manifests have been specified or independently authored.

## 4. Future fixture production and immutable input provenance (PROPOSAL ONLY)

**Phase F0: owner/reviewer freeze decision** — A reviewer checks this draft vs V0.1, exact assertion definitions, source roles, optional fields, the OQ/SMOKE restrictions and the 18 approved IDs. An authorized owner must explicitly select whether to freeze the **specific schema, canonical byte contract, scope and handling of OQ-13**. **No freeze is granted by this document.**

**Phase F1: separate Claude Code implementation-only task** — After explicit approval, Claude Code may implement: (i) a deterministic **offline fixture writer** whose output is **not generated in the implementation-only stage**, (ii) strict S/O schema validators and canonical serializers, (iii) a **separate, non-J1 truth-verifier interface**, (iv) a static isolated runner/guard source. Any code stage needs a new branch, independent static review and checkpoint. It must not import Bench or spawn gate-related child processes as a side effect.

**Phase F2: explicit materialization authorization** — An authorized operator invokes the reviewed offline generator **only after independently reviewing its exact command, output destination, side effects and resource bound**. At this stage and not earlier, materialize exact S/O **separately stored byte artifacts**, independently review/read back complete files, compute actual SHA-256/digests, file sizes, canonical JSON schema version, declared source roles and an immutable **manifest**. Record real SHA values and provenance; NEVER invent them now. The truth O must originate from **independent authored assumptions or manually adjudicated scenario contracts**, not from running J1 and copying its predictions.

**Phase F3: external attestation** — A distinct reviewer/custodian (not the judge under test) checks **complete file readback**, S/O byte hashes, immutable 18-case ID list, expected status distribution, trusted source-handle role contract, sidecar chain and seal input. Distinguish plain SHA hashes (accidental integrity) from *authentic custody*, which requires a separately controlled publication or signing trust root. A digest written by the same untrusted process that controls a file is **not** independent authentication. Record a negative readback/corruption control.

**Phase F4: guarded CPU execution** — Only with an independently reviewed runner, explicit owner authorization and source+fixture seal frozen, execute under a **CPU-only no-native-process** sandbox. Validate inputs/attestation **before J1**; J1 sees only Lane S, oracle sees Lane O only after J1 result; collect both raw output and guard result. A forbidden import/process creation/network/real gate interaction immediately causes `FAIL` or `BLOCKED` according to a predeclared failure taxonomy; never report PASS if guard evidence is absent.

**Phase F5: independent acceptance and checkpoint** — An independently implemented acceptance verifier checks each J1 output against the pinned O truth **and** separately verified S/O custody and guard reports. Missing evidence → BLOCKED; actual mismatched verdict on valid, verified inputs → FAIL; no skippable cases, exactly 18 expected. A passing synthetic J1 fixture is **not** a native B0 or G2 safety pass. Archive Git head, OS/Python stdlib version, exact command/scope, seed (if applicable), time-independent observable order, input files/hashes, output files/hashes, expected vs actual, limits and next instruction. Grok review if unavailable remains DEFERRED rather than falsely PASS.

**No phase F1–F5 is authorized by this documentation turn**. F0 is a *future owner/reviewer decision*, not silently satisfied.

## 5. Lane firewall, roles, independent oracle and anti-cheating preflight

| Boundary / check | Required future evidence | Currently supported? |
|---|---|---|
| S → judge narrow input | API accepts only `assertion_id,subject_observables,declared_trust_model`; forbid IDs/truth/grades in **record fields, source handles, errors, file paths, closures and environment** | **SOURCE-STATIC PARTIAL**: schema and judge code exist; end-to-end runner isolation **NOT TESTED** |
| O private expected truth | Pin O as independent versioned records with `fixture_id,canonical_card,assertion_id,expected_subject_verdict,truth_model` and optional behavior label; independent authorship/custody | **NOT MATERIALIZED / NOT VERIFIED**; Python inventory tuples are not independent custody |
| Same-case join | Runner privately maps S digest ↔ O case ID, **after** J1 output; J1 cannot open O, import oracle, infer label from file naming or know case order | **NO RUNNER / NOT TESTED** |
| Trust grants | Harness predeclares opaque source handles/role ceilings; `synthetic_assumption=True`; mapping authenticated **outside** J1 if claiming trusted fixture origin | **NOT AUTHENTICATED**; source role table alone is not trust |
| Sidecar seal | Match/mismatch judged against independently retained manifest; canonical byte readback and chain validity before interpreting mismatch | **NO MATERIALIZED MANIFEST / NO TRUST ROOT** |
| Independent grade | Only acceptance verifier with independently attested S/O+guard may issue *formal* test PASS; guard absence / invalid input → test BLOCKED, never "matching subject BLOCKED" PASS | **BLOCKED BY CODE**: oracle stub refuses attestation; must not override without separate review |
| Aggregate full-suite | exactly 18 case IDs, no duplicates/unknowns/skips, no optional `expected_ids` shrink, formally reviewed fail-vs-block decision | **CODE SOURCE EXISTS BUT FORMAL NOT READY** |
| Robustness/metamorphic | future independent controls: rename node/gate tokens, irrelevant-record order, remove trusted witness, replace trusted with untrusted source | **SOURCE TEST SKELETONS ONLY / NOT RUN** |

**Never leak a fixture's target verdict by encoding it in the handle name or `assertion_id`-specific magic.** `assertion_id` is a legitimate question selector but a constant verdict per selector must fail the five discriminative families. Four SMOKE_ONLY families are *deliberately incapable of proving general correctness*; report that ceiling even if their selected cases later pass.

**Cross-source proof disclaimer:** F01-C can establish at most observed equality under an assumed simulated gate witness, F02-B finite internal uniqueness, F04-B one simulated Z at T, F05-B matching sealed bytes and F06-B one simulated write result. None establishes the real B0 properties those labels resemble.

## 6. CPU runner and guard design — threat model & non-goals (NO implementation now)

**Intended compute:** CPU-only deterministic stdlib Python; no network, GPU, model weights, dataset downloads, subprocesses, fork/exec, signals, janitor or Bench native runtime in the J1 **test payload**. The future runner itself must explicitly inventory its Python launch, permitted imports and file reads; **the earlier source-only no-Python rule is not a magical no-process CPU test**. Future authorization must name exact allowed commands, isolated working directory, resource limits and operating owner.

**Threats to test validity:** subject answer contamination, source-role self-promotion, altered expected O, forged 18 PASS rows, truncation/torn chain, malformed numeric booleans, missing file/stray fixture, handler exception, nondeterministic record ordering, hidden native import/side effects, test skipping, flaky order/seed, accidental overwrites. These threaten **scientific acceptance**, not only runtime security.

**Guard preflight design checklist (future approval):**
1. Use a disposable non-production workspace with read-only pinned source + read-only S/O inputs; separate write-only experiment output area. Never point at proprietary logs, personal data or networked services.
2. Read-only code and import graph inspection; verify `judge/schema/codec` do not invoke native Bench/Parcae, open arbitrary process endpoints or mutate protected files. Runner/harness is not assumed safe merely because J1 is pure.
3. Explicit CPU-only environment with pinned Python/OS/stdlib, process count and memory/time bounds, no GPU invocation, no external requests. An actual guard requires independent review and verification; **do not claim OS sandbox capability without evidence**.
4. Pure synthetic tests must not require `/proc` traversal, real `waitpid`, real signals, gate pipe, live child identity, actual reaper or D1/G2 process control. Any such need is **OUT OF SCOPE**, BLOCKED and escalated to the separate REAL program.
5. Capture *actual* exit code, stderr/traceback, file hashes, absence-of-side-effect guard result, raw case results and time/order metadata. Exit code 0 alone is **NOT PASS**. Exceptions are not silently mapped to expected subject BLOCKED.
6. Future independent verifier checks full 18-ID inventory, separate S/O custody, readback, allowed stdout/stderr, tests executed count, selection/smoke limitations, and no unreviewed post-run edits.

**Safety note:** The CPU-pure J1 detector is not equivalent to native G2 process-management verification. Even a clean CPU test cannot release the **G2 REAL BLOCKED** state without lawful creator-owned reap / crash-orphan / no-signal bounded-cleanup resolution and independently preapproved disposable Linux containment.

## 7. Unresolved decisions — do not "solve" by silently changing source

| Ref | Present fact | Proposed handling in future preflight | Now |
|---|---|---|---|
| `OQ-13` FORKED.pid vs REGISTERED.pid | Frozen `registry.integrity_issues` checks fork PID type, **not** equality with REGISTERED PID; current J1 does not compare them | **Retain legacy V0.1 source-scope behavior for these 18**; note no equality claim. A stronger same-node relation must be a **separately versioned assertion/change** approved by owner after source review. Include a supplementary *unscored* thought-control in a future design review, never silently alter F02-B | **OWNER UNDECIDED / NO CODE** |
| `OQ-11` synthetic gate/ticket | `gate_token` is asserted by hypothetical witness/REGISTERED; not externally authenticated | Specify an independent source-binding/custody contract before any formal "trusted" label; absent authority ⇒ `BLOCKED / NOT_READY` | **UNRESOLVED** |
| `OQ-12` formal acceptance | Seal, verifier, guard, runner and frozen criterion absent | Keep `FORMAL_ACCEPTANCE_READY=False` and formal `BLOCKED` until a separately approved trusted verifier and guard are implemented/audited | **BLOCKED / NOT_READY** |
| `OQ-1` snapshot time T | Multiple snapshot selection undefined | Either exactly one snapshot per relevant fixture or separately specify a T selection rule before freeze | **UNDECIDED** |
| `OQ-2` pre-R attribution | Current attribution retrospective | No pre-R prevention claim; don't silently upgrade retrospective PASS to prevention PASS | **LIMITED** |
| `OQ-3/OQ-7` sidecar, raw fields | Proposed codec/normalized schemas are not frozen | Pin exact schema, canonicalization and digest/complete-read before materialization | **NOT FROZEN** |
| `OQ-4/OQ-8/OQ-9` registry/order/identity | Finite synthetic ordinals and conditional identity metadata assumptions | Publish exact table of required fields and allowed event kinds per selected fixture, avoid native B0 equivalence | **DRAFT** |
| `OQ-5` smoke-only | Four assertions have no contrasting PASS by design | Maintain `SMOKE_ONLY`; no generalized accuracy/security claim | **LIMITED** |
| `OQ-6/OQ-10` write/role trust | Wrapper schema and harness authentication not frozen | Pin byte/errno shape and independently assigned role manifest before execution | **DRAFT** |
| `G2 O-1…O-15` REAL safety | Lawful reaper/abnormal cleanup/operational containment not decided | Do **not** use J1 to answer or sidestep REAL questions | **OWNER UNDECIDED** |
| Grok cross-review | No new actual reviewed report in project evidence for this stage | Record independently if later supplied; disagreements to minimal authorized experiment | **DEFERRED / NOT PASS** |

## 8. Readiness acceptance gates and present states — no false green

**Each gate is independently assessed against explicit evidence, not a task-completion command.** `PASS` here may refer only to the noted document/static-source fact; it **cannot** mean a CPU experiment passed.

| Gate | Expected evidence / acceptance criterion | Actual as of this document | Status |
|---|---|---|---|
| `PF-00` pinned checkpoint/code | Actual verified source branch HEAD and frozen blobs | Verified latest independent source-static review HEAD and file blobs | **PASS (PROVENANCE)** |
| `PF-01` 18-case scope and claims | Exact 18 IDs, 5/5/8 expected, 5 discriminative + 4 SMOKE, nine deferred | V0.1 matrix + current Oracle inventory exist as **draft**, no fixture bytes | **PASS (DESIGN INVENTORY ONLY)** |
| `PF-02` exact S/O schemas and canonical byte contract | Versioned byte-level field contract, complete-event ledger, no identifier leak, signed-off normalized input mapping | Draft descriptions only; schema/codec source unexecuted; some OQs remain | **BLOCKED / NOT FROZEN** |
| `PF-03` independent truth and custody | Authoritative O authored independently of J1, source binding, actual sealed S/O readbacks and stable digests | No S/O files, signatures, custodial proof or real hashes | **BLOCKED / NOT MATERIALIZED** |
| `PF-04` trust origin / external seal | A reviewed trust-root/provenance scheme independent of subject/runner-controlled records | Current map unauthenticated; seal is hypothetical | **BLOCKED** |
| `PF-05` runner isolation and CPU guard | Reviewed no-native-process runner, bounded CPU workspace, import/side-effect guard, exact command/policy | No reviewed runnable guard or runner | **BLOCKED / NOT IMPLEMENTED** |
| `PF-06` formal independent verifier | Accept only verified sealed S/O, guard and exact expected values; cannot accept fabricated grade rows | `verify_fixture_attestation` always rejects, formal acceptance BLOCKED | **BLOCKED / NOT IMPLEMENTED** |
| `PF-07` source functionality smoke and regression | Separately authorized CPU syntax/import+unit check, results, negative controls, reproducibility | Only static source tests exist; **none executed** | **NOT TESTED / NOT AUTHORIZED** |
| `PF-08` explicit freeze & execution permission | Owner-reviewed scope, schema, trust/guard contract, independent review status, exact run permission | V0.1 draft, OQ-13 + trust decisions open, Grok deferred | **BLOCKED / NOT AUTHORIZED** |
| `PF-09` full formal run + archived evidence | Real 18/18 input validity, verified O and guard, expected vs actual, no skip, full checkpoint | No actual run/output/artifacts | **NOT TESTED / NOT AUTHORIZED** |
| `PF-REAL` G2 real process safety | Separate real creator-owned reap, orphan/crash, zero-signal safe containment | Unresolved O decisions, separate REAL safety blocked | **BLOCKED / OUT OF J1 SCOPE** |

**Overall readiness verdict: `CPU FORMAL ACCEPTANCE NOT_READY / BLOCKED`.** `PF-00` and `PF-01` refer ONLY to source/document provenance; they do **not** turn any subsequent gate green. Four smoke-only assertions are non-discriminative, regardless of hypothetical fixture test count.

## 9. Sequence of future permissions and stage-checkpoints (NOT granted now)

1. **This document's independent design review:** reviewer checks source fidelity, 18 ID/count invariants, no fake attestation, OQ-13 disposition and gate states. Record `PASS/CHANGES REQUIRED/BLOCKED` **for the document only**.
2. **Owner separately decides PF-02/03/04/08 design assumptions** or records explicit deferred constraints; freeze only a specific selected scope after cross-review decisions are documented. If Grok unavailable, treat its review as DEFERRED and never fabricate consensus.
3. **Owner separately instructs Claude Code implementation-only** for pure fixture generator, oracle verifier, runner/guard source and regression source with no execution, on a new branch; ChatGPT independently static-reviews actual diff and updates checkpoint.
4. **Owner separately authorizes fixture materialization** with exact offline command, output layout, evidence preservation, data classification and custody; independently verify real hashes and complete readbacks. Materialization is not equivalent to running J1.
5. **Owner separately authorizes bounded CPU correctness tests** after guard proof/readiness gates are satisfied; define environment, actual inputs, expected/actual, status for each assertion and run, multiple-seed controls only where randomness exists. Preserve failure and discrepancy; do not auto-patch architecture.
6. **No J1 gate can auto-authorize G2 REAL**. G2 REAL needs separate proof of lawful reaping, orphan/abnormal cleanup without signals and explicit external operational owner/containment plan.

**Only next instruction:** submit this **DOCUMENT-ONLY preflight draft** for independent source-grounded design review, save that review and a new checkpoint; do not generate S/O, implement code, freeze, run CPU, or proceed to REAL. User must explicitly authorize subsequent stages. This preflight draft is not a Claude Code task and does not delegate work to an agent in the background.
