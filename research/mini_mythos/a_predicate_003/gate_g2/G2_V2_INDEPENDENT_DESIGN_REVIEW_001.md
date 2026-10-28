# G2 V2 independent design review 001 — 2026-10-28

**Reviewer:** ChatGPT (independent GitHub source read-only review; no CPU/process execution)  
**Object:** `research/mini_mythos/a_predicate_003/gate_g2/G2_IDENTITY_DESCENDANTS_DESIGN_V2.md` at `6c223ef2efa8830c1552d44e046b72063d87a637` (blob `e58fe0e0881beebcef2f3d8b0510b7e4175da1da`).  
**Frozen code:** `bench/` at the same pinned tree, previously independently compared with `450914367c247231c51be02e13775cb001e69c5d` (unchanged).  
**Review status:** **G2 V2 DESIGN CHANGES REQUIRED**. The V2 document is readable and the corrections of V1-R1…R5 are substantial. It is **not BLOCKED to review**; however the **G2 criteria freeze, implementation, CPU tests and REAL are NOT AUTHORIZED**. In particular the first REAL remains **design-blocked** by lawful reaping and no-signal liability.

**Grok:** User reports usage limits and temporarily permits ChatGPT-led **documentation progress only**. `GROK G2 DESIGN REVIEW = DEFERRED / NOT PERFORMED / NOT PASS`. No proxy reviewer result or bilateral acceptance is manufactured. User-owner choices are explicitly separate from reviewer recommendations.

## 1. What V2 got right (document-level observation, not runtime PASS)

1. The frozen B0 Observer, hypothetical P1 isolated intervention and proposed J1 pure judge are explicitly separated (V2 lines 13–19).
2. PID/starttime, PPID, time-indexed SID/PGID, gate inode/fdinfo and trust-boundary categories are distinguished. `pipe:[inode]` does not prove unique gate reader or adversarial lineage; READY/FIRST_ACTION are post-release socket claims.
3. The evidence terminology `REAP_CLAIMED`, `REAP_CORROBORATED` and `REAP_INSTRUMENTED` replaces unqualified inferred reap, and Z/DEAD/ECHILD/pidfd are explicitly insufficient (V2 lines 36–52).
4. A test's expected/actual *subject* verdict is separated from the *test acceptance* verdict; subject BLOCKED can be the correct result of a passing CPU fixture (V2 lines 68–80).
5. Fourteen unique scenario IDs are explicit, and the CPU/REAL scopes do not imply permission to run hostile LIVE stimuli (V2 lines 80–107).
6. No longer asserts a 60-second total recovery guarantee for a frozen child that can live 120 seconds; manual disposition is a BLOCKED responsibility, **not** cleanup proof.
7. A byte-identical archived V1, Grok deferral provenance, checkpoint and document-only diff are present in the parent tree.

## 2. Remaining findings — minimal counterexamples and corrections

### V2-F01 HIGH — D01 blends B0 with P1 yet requires a PRE_RELEASE evidence link that B0 cannot acquire through its own path

**Code:** `bench/observer.py:103–126` `_register(...,hold_release=False)`; `observer.py:276–302` `_on_created` calls `_register(child,pid,creator.pid)` **without hold_release**; `observer.py:128–139` immediately writes RELEASED intent and then gate `R`.  
**Design:** V2 §1 lines 13–19; §2 release cutoff; 14-card table line 86 requires D01 attribution with PRE_RELEASE links, lists `B0/P1 separate`; §7 says D01 is first possible REAL.

**Counterexample:** Honest creator invokes B0 ticket path. The stock observer records the PID and calls `release` synchronously before any G2 sidecar external gate-read-hold sample can be guaranteed. A post-release fd check normally finds no gate read descriptor because `bench/gate.py:77` closes it. A judge treating B0 D01 as a preventive PRE_RELEASE PASS would certify a fact it did not observe.

**Required:** Separate **D01-B0** (only baseline behavior/detective observations; PRE_RELEASE gate witness not required; *no prevention claim*) from **D01-P1** (a distinctly versioned/authorized G2 driver that explicitly holds release and obtains PRE_RELEASE observation before release). If D01 requires prevention, B0 must be **INELIGIBLE/BLOCKED**, not PASS. P1 pipe evidence still cannot prove malicious-creator-resistant identity. Fix the exact SUT/expected result/permission for the first REAL and every relevant CPU fixture **before criteria freeze**.

### V2-F02 HIGH — REAP_INSTRUMENTED still has an undefined trust boundary

**Code:** `bench/node.py:45–74` has no wait by the creator; `observer.py:377–394` waits only on observer-owned children; `common.py:238–241` counts zombie as dead.  
**Design:** V2 §3–4 (REAP_INSTRUMENTED, plan A, plan B), §7 healthy flow.

