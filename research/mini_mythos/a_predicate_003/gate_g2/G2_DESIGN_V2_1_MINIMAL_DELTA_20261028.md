# E1-A G2 — V2.1 minimal design delta (DOCUMENT ONLY, NOT FROZEN)

**Task:** F3B-D1-A-CPU-003-E1A-G2-DESIGN-REVISION-003  
**Review input:** V2 independent review V2-F01…V2-F06 at Git commit cf9a77b22af4487452e1ecf5add6fb284b0aa69e  
**Frozen Bench audit source:** bench/ at cf9a77b22af4487452e1ecf5add6fb284b0aa69e; no patching or code mutation.  
**Status:** V2.1 DESIGN DELTA PREPARED / INDEPENDENT V2.1 REVIEW PENDING. G2 CRITERIA NOT FROZEN; IMPLEMENTATION, CPU, REAL NOT TESTED / NOT AUTHORIZED.  
**Reviewer availability:** Grok review DEFERRED / NOT PERFORMED due to reported usage limit. Owner's temporary permission covers document work, **not** fabricated Grok PASS or technical authorization.  
**Scope precedence:** Read alongside the historical V2 draft. Wherever V2 §1–§9 conflicts with the following narrower definitions, this V2.1 delta is the **proposal for review only**; neither version is an approved frozen G2 protocol. Original G1 REAL evidence remains untouched.

## A. Minimum research question — V2-F01; separate B0 from P1

**First proposed CPU-only research target:** Determine whether a pure judge **J1** can classify recorded *frozen B0* defects and uncertainty from synthetic, independently authored truth, with no false safety PASS. This is **detection**, not prevention, and is not a claim about original Parcae or the Mythos model.

**B0 — unchanged frozen Observer:**
- Source: bench/observer.py::_on_created passes _register(child,pid,creator.pid), which defaults to hold_release=False; _register then immediately calls release().
- No guaranteed pre-R gate holder sample is available in B0. The native path's REGISTERED + RELEASED ledger entries, pid/starttime and PPID are **not** PRE_RELEASE gate proof or unique-fork proof.
- For a D01-B0 detection-only scenario, the output may identify a *trusted-creator scoped, retrospectively corroborated registration* if independent evidence exists. It **must not** claim a PREVENT PASS or authenticated gate-to-pid lineage. If a required proof is unavailable, subject BLOCKED; a correct BLOCKED can make the CPU test PASS.
- An adversarial same-PPID wrong-PID case is a known **B0 unsafe-acceptance behavior**. A CPU fixture reproducing it can have test acceptance PASS while **system safety is not PASS**.

**P1 — possible new isolated G2 driver (NOT IMPLEMENTED OR AUTHORIZED):**
- Would deliberately hold release via a separate audited code path, obtain pre-R time-ordered observations, decide whether to refuse, and only then release or abort.
- Pipe inode + fdinfo + PPID checks support observations, **not proof of unique gate recipient or protection against malicious creators**; two same-parent processes may each hold a reader descriptor.
- P1 results, if ever obtained, cannot be reported as unchanged B0 results. If adversarial-prevention is required, further independently reviewed kernel-backed identity/creation proof is mandatory; otherwise subject BLOCKED.
- **Split card identity:** D01-B0 (detection/retrospective, baseline) and D01-P1 (intervention/pre-release, distinct system). Never collapse them into one D01 PASS. Proposed stage sequencing: pure CPU fixtures first; no D01 REAL is authorized.

**Required future pre-registration per arm:** SUT source hash, intervention flag, actual release decision path, PRE_RELEASE cutoff (before earliest R write attempt), witness presence/absence, the accepted trust model, subject expected output, and forbidden claims.

## B. Lawful reaper evidence tier — V2-F02

**Design recommendation for first narrowly scoped future study: Plan A (creator-owned).** This is a reviewer recommendation, NOT an owner-approved choice. Keep Plan B (observer subreaper) as a distinct, separately reviewed experiment that changes the target kernel behavior.

