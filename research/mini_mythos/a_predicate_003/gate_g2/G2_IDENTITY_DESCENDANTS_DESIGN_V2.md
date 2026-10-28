# E1-A Gate G2 — identity, lineage and lawful reaping (DESIGN V2 DRAFT)

**Task:** F3B-D1-A-CPU-003-E1A-G2-DESIGN-REVISION-002 · 2026-10-28  
**Git baseline:** V1 at `ee7e9d46bc46b8dc15cc66ca06569d32a677561d`. Frozen Bench implementation audited at `450914367c247231c51be02e13775cb001e69c5d` (no Bench changes through V1).  
**Authority:** User reports Grok usage limit, permits **documentation work under a temporary Grok-review deferral**. This is NOT a Grok opinion, a PASS, a two-review substitute, a criteria freeze, implementation approval, CPU-test authorization or REAL authorization. Grok status: DEFERRED / NOT REVIEWED.  
**Stage status:** V2 DRAFT PREPARED; V2 design acceptance PENDING; G2 criteria NOT FROZEN; G2 code/CPU/REAL NOT AUTHORIZED; G3/BV/E1-A NOT AUTHORIZED.  
**History:** V0 and V1 remain preserved. Full F1–F9 historical review is in `G2_DESIGN_REVIEW_001_FINDINGS.md`; V1 reply is `G2_DESIGN_REVISION_001_RECORD.md`; V1 additional independent findings are `G2_V1_REVIEW_AND_GROK_DEFER_RECORD.md`. This V2 document takes precedence over V1's conflicting draft wording **only for design discussion**, not for frozen behavior.

## 1. Research boundary and system under test

G0: valid release under controlled process conditions (accepted one-run REAL result). G1: negative gate T1–T4 (accepted one-run REAL result). Neither proves a genuine descendant's uniqueness, trustworthy creator sender, complete runtime topology, lawful descendant wait, nor signal-free cleanup under adversarial conditions.

**B0 frozen system under test:** exact existing `bench/observer.py` ticket, `_on_created`, `_register` and `release` paths. No editing, importing and monkeypatching Bench as a replacement, or pretending its PRE_RELEASE checks suffice. Known B0 defect: a creator may report a different child with matching PPID, which B0 can register and release the *actual* gate reader. A CPU fixture demonstrating this unsafe acceptance is a **successful defect-reproduction test**, not a G2 safety PASS.

**P1 proposed isolated G2 preventive driver:** possible wrapper or subclass using the current `hold_release` parameter plus read-only witness before calling `release`; it is a **different intervention arm** with its own provenance and, if ever implemented, separate authorization. It can check consistency and reject observed conflicts, but mere /proc pipe possession is NOT sufficient adversarial creation-lineage proof. Unless a stronger independently reviewed witness or explicit trusted-creator restriction is adopted, P1 must not advertise malicious-creator prevention.

**J1 proposed pure G2 judge:** consumes read-back, timestamped raw observations, a separately specified immutable fixture truth for CPU, and a proposed evidence sidecar. Judge output is a classification, not an external source of truth. One may compare B0 versus P1, but not conflate outcomes.

**Allowed first REAL threat model (proposal only):** a controlled **trusted G2 creator** that calls the expected Bench ticket API honestly, no forged CREATED, socket-fd sharing, inherited gate-fd adversary, unknown outsiders, orphan injection, SIGKILL, subreaper changes, or fault injection. A PASS under this assumption must explicitly say **scoped trusted-creator attribution corroborated**, not uniquely authenticated fork identity. Malicious-creator properties remain NOT TESTED and cannot be inferred. If requirements demand adversarial safety, DESIGN BLOCKED until a kernel-backed witness mechanism is specified and authorized.

## 2. Source-grounded invariants and the pre-release trust boundary