**Counterexample:** The proposed G2 creator emits a plausible `WAIT_REPORT` and the observer sees Z then /proc disappearance, but the actual wait is performed by a different thread / unexpected wait call, or the creator is reparented or uses `SIGCHLD` ignoring / `SA_NOCLDWAIT`. The report and time ordering alone do not establish *which syscall* legally reaped. A creator-side Python wrapper improves traceability **only under a trusted single-reaper/call-path assumption**, not unforgeable kernel attestation.

**Required:** Freeze *what is claimed*, not merely a nicer label. For scoped plan A, either (a) require explicit trusted creator-side wrapper + call/return/status/errno + observer Z and PROC_GONE + scoped assumptions of no other reaper and normal SIGCHLD behavior, and report `REAP_INSTRUMENTED_WITH_KERNEL_CORROBORATION`, OR (b) accept `REAP_CORROBORATED` with an appropriately weaker claim; in either case require owner approval of evidence tier. `REAP_CONFIRMED` without qualifications is prohibited. If neither tier meets the stated research question, D07 REAL is **BLOCKED**. S0 source cannot prove an unimplemented wrapper.

### V2-F03 HIGH — Signalless abnormal termination has no closed operational containment plan

**Code:** `bench/common.py:24` `T_NODE_MAX=120`; `bench/node.py:61–74` uses `os._exit` on after-READY / EXIT / EOF / the 120-second self-cap; `bench/observer.py:338–375,456–533` and `bench/janitor.py:44–72,224–245` have SIGKILL-capable cleanup paths, intentionally excluded in G2 V2.  
**Design:** V2 §7, nominal <=60 s vs anomaly >=120 s, no janitor, no signals, manual disposition.

**Minimal blocker:** Creator dies unexpectedly before `waitpid` on its zombie descendant. The observer is not a subreaper and cannot legally wait for the now-orphaned process. An unknown inherited control socket holder can also prevent EOF. Even after a 120-second self-cap, there is no guarantee of a lawful reap or bounded zero-residue confirmation. `MANUAL_DISPOSITION_REQUIRED.json` is only a stop and disclosure document.

**Required:** Before any REAL authorization, explicitly define **containment** (a private disposable execution environment with no third-party workload, preflight and a separately owner-controlled host-level disposition), lawful reaper table, per-node cooperative normal-exit plan, anomaly deadlines and external responsibility if a process survives. A host/VM teardown or external signal would be an **independent manual recovery action**, not a G2 zero-signal PASS; it requires separate governance and evidence. If that containment is unavailable, do **not** run a descendant REAL. Never silently auto-kill on experiment failure.

### V2-F04 MEDIUM — Sidecar chain durability and provenance are not yet testably closed

**Design:** V2 §5 proposes append-only canonical JSON/prev_sha256, separate sealed head and readback, but no closed schema for genesis hash, canonical bytes, atomicity boundaries, max record, partial write, filesystem crash, signed or independently trusted external head, or competing writers.

**Counterexample:** A writer drops the final valid record(s) and recomputes a self-contained chain and its closeout (or faithfully writes a false WAIT_REPORT); internally valid hashes do not establish a complete event history or sender authenticity.

**Required:** Define a separately trusted seal provenance and failure policy, exact record format, sequence/gap and torn-tail checks, byte length, permissions, fsync and readback, and how missing / unknown events become BLOCKED. Do not claim a hash-chain proves kernel provenance. **Pure CPU fixture proposals only** for tampering/truncation, not an executed experiment.

### V2-F05 MEDIUM — Two-level verdicts are fixed conceptually, but D01/B0 expected acceptance, and card-by-card exact outcomes, are still open

**Design:** V2 §6 enumerates 14 IDs and the three verdict fields. However `ACCEPTED_UNSAFE` is a *diagnostic classification*, while subject outcomes otherwise are PASS/FAIL/BLOCKED; fixture schema must distinguish `observed_behavior_label` from `actual_subject_verdict`, especially when running a frozen B0 defect replay. D01-B0 vs D01-P1 differs materially in PREVENT/DETECT evidence and must have unique IDs/fixtures.

**Required:** Freeze a CPU-only expected table with exact fixture IDs, immutable independent truth, SUT arm, expected behavior label (optional), expected subject verdict, and expected test acceptance verdict; ambiguity about FAIL versus BLOCKED must be resolved using positive witness / missing evidence, never chosen after seeing results. Test-level PASS of a reproduced B0 bug must not be called system safety PASS.

### V2-F06 LOW — Stage authority can be read too broadly

**Design:** V2 §9 says S1 criteria freeze after open choices are scoped/decided and separate owner approval. Because O-1…O-15 recommendations are offered in a table, future agents might incorrectly treat them as accepted.