| Level | What can be asserted | Mandatory available evidence | What it cannot assert |
|---|---|---|---|
| EXIT_OBSERVED | The pinned identity exited | pidfd readable and timestamped process identity | Wait or ownership |
| ZOMBIE_OBSERVED | This identity was un-reaped at observation T | /proc state Z, same starttime, parent at T | Who will reap |
| REAP_CLAIMED | Creator reports a specific-pid wait | Creator control-socket message, raw claimed status | That a wait actually occurred |
| REAP_CORROBORATED | Reap claim is consistent with independent kernel lifecycle observations | Prior Z with rightful live parent, claim, later /proc gone; SIGCHLD/no-auto-reap and known waiter assumptions documented | Independent observation of actual wait syscall or globally unique reaper |
| REAP_INSTRUMENTED_WITH_KERNEL_CORROBORATION | A **trusted G2-owned creator wait wrapper** logs exact call and return, corroborated by separate kernel observations | Predeclared wrapper source/identity, no alternate waiters in trusted process, call pid, wait return pid/status/errno, monotonic interval, Z/parent before, /proc gone after; dispositions checked | Unforgeable kernel audit or proof of unknown outsider behavior |

**No unqualified REAP_CONFIRMED** under plan A. The trusted call-wrapper assumption must be explicitly approved or treated as an epistemic limitation. A creator WAIT_REPORT alone cannot be upgraded. In the observer's own direct child, its own specific-pid wait is a separate first-hand observation, not a proof of someone else's wait. ECHILD, DEAD, pidfd-readable and PROC_GONE in isolation never establish reaping.

**Blockers before any REAL:** Decide O-1 lawful owner and O-3 accepted evidence tier, specify SigIgn/SA_NOCLDWAIT, no competing waiters/threads, and prove that creator remains alive until it has completed its own reaping duty. If any required witness is missing or another waiter is possible, classify **subject BLOCKED** rather than asserting a stronger tier.

## C. Real-process containment and no-signal stop — V2-F03

**Design condition, NOT an environment already obtained:** A private, disposable Linux execution environment that runs no unrelated workload, has a pre-authorized *external* operational owner, records pid namespace/boot id, includes a reliable preflight and separately approved manual-disposition capability. No experiment should start until the environment and authority to handle failed residue are demonstrated.

| Phase | Proposed responsibility | Forbidden shortcut |
|---|---|---|
| Normal creator/descendant | Creator stays alive as the child's lawful waiter; descendant self-exits after READY (preferred for a first study); observer performs exact-pid wait only on the direct creator | Signal, kill by name, janitor, wait on a non-child |
| Normal time budget | Define separate per-gate, per-registration, wait and creator-exit clocks; 60 s is a **target for nominal flow**, not cleanup guarantee | Convert a deadline or ECHILD into cleanup PASS |
| Anomalous late exit | Frozen node_main may wait up to T_NODE_MAX=120 seconds; allow an independently budgeted settlement observation horizon, with lawful reaper still alive when possible | Assume socket EOF despite unknown fd copies |
| Crash/orphan/unknown FD | Stop new fork and unsafe R, preserve kernel identities and evidence, write MANUAL_DISPOSITION_REQUIRED, return BLOCKED, require human/OS external owner to decide separately | Auto SIGKILL, automatic retry or false zero-residue closure |
| Host-level disposition | A later OS/VM intervention is a **separate, separately authorized operational action** with its own record; even if it recovers the VM, the affected G2 REAL remains BLOCKED | Reclassify G2 zero-signal PASS after outside teardown |

**Safety blocker remains:** A no-signal protocol cannot guarantee deterministic recovery if the creator dies before wait or an inherited socket holder prevents EOF. Merely operating in a disposable VM does not change that logical fact; it bounds external harm if independent handling exists. If no such approved containment is available, **G2 descendant REAL must not run**. G2 V2.1 does not claim G2 REAL is safe or ready.

## D. Evidence sidecar sketch, complete enough for review but not a frozen schema — V2-F04

Proposed file: g2_sidecar.jsonl. Scope: integrity of what the G2 witness **reported**, **not** kernel authenticity or absence of unreported events.