- `bench/observer.py::_on_created` takes `msg["pid"]` and verifies /proc identity, pidfd and `ppid == creator_pid` through `_register`, **not** proof that the PID is the uniquely intended gate reader. It also has no global duplicate-(pid,starttime) rejection.
- `bench/gate.py::fork_gated` creates children that block until a one-byte `R`; the child closes `gate_r` **after** release. `bench/observer.py::release` persists `RELEASED` **before** attempting the byte write. Thus ledger RELEASED means intent, not actual delivery.
- The `/proc/<pid>/fd/<fd>` link `pipe:[gate_ino]` proves that descriptor points to the same pipe inode when observed, **not** which side is held, provenance, exclusive possession or receipt of `R`. A separate `/proc/<pid>/fdinfo/<fd>` open-mode read may distinguish read/write, but does not prove exclusive holder or unique fork. An unreadable required fd/fdinfo is UNKNOWN.
- PRE_RELEASE evidence must complete strictly **before the earliest possible `os.write(gate_w,b"R")`**, tracked with both `RELEASED`-ledger-intent time and actual `R`-write-begin/end times; the ledger timestamp alone is not a safe boundary. Only a specifically held release can support a controlled pre-release witness point. A later READY/FIRST_ACTION is a claim from a control socket and may corroborate/refute, **never retroactively prove pre-release safety**.
- Control `SOCK_SEQPACKET` messages are mapped to the socket-owning node record; `proto.py` has no per-message sender credentials. A forked sender can inherit a descriptor; READY, CREATED, WAIT_REPORT and FIRST_ACTION are **claims**, not independent sender-identity proofs. The design does not assert that SO_PEERCRED would fix this. Any real credential change to frozen Bench is out of scope.
- Kernel identity observation: `(boot_id, pid-namespace inode, pid, starttime)` plus pidfd identity and timestamp where available. Starttime resolution is coarse; `ppid` and `sid/pgrp` are time-indexed observations. Same PPID is not unique lineage; different SID does not disprove true child.
- **No hidden-holder/descendant absence by scanning.** Any /proc scan is non-atomic, may miss fast forks and may be obscured by hidepid. Two stable scans, `ns_last_pid` and a python fork counter are diagnostic, not sufficient universal absence proofs. Only positive structural proofs within their precise domain may support a negative claim, e.g. EPIPE for no gate reader on a never-released ticket; it says nothing about arbitrary untracked descendants.
- Source reaping shortfalls: `node_main` does not call wait; `Observer.reap_direct` only waits on its own direct children and treats ECHILD as a stored status; `common.process_is_dead` treats Z as dead; `DEAD` and `cleanup_confirmed` are not reap proofs; `e1a_runner`/janitor cleanup can SIGKILL. None of these may be reused as G2 REAL recovery claims.

**Counterexamples for CPU-only controlled fixtures:** CX-1 same-parent ordinary Q registered instead of actual gated G; CX-2 duplicate registered (pid,starttime); CX-3 multiple gate readers through inherited fd; CX-4 inherited control socket spoofs messages; CX-5 unreported/revoked/late CREATED; CX-6 RELEASED intent recorded without delivery; CX-7 stable scans miss a transient fork; CX-8 Z and DEAD but no wait; CX-9 ECHILD without proof of lawful reap. Do **not** run live malicious-creator, bystander or fault-injection cases under G2 first REAL.

## 3. Evidentiary vocabulary and lifecycle

| Claim | Minimum evidence | Forbidden inference |
|---|---|---|
| CLAIMED_PID | Creator's CREATED or ticketed FORKED pid | Validated identity/lineage |
| KERNEL_ID_AT_T | Timestamped pinned /proc identity; optionally pidfd | Parent history, ticket recipient |
| PARENT_AT_T | Timestamped `ppid`, ideally while gate held | Creation lineage forever |
| GATE_FD_OBSERVED | Before R: a matching fd inode plus *separate* read-mode observation if available; report seen holders and unreadable entries | Exclusive gate holder; unique creator fork; R recipient |
| ATTRIBUTION_CORROBORATED | Under **trusted-creator** scoped assumption: ticket + PARENT_AT_T + GATE_FD_OBSERVED + stable identity + ledger; all temporal constraints satisfied | Adversarial identity/authenticity guarantee |
| EXIT_OBSERVED | Pinned pidfd readable | Reaped or its exit status |
| ZOMBIE_OBSERVED | Same process instance has /proc state Z with observed ppid | A wait already occurred |
| REAP_CLAIMED | Creator sends WAIT_REPORT(pid, raw status) | Wait syscall actually occurred |
| REAP_CORROBORATED | Z with lawful parent, creator alive, claimed wait, then same identity absent under /proc; `SIGCHLD` / `SA_NOCLDWAIT` / other waiter assumptions reviewed | Independent proof of creator's wait call |
| REAP_INSTRUMENTED | An explicitly **trusted** G2 wait wrapper, in the lawful reaper, records called pid, return pid/status/errno and order; cross-checked against independent kernel observations | Kernel-level unforgeable attestation |
| PROC_GONE | Same /proc PID instance absent with pinned lifecycle observations | Identity of reaper or that process never existed |