**Required:** In the next decision record, columns `reviewer_recommendation`, `owner_decision`, `blocking_status`, and `evidence_ref`; all `owner_decision = UNDECIDED` until explicit owner action. A missing Grok review remains `DEFERRED`, not PASS; the owner's temporary workflow exception is document-only.

## 3. Provisional decision matrix — proposals only, no actual O item approved

| Item | ChatGPT technical proposal (NOT owner approval) | Blocking condition |
|---|---|---|
| O-1 | Prefer **plan A**, creator is lawful descendant wait owner; B subreaper deferred | REAL blocker |
| O-2 | B0 baseline diagnostic and P1 held-release driver **separate**; no adversarial preventive PASS | Criteria/REAL blocker |
| O-3 | Explicit `REAP_INSTRUMENTED_WITH_KERNEL_CORROBORATION` under trusted creator and witness assumptions; weaker `REAP_CORROBORATED` separately labeled | REAL blocker |
| O-4 | G2-only claim tap; disclose whether subclass changes the tested path | Before implementation |
| O-5 | fd+fdinfo positive observation only; no exclusive gate-holder claim | Prevention blocker |
| O-6 | Allow only scoped `NOT_OBSERVED_UNDER_REGIME`; required negative safety property unprovable => BLOCKED | Criteria blocker |
| O-7 | Closed sidecar schema and external seal trust source | Criteria blocker |
| O-8 | 2 forks maximum per card, at most 2 live nodes; time budgets require review | REAL blocker |
| O-9 | Each REAL case gets separate owner authorization, first D01 only if prior gates clear | Before REAL |
| O-10 | No intentional orphans in first REAL; accidental orphan => BLOCKED/manual | REAL blocker |
| O-11 | No Bench credential change; claims stay claims; scope excludes adversarial sender authentication | Before freeze |
| O-12 | Honest creator through G2 entry + frozen `node.request_spawn` for descendant | Before implementation |
| O-13 | Distinguish normal clock and anomaly containment; 120 s child cap does not guarantee reap | REAL blocker |
| O-14 | Shared gate FD adversary is CPU fixture only | Test scope |
| O-15 | No evidence transfer from B subreaper to E1-A frozen baseline | Scope if B considered |

## 4. Minimal *not executed* CPU-only discriminating fixture proposals

1. **CPU-A (B0/P1 cutoff):** frozen B0 `_on_created` invokes `_register` with default immediate release; supply timestamped synthetic states with a gate witness only *after* R. Expect B0 `pre_release_witness=UNAVAILABLE` and no PREVENT PASS. For a hypothetical P1 override with hold, pre-release witness can be observed, but not unique lineage guaranteed.
2. **CPU-B (reap levels):** identical independent kernel observations (Z, parent ppid, then gone), but different purported wait reports / instrumentation status. Correct judge returns REAP_CLAIMED, REAP_CORROBORATED or REAP_INSTRUMENTED only to the predeclared evidence tier, never inferred kernel certification.
3. **CPU-C (reap zombie / ECHILD):** ledger DEAD, Z and wait `ECHILD` without trusted wait invocation -> subject BLOCKED (reap); CPU test PASS if matching expected.
4. **CPU-D (sidecar prefix deletion):** a hash chain internally consistent but missing the expected externally sealed tail -> subject BLOCKED, CPU test PASS if detected.
5. **CPU-E (abnormal exit):** creator death before child wait + unknown socket holder + orphan; subject BLOCKED and manual responsibility, never zero-residue success.

These fixtures are **designs only**. No implementation, test runner, fork, wait, signal or authorization file exists or has been run in this review.

## 5. Acceptance, unresolved issues and next action

| Dimension | Status |
|---|---|
| Git/source audit (read-only) | PASS, pinned source references and reviewed V2 scope match |
| V1-R1…R5 conceptual corrections | ACCEPTED AS DOCUMENT IMPROVEMENT |
| G2 V2 design for freezing/implementation | **CHANGES REQUIRED** |
| G2 REAL safety prerequisites | **BLOCKED / NOT AUTHORIZED** |
| G2 criteria | NOT FROZEN |
| G2 code / CPU / REAL | NOT TESTED / NOT AUTHORIZED |
| Grok G2 review | DEFERRED / NOT PERFORMED |
| G1 REAL | Historical cross-review PASS, unchanged |

**Single next instruction:** prepare a **minimal V2.1 document-only delta** addressing F01–F06 without changing Bench or source architecture. The most effective reduction is to choose the first G2 research question (B0 purely detective vs P1 intervention), precise wait trust tier and explicit no-signal human-responsibility boundary; if these remain genuinely undecidable, leave them OPEN and do **not** promote the design. Return the V2.1 delta for ChatGPT source review; request owner approval separately before any freeze/implementation/CPU/REAL. Grok may review later; register differences rather than rewriting history.