**Candidate canonical record envelope:**
- schema_version = g2-sidecar-draft-1; run_id; monotonically increasing seq starting at 1; prev_digest (32-byte SHA-256 hexadecimal, genesis is 64 zero hex characters); source_role; event_kind; CLOCK_MONOTONIC sample (decimal string in a predeclared format, to avoid float encoding ambiguity); node_id; optional kernel identity; payload; event_digest.
- Canonical bytes for hashing: UTF-8 JSON with sorted keys, compact separators and no NaN/Inf, event_digest omitted from the hashed object, normalized Unicode/encoding policy documented; final JSONL line is complete and newline-terminated. One writer process, exclusive create with restrictive permissions (0600), append-only under exclusive lock; size and record limits predeclared.
- event_digest = SHA-256 of those canonical bytes. Next record prev_digest must equal the prior event_digest. Record-level hashes must be recomputed from **actual bytes** after file reread; chain alone cannot detect a removed consistent suffix.
- Explicit closeout manifest outside the sidecar: expected run_id, independently retained final seq, last event_digest, full file SHA-256 and byte length, source SHA and times. The trust source responsible for preserving/managing this manifest **must be separately named and independently checked**; if witness can rewrite both log and seal, hash match is not authenticity. A digital signature is optional only if a real, authorized independent signer and key custody are defined.
- Open/flush/close fsync policy, atomic manifest publication and directory fsync are **draft requirements**, not a promise of power-loss resistance; scope initial acceptance to ordinary-process-crash durability. Read errors, sequence gaps, truncated final line, bad canonicalization, invalid digest, missing independent final seal, inconsistent lengths, multiple writers or unknown trust source => subject BLOCKED.
- An event is only what its declared **source_role** can attest (e.g. WAIT_REPORT is a creator claim; /proc observation is witness read); no hash transforms it into a trustworthy sender ID or independently audited kernel syscall.

**Synthetic, not-run discriminators:** (i) internally valid log with suffix removed but independent final seal unchanged => subject BLOCKED; (ii) creator-forged wait event with valid chain => provenance still only CLAIMED; (iii) interrupted last line => BLOCKED. No tampering experiment executed.

## E. Exact scenario and verdict separation — V2-F05

**Historical 14 canonical card IDs stay intact:** G2-D01, D02, D03a, D03b, D03c, D03d, D03e, D04, D05, D06, D07, D08, D09, D10. The **arm-qualified candidate inventory has 15 entries** when D01 is split into D01-B0 and D01-P1 (not 14). This is a proposed inventory; no frozen count is claimed. D01-P1 must be NOT_RUN/NOT_AUTHORIZED until a separate intervention implementation approval exists. All CPU and REAL permissions are still absent.

Every immutable CPU fixture specification must have:
- fixture_id, case_id, arm (B0 / P1 / J1 / GUARD), scope (synthetic only), source SHA, immutable independent fixture-truth hash, controlled input, expected observations, expected_subject_verdict (PASS/FAIL/BLOCKED only), expected_observed_behavior_label (optional), expected_test_acceptance_verdict (normally PASS for a correct behavior), and intended evidence requirements;
- after execution (future only): actual_subject_verdict, actual_observed_behavior_label, test_acceptance_verdict (PASS / FAIL / BLOCKED / NOT_RUN), observed evidence references and acceptance delta. **No actual outcomes may be inserted in advance.**
- SUT unknown/ambiguous evidence must not be scored post hoc: if an expected subject verdict cannot be predeclared from independent fixture truth, the **fixture design is NOT_READY**, not an experiment.

| Proposed fixture | Predeclared independent truth | Expected subject verdict | Expected behavior label | Expected *CPU test* if correct |
|---|---|---|---|---|
| D01-B0, baseline honest, no pre-R witness | Stock _on_created immediately releases and pre-release pipe evidence is not available | BLOCKED **for any PREVENT assertion**; retrospective DETECT outcome separately scoped | B0_RELEASE_WITHOUT_PRE_RELEASE_WITNESS | PASS if judge refuses PREVENT PASS |
| D01-P1, synthetic held release + observable pipe holder | Held state may be observed, but pipe observation does not guarantee unique fork | BLOCKED **for adversarial-uniqueness**; narrower corroboration is not adversarial PASS | P1_HELD_GATE_OBSERVED | PASS if judge limits proof |
| D03c, malicious same-parent wrong PID | Frozen B0 misregisters Q while G is actual gate child | FAIL (positively observed wrong attribution) | B0_ACCEPTED_UNSAFE | PASS **for defect reproduction only** |
| D05, torn or unreadable registry | Required integrity evidence missing | BLOCKED | REGISTRY_INVALID | PASS |
| D07, Z plus ledger DEAD but no lawful wait | No reaping proof despite zombie and DEAD | BLOCKED | ZOMBIE_NOT_REAPED | PASS |
| D09, RELEASED intent without proven R delivery | No delivery proof | BLOCKED | DELIVERY_UNCONFIRMED | PASS |