**`REAP_CONFIRMED` is not used as a blanket label for REAP_CLAIMED or REAP_CORROBORATED.** If a frozen later protocol uses it at all, it must define which trusted instrumentation (and trust boundary) justifies it. A subreaper observer directly executing `waitpid` can record its own call but changes the target kernel behavior and is a separate arm.

Explicit negative case: `ECHILD`, zombie `Z`, `DEAD`, `cleanup_ok`, pidfd readiness or `PROC_GONE` by itself **never** implies lawful reap. Lost ppid history, unknown signal disposition, `SA_NOCLDWAIT`, other waiters or an orphaned child => insufficient provenance → subject BLOCKED, no invented REAP event.

## 4. Reaper alternatives — not frozen

**A: creator-owned:** a G2-specific `g2_creator_main`, spawned as an observer direct child through the existing Bench interface, creates one honest ticketed descendant. The child runs frozen `node_main` and can self-exit after READY (or on EXIT/EOF if fd closure is understood). The creator, as actual parent, is the lawful waiter for its descendant. An outside observer witnesses pidfd-readable + Z with `ppid == creator`; sends GO_REAP; creator's G2 wait wrapper makes *specific-pid* wait and records syscall attempt/result; observer verifies `/proc` disappearance. Record both claimed/instrumented source and corroborating external observations; judge uses the agreed strength **without upgrading a claim to a kernel fact**. The creator then exits under its own cooperative/lifetime controls, and the observer—as creator's actual parent—directly witnesses its own specific-pid wait. Creator must remain alive until descendant has been lawfully reaped. **REAL remains blocked** until trusted recorder/exit lifetime is reviewed.

**B: observer subreaper:** enable PR_SET_CHILD_SUBREAPER before forks; adopted orphans become direct descendants of the observer, which can wait on pinned identities. This materially changes E1-A target behavior (S0 requires subreaper initially unset), may adopt unregistered unrelated children, and cannot transfer a PASS to frozen E1-A. Strictly separately versioned future study, not first-real default; no authorization.

**Provisional recommendation, not a decision:** prefer A for a minimal honest-creator **design** and defer B. The owner must approve O-1 and the required evidentiary strength O-3 before any criteria freeze. Orphans are excluded from first real; accidental orphans => BLOCKED + manual disposition, never "reaped by PID 1" as an attributable wait.

## 5. Independent witness / sidecar

A G2-only, append-only `g2_sidecar.jsonl` (not a Bench registry extension) records separately time-stamped raw claims and reads: CLAIM_RECEIVED, KERNEL_ID_AT_T, PARENT_AT_T, GATE_FD_OBSERVED, actual R write begin/end if wrapped, RELEASED_INTENT, ZOMBIE_OBSERVED, EXIT_OBSERVED, WAIT_REQUEST, WAIT_REPORT, INSTRUMENTED_WAIT, PROC_GONE, SCAN_REGIME, STOP_RULE, GUARD_EVENT. Each record has node/creator ids, observation time, source, trust tier and local sequence.

Proposed chain: canonical JSON serialization; monotonically increasing seq, `prev_sha256` and digest of each record; explicit genesis, max size, torn-tail rejection, fsync + readback and **externally separately sealed final head** bound in closeout. A self-contained chain **alone** cannot detect valid-prefix truncation without an independent trusted final digest, and cannot authenticate the sender or make a shared-process witness independent. Same-process witness is **code-path independence, not process independence**; a separate witness is a future design choice and cannot silently be assumed present. Record file hashes and readback verdicts, including fail-closed corrupt/missing paths.

## 6. Two-level acceptance — CPU fixture expected BLOCKED can produce TEST PASS

Three required per-fixture fields: `expected_subject_verdict`, `actual_subject_verdict`, `test_acceptance_verdict`. The expected classification is frozen *before* evaluating the SUT. Subject classifications: PASS within scoped assumptions / FAIL on positively proven violation / BLOCKED for unknown, missing, unreadable or unverifiable required proof. Aggregation precedence for subject: FAIL > BLOCKED > PASS. The CPU **test** is PASS when actual subject == predeclared expected subject and separate guard/evidence conditions pass; FAIL on mismatch or unsafe acceptance; BLOCKED when test instrumentation itself is inconclusive; NOT_RUN when not executed. Test-run PASS requires complete expected test-ID set exactly once, no exceptions, skips, unknown IDs or violation, and two independent raw checks if so preregistered.

| Fixture example | Expected subject | Actual subject example | CPU test |
|---|---|---|---|
| corrupted ledger / unreadable /proc | BLOCKED | BLOCKED | **PASS** |
| zombie DEAD but no wait | BLOCKED for reap | BLOCKED | **PASS** |
| frozen B0 accepts wrong same-PPID child | ACCEPTED_UNSAFE (diagnostic behavior label, not a safe G2 verdict) | ACCEPTED_UNSAFE | **PASS — defect reproduced, not safety PASS** |
| judge falsely calls wrong child safe | FAIL or BLOCKED from independent positive truth | PASS | **FAIL** |
| judge classifies true documented violation | FAIL | FAIL | **PASS** |

The CPU suite must explicitly bind unique IDs for **14 scenario cards** grouped into 10 families: `G2-D01,D02,D03a,D03b,D03c,D03d,D03e,D04,D05,D06,D07,D08,D09,D10`. Maintain distinct SUT (B0 / P1 / J1 / guard), independent truth provider and preventive/detective expectations per card; first REAL does not inherit permission to run the CPU fixture's malicious actors.

### Exact 14-card acceptance inventory (V2; **proposed, not frozen**)

| Unique ID | SUT | Truth source | Required *subject* result/limit | Test permission boundary |
|---|---|---|---|---|
| G2-D01 | B0/P1 separate, J1 judge | TP-KERNEL + declared honest-creator truth | Attribution corroborated only in trust-limited REAL; missing pre-release links -> BLOCKED | REAL later; no permission now |
| G2-D02 | J1 on time-indexed sid/pgrp | TP-KERNEL before/after READY | Never infer bloodline from current sid/pgrp; undocumented transition -> BLOCKED | REAL later |
| G2-D03a | B0 identity check + J1 | TP-FIXTURE wrong starttime | Refuse/identity UNKNOWN; unsafe accepted identity -> FAIL | CPU only |
| G2-D03b | B0 ticket check + J1 | TP-FIXTURE foreign node id | Refuse foreign ticket; unsafe accepted child -> FAIL | CPU only |
| G2-D03c | B0 defect replay / J1 | TP-FIXTURE same-parent wrong PID | B0 ACCEPTED_UNSAFE is expected diagnostic reproduction, **not safety PASS**; J1 unsafe PASS -> test FAIL | CPU only |
| G2-D03d | B0 defect replay / J1 | TP-FIXTURE duplicate pid/starttime | No proof of unique owner, J1 BLOCKED or FAIL when positive conflict known | CPU only |
| G2-D03e | J1 pid-reuse identity | TP-FIXTURE time-indexed starttime | Wrong instance not accepted; unknown race -> BLOCKED | CPU only |
| G2-D04 | B0 revoke/late handling + J1 | TP-FIXTURE, gate EPIPE if positively supplied | Unresolved ticket -> subject BLOCKED, correct decision -> CPU test PASS | CPU only |
| G2-D05 | J1 ledger / sidecar integrity | TP-FIXTURE torn, altered, missing record | subject BLOCKED when integrity unknown; correct BLOCKED -> CPU test PASS | CPU only |
| G2-D06 | J1 outsider / spoofed socket | TP-FIXTURE independent outsider labels | No outsider signal/wait; origin unverifiable -> BLOCKED | CPU only |
| G2-D07 | J1 reaping states, later A recorder | TP-FIXTURE + TP-KERNEL for future REAL | Z/DEAD/ECHILD not REAP; claimed wait not confirmed; correct BLOCKED -> CPU test PASS | CPU first; REAL later |
| G2-D08 | J1 gate shared holder | TP-FIXTURE two readers | No unique gate recipient proof; subject BLOCKED, positive wrong-pass -> FAIL | CPU only |
| G2-D09 | J1 release delivery | TP-FIXTURE RELEASED without R/action proof | RELEASED is intent; unconfirmed delivery -> BLOCKED | CPU only |
| G2-D10 | G2 guard and exception judge | TP-FIXTURE forbidden call / residual | guard blocks forbidden call; subject FAIL for proven unsafe attempt / BLOCKED for missing guard | CPU first; REAL only in authorized run |