This table does not change the 14 canonical IDs, and its six examples do not pretend that all cards have complete fixture inputs. Before freezing, enumerate each required arm/fixture and exact expected result **once**, with no unknown IDs/skips; positive protocol violation -> subject FAIL, incomplete proof -> subject BLOCKED. A CPU test PASS for the expected B0 defect **never** means native B0 safety PASS or G2 REAL PASS.

## F. Owner decisions and conflict policy — V2-F06

**All O-1…O-15 owner decisions remain UNDECIDED.** Suggested reviewer directions are not approvals; a separate explicit owner action is needed to freeze any decision or criteria. Evidence references below are to V2 and the V2 independent review, not experimental proof.

| Item | reviewer_recommendation (provisional) | owner_decision | blocking_status | evidence_ref |
|---|---|---|---|---|
| O-1 | A creator reaps, B subreaper deferred | UNDECIDED | REAL blocker | V2 review F02 |
| O-2 | B0 detective first; P1 separate intervention | UNDECIDED | criteria/REAL | V2 review F01 |
| O-3 | Instrumented creator wait with kernel corroboration, scoped trusted call path | UNDECIDED | REAL blocker | V2 review F02 |
| O-4 | G2-only claim capture, no Bench patching | UNDECIDED | implementation gate | V2 §5 |
| O-5 | fd+fdinfo only positive holder observation | UNDECIDED | prevention limit | V2 §2 |
| O-6 | No unproved absence; scope NOT_OBSERVED_UNDER_REGIME | UNDECIDED | criteria gate | V2 §2 |
| O-7 | Canonical sidecar chain plus independently retained seal | UNDECIDED | criteria gate | V2 review F04 |
| O-8 | <=2 forks, <=2 created live nodes, separate clocks | UNDECIDED | REAL blocker | V2 §7 |
| O-9 | D01-B0 before any P1/REAL grant | UNDECIDED | REAL scope | V2 review F01 |
| O-10 | Exclude intentional orphan; accident -> BLOCKED/manual | UNDECIDED | REAL blocker | V2 §7 |
| O-11 | Frozen Bench, socket claims untrusted | UNDECIDED | scope/credentials | V2 §2 |
| O-12 | Trusted G2 creator + native request_spawn | UNDECIDED | implementation | V2 §4 |
| O-13 | No guarantee normal<=60 implies anomaly recovery; require external containment | UNDECIDED | REAL blocker | V2 review F03 |
| O-14 | Shared-gate case synthetic only | UNDECIDED | test scope | V2 §2 |
| O-15 | B subreaper results not transferable to frozen E1-A | UNDECIDED | if B chosen | V2 §4 |

**Grok:** DEFERRED / NOT PERFORMED. When Grok becomes available, record its independent source-referenced findings, retain disagreement, and propose a separately authorized minimal controlled CPU-only discriminating experiment. User's temporary doc-continuation permission is not a Grok consensus.

## G. V2.1 acceptance and next checkpoint

| Check | Expected | Actual this turn | Status |
|---|---|---|---|
| Source provenance | Pinned V2 review and frozen Bench unchanged | GitHub source/checkpoint read and verified before document drafting | PASS (read-only scope) |
| F01–F06 response | Minimal, explicit design corrections with remaining limitations | Sections A–F, documented only | PREPARED, independent V2.1 acceptance PENDING |
| Authority | No implied Grok, owner decision or experiment grant | Grok deferred, O-1…O-15 all UNDECIDED | PASS for documentation consistency |
| Frozen criteria / G2 code / CPU / REAL | No modifications or new execution | NONE authorized or attempted | NOT TESTED / NOT AUTHORIZED |
| Git scope | Only new documentation branch, files and project checkpoint/index | Verify final commit comparison | PENDING final verification |

**Unique next instruction:** Independently review this V2.1 delta against frozen Bench and the V2 findings. Determine whether the scope can be **document-accepted for a future CPU-only specification drafting step** without pretending that native B0 is safe or that REAL is authorized. If the review still finds proof or operational-safety blockers, keep them OPEN / REAL BLOCKED; do not implement, run, freeze, signal or move stages.