**All rows require** separate fixture-declared `expected_subject_verdict`, observed `actual_subject_verdict` and `test_acceptance_verdict` (PASS on exact expected response plus intact guard/evidence). `ACCEPTED_UNSAFE` is a **diagnostic baseline behavior label** in a defect-reproduction fixture, not a G2 safe subject PASS. Every positive FAIL requires a witness of the protocol violation, while missing required proof yields subject BLOCKED. For each REAL candidate, specify PREVENT vs DETECT semantics and do not claim inherited permissions from CPU fixtures.

## 7. Card scope, stop rules and process budget

| Scope | Candidate cards | Truth/expected limit |
|---|---|---|
| CPU only / synthetic | D03a–e, D04, D05, D06, D08, D09; pure judge/guard parts of D07/D10 | Author hand-specified immutable truth; no fork/signal/kill/wait/exec/subprocess; correct subject BLOCKED may yield TEST PASS |
| REAL future, strictly separate owner grant | D01 initially; D02 and live D07 only after separately reviewed scope | Honest single creator + one descendant; predeclared attribution claim strength; no adversarial creator, sharing, orphaning or fault injection |
| Out of scope | Any forged live claim, outsiders, malicious gate reader, subreaper manipulation under A, G3/BV/E1-A | Never auto-authorized by a G2 design/CPU PASS |

**Candidate graph budget (not frozen):** exactly at most 2 fork attempts per card (one observer-created creator; one creator-created descendant), maximum 2 concurrently alive spawned nodes, no grandchildren, no janitor, no signals, no group operations, no external process manipulation. `T_GATE_MAX=10s`, `T_REG_MAX=5s`, `T_NODE_MAX=120s` for frozen `node_main`. A proposed **normal-path target ≤60 s is not a maximum safe cleanup time**. To use frozen node_main, anomaly observation/settlement may need at least 120 s from last child creation plus bounded margin and a still-live lawful creator; exact deadlines and timeout budgets O-8/O-13 remain **OPEN**. If containment cannot be guaranteed in the given environment and no-signal policy, do not authorize REAL. A timer expiry is not evidence of cleanup.

**Forbidden real paths:** `e1a_runner`, `trial._cleanup`, `Observer.finish_cleanup/final_cleanup/kill_registered/kill_unregistered_direct`, janitor start or `janitor.run_cleanup_full`, any SIGKILL, `waitpid(-1)`, unreviewed subreaper. A G2 runtime guard must intercept or detect forbidden calls, be installed before any fork and be tested independently on CPU; it is only Python-level enforcement. Signalless cleanup is *cooperative exit*, not a guarantee.

**Healthy flow A (proposal):** preflight → install guard → pin hashes & complete reaper table → one creator fork/release → one gated descendant registration → expected self-exit → pidfd+Z snapshot → request specific-pid parent wait → observe reported/instrumented wait and /proc disappearance → creator cooperative exit → observer-specific wait for creator → confirm no *known* live nodes in defined scope; record scan limits, hash/read-back, closure. No hidden-absence claim.

**Anomaly flow:** stop new work, do not send R to unresolved/unsafe nodes, close intake for unreleased tickets, request EXIT only from identified nodes where safe, inspect **all socket descriptor holders** as far as visible (EOF does not occur until all write/peer references close), preserve the lawful creator to wait for its child when possible, and perform bounded observation. If any identity, reaper, socket holder, survival state, or evidence integrity remains unknown: verdict BLOCKED and emit `MANUAL_DISPOSITION_REQUIRED.json` (pid/starttime/boot/pidns, last ppid/state, expected reaper, fd holders, time, unperformed actions, hash). A manual-disposition file is an **outstanding human/OS responsibility** and never retroactively clears residue. Do not kill, clean by process name, wait for non-children, or retry to make PASS. REAL remains design-blocked until both normal and anomaly paths have credible approved bounds and the environment can safely support them.

## 8. O-1 through O-15 — provisional recommendations, NOT owner decisions

| Open | Suggested direction for next design review | REAL gate |
|---|---|---|
| O-1 lawful reaper | A initially, B deferred | **BLOCKER** |
| O-2 prevention tier | Freeze B0 vs P1 as distinct arms; P1 cannot claim malicious-creator proof | **BLOCKER** |
| O-3 witness/attribution | Require exact wait evidence tier; decide whether INSTRUMENTED is enough | **BLOCKER** |
| O-4 raw claim capture | G2-only tap/wrapper, record intervention status; keep Bench immutable | review |
| O-5 gate fd visibility | fd + fdinfo as observed, never exclusive-holder proof | **BLOCKER for prevention claim** |
| O-6 absence claims | Limited NOT_OBSERVED_UNDER_REGIME wording; required unprovable absence -> BLOCKED | **BLOCKER** |
| O-7 sidecar durability | canonical chain + externally sealed head + readback + size limits | review |
| O-8 budget | <=2 forks, <=2 live, max depth 2, exact timeouts to be frozen | **BLOCKER** |
| O-9 run separation | D01-only first; D02/D07 require separate owners' decisions | review |
| O-10 orphans | Exclude intentionally; unexpected orphan -> BLOCKED/manual | **BLOCKER** |
| O-11 sender creds | Bench unchanged, claims not authentication | review |
| O-12 descendant path | frozen node.request_spawn, G2 creator entry | review |
| O-13 lifetime/settlement | normal and anomaly budgets separate; creator must outlive lawful wait duty | **BLOCKER** |
| O-14 shared gate | CPU synthetic only | review |
| O-15 B transfer | No transfer from B to E1-A; if B used, separate study | **BLOCKER if B chosen** |

No open choice is silently settled by Grok's unavailability; the user permits drafting proposals, not backfilling an independent evaluation.

## 9. Stage gates / acceptance

- **This stage (S0 V2 design):** Objective = revise V1-R1…R5 and preserve F1–F9; environment = GitHub document-only; inputs = pinned source, V1, previous review; expected = scoped proof definitions, double verdicts, safe stop, 15 open decisions; actual = V2 document; design drafting **PREPARED**, review **PENDING**; CPU/REAL **NOT TESTED/NOT AUTHORIZED**.
- **S1 criteria freeze:** only after remaining O decisions resolved or explicitly scoped out, reviewer evidence retained, and separate OWNER APPROVAL; publish own G2 V1 closed criteria, hashes, predeclared tests, epistemic ceilings, safety budgets, and immutable provenance.
- **S2 implementation:** separately authorized G2-only code and independent static review; no Bench/Parcae/R3 edits.
- **S3 CPU:** separately authorized pure fixtures with pre-import process sentinel, complete ID set and two-level verdict; no real processes.
- **S4 CPU evidence cross-review**, then **S5 single-use REAL authorization** only for pre-approved scoped case(s).
- **S6 REAL:** never infer it from S3 PASS; require full preflight, safe stop and honest-creator scope, specified reaper; preserve all identities, raw evidence and separate closure.
- **S7 cross-review and checkpoint:** only after independent evidence evaluation; G3/BV/E1-A remain separate.

**Next unique instruction:** independent V2 source/design review with Grok review explicitly DEFERRED under user-approved temporary documentation exception. If reviewer finds a counterexample, revise the *smallest* design assertion; if unavoidable proof/recovery gap remains, keep REAL BLOCKED. No tests, process experiments, code implementation, criteria freeze or new-stage authorization are granted.
