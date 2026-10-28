# Historical G2 design V1 — superseded by the separate V2 draft

> **ACTIVE DESIGN DRAFT (NOT FROZEN):** [`G2_IDENTITY_DESCENDANTS_DESIGN_V2.md`](G2_IDENTITY_DESCENDANTS_DESIGN_V2.md). This V1 body remains here as a historical review target and is archived byte-identically at `G2_IDENTITY_DESCENDANTS_DESIGN_V1_ee7e9d4.md`. Its stronger `GATE_HOLD_PROOF` / `CREATION_LINEAGE`, creator-reported `REAP_CONFIRMED`, and single-level BLOCKED test semantics are **not approved claims**. The V2 draft corrects them. Grok design review is temporarily deferred due to reported usage limits, **not PASS**. G2 criteria/code/CPU/REAL remain NOT AUTHORIZED.

---

# E1-A Gate G2 — process identity, descendant lineage, reaping and observation safety (DESIGN DRAFT V1, revision 001)

**Task:** `F3B-D1-A-CPU-003-E1A-G2-DESIGN-REVISION-001` (revises `F3B-D1-A-CPU-003-E1A-G2-DESIGN-001`)  
**Date:** 2026-10-28  
**Scope:** DOCUMENTATION ONLY. **G2 DESIGN REVISION PREPARED — CROSS-REVIEW PENDING. G2 CRITERIA NOT FROZEN. G2 IMPLEMENTATION NOT AUTHORIZED. G2 CPU TESTS NOT TESTED / NOT AUTHORIZED. G2 REAL NOT AUTHORIZED.**  
**Base commit of this revision:** `8f9e8b2c027b3f6c0b738650b57af62d52dce141` (V0 draft, archived unchanged as `G2_IDENTITY_DESCENDANTS_DESIGN_V0_8f9e8b2.md`).  
**Source baseline audited:** `bench/` at `450914367c247231c51be02e13775cb001e69c5d` (byte-identical in `8f9e8b2`). File:line references below are to that baseline.  
**Review record:** the nine original findings F1–F9 are preserved in `G2_DESIGN_REVIEW_001_FINDINGS.md`; how each was handled is in `G2_DESIGN_REVISION_001_RECORD.md`. Nothing in this document is a runtime authorization, a frozen criterion or a claim that any property holds.  
**Naming:** this G2 is the E1-A process-identity gate after G0 (valid release) and G1 (negative gate). It is not the archived R3-A liveness-predicate "G1/G2 FAIL", and not BV / E1-A cells / G3.

## 1. Why G2, research question, non-goals

G0 checked one valid release, G1 four negative gate paths; neither shows that a released creator's ticketed child is attributed to the right creator, that identity facts are not confused with lineage, or that exit and reaping are proven rather than assumed.

**Question (unchanged in intent):** with frozen Bench code, can an independent witness plus a G2 judge tell the authorized creation chain from outsiders and uncertain children, without inventing a child, losing an unresolved child, signalling anything, or calling a process "reaped" without trustworthy evidence?

**Not in scope:** G3 recovery / fault injection; BV; E1-A cells; performance or quality; architecture; training; data; process-group cleanup; any signal. Design approval is not authorization.

**Frozen and untouched by this revision:** G0 V1–V5, G1 V1, `bench/` (hash `b6f52a8c…d3b0`), Parcae, R3, E1-A preregistration, model architecture. G2 will live only in `gate_g2/` (and tests / tools later); nothing in `bench/` may be edited, patched or monkey-patched in place. Python-level *subclassing or wrapping from G2 code* is not an edit of Bench, but it changes which code path is tested; that is recorded as open choice O-2 / O-4.

## 2. Source audit (observed code, baseline `4509143`; corrections of V0 marked ★)

| Source | Observed mechanism / fact | Limitation relevant to G2 |
|---|---|---|
| `bench/gate.py::fork_gated,gate_wait,child_hygiene` (33-39, 42-61, 64-82) | The only `os.fork`; child closes all fds except `{0,1,2,gate_r,ctrl}`, waits for `b"R"`, then **`os.close(gate_r)`** (line 77) and runs `entry`. | ★ After release the child no longer holds the gate read end, so **no gate-hold evidence can exist after release**; it can only be collected before `R` is written. |
| `bench/observer.py::spawn_direct,_note_forked,_register,release` (61-141) | Direct child: INTENT -> fork -> FORKED -> REGISTERED (fingerprint, `PidfdHandle`, `ppid == creator_pid`) -> `RELEASED` record -> write `R` -> SPEC. `_register(rec, pid, creator_pid, hold_release=False)` has a **`hold_release` parameter** (103, 124). | ★ `release()` is outside the `try` in `_register` (125); `BrokenPipeError` from `os.write` would escape `_on_created`. `RELEASED` is written before the byte (131-133): it records intent, not delivery. |
| `bench/observer.py::_on_ticket,_on_created` (246-305) | Ticket for a creator in state `RELEASED`; `CREATED` carries a **creator-supplied pid** (281). Child record keyed by node id; `child.creator != creator.node_id` is rejected (278). Late or revoked paths: ignored if the gate already proved absence (282-286), recorded as FORKED but not registered or released if aborted / intake closed (287-294). Otherwise `_note_forked` then `_register` **with immediate release** (299-301). | ★ No check that the pid holds the gate read end, none that the pid is not registered to another node; the ticketed path offers no hold point unless a caller overrides `_register`. Node identity is by *socket*, not by process. |
| `bench/observer.py::_handle` (201-229), `bench/proto.py` | SEQPACKET socketpair created by the observer; no `SO_PASSCRED` / `SCM_CREDENTIALS`; node messages are JSON dicts. | ★ Anyone holding the socket end can send or receive on it. |
| `bench/node.py::request_spawn,node_main` | Creator side of TICKET -> `fork_gated(gate_r, ctrl, node_main, …)` -> CREATED -> REGISTERED_OK. `node_main` applies `setsid` / `setpgid`, creates declared children, sends `READY` with its own fingerprint, `exit_after_ready` -> `os._exit(0)`; otherwise waits for `EXIT` / EOF / `T_NODE_MAX = 120 s`. | ★ **`node_main` never calls any wait function**; `request_spawn` hard-codes `node_main` as the child entry. |
| `bench/sup_stub.py::bench_reap` (69-82, 115-116) | The supervisor stub waits by specific pid, only for helper nodes named by a recipe `reap` op. | ★ This is the only existing creator-side reaping; it does not cover descendants created by `node_main`. |
| `bench/observer.py::reap_direct,_confirmed_dead,mark_dead` (377-454) | Observer waits by specific pid on its own direct children. `ChildProcessError` sets `exit_status="ECHILD"` (386-388); `_confirmed_dead` returns true for any non-None `exit_status` (407) and for `process_is_dead` (403); `mark_dead` writes `DEAD` with basis "confirmed dead from /proc" (440-441). | ★ `ECHILD` and zombie-as-dead are folded into "dead". |
| `bench/common.py::scan_proc,children_of,fingerprint,PidfdHandle,process_is_dead` (99-241) | `scan_proc` records only *unreadable* entries; a vanished entry is silently skipped (122-128). `children_of` ignores `problems` (132). `PidfdHandle` opens the pidfd first, then compares starttime; readable pidfd = exited (zombie or reaped). `process_is_dead` counts state Z / X as dead (238-241). | ★ A scan is not a point-in-time snapshot; pidfd readability and Z say nothing about who reaped. |
| `bench/registry.py` (9, 61-80, 83-143, 170-247) | KINDS = RUN_START, INTENT, FORKED, REGISTERED, RELEASED, ABORTED, DEAD, RUN_END. Torn tail, corruption, sequence gaps detected. `cleanup_confirmed=True` legal when all non-janitor nodes have `DEAD` (121-126). | ★ **No CREATED / EXIT / REAPED kind.** `integrity_issues` / `check_order` do not check `REGISTERED.ppid == creator pid`, `INTENT.creator_pid` or pid uniqueness. `FORKED.pid` of a ticketed node is creator-asserted and `FORKED.starttime` is read at receipt. |
| `bench/observer.py::close_intake,_abort,_probe_gate,verify_run_set,finish_cleanup,final_cleanup,kill_registered,kill_unregistered_direct` (143-182, 232-241, 338-375, 456-533) | EPIPE on the gate write end proves that no process holds the gate read end (sound for never-released tickets); `kill_*` use pidfd SIGKILL; `finish_cleanup` / `final_cleanup` call them. | Unsafe for a non-signal run; bypass required (§9). |
| `bench/janitor.py::run_cleanup_full,decide,main` (44-82, 179-245) | Acts only on complete REGISTERED records with pidfd + starttime check; **SIGKILL** to every non-DEAD registered target; autonomous process; uses `process_is_dead` (114). | A wrongly attributed pid in the ledger becomes a kill target. |
| `bench/trial.py::_cleanup`, `bench/e1a_runner.py:319` | `finish_trial_cleanup`; `final_cleanup` unconditionally in `finally`; janitor started by the runner. | These runners cannot be reused for a non-signal G2. |
| `bench/truth.py` (9-15, 55-67, 100-112) | Enumeration-incomplete -> BLOCKED; topology / bystander checks; subreaper must be unset before S0; fd hygiene checks the *write* end only. | Existing truth functions are E1-A specific, not an identity judge. |
| `bench/validity.py::bv2,bv6,bv7` | BV checks (observer death, wrong-identity janitor, torn registry). | BV, some signal-capable; not G2. |

This audit shows available mechanisms and limits; it is not proof that an unwritten G2 protocol satisfies anything.

## 3. Evidence vocabulary (resolves F1, F3, F4, F5; all names are proposals until frozen)

### 3.1 Identity layers (F1) — never interchangeable

| Term | Definition | Provider | What it can support | What it must never be used for |
|---|---|---|---|---|
| **CLAIMED_PID** | A pid asserted by a node message (`CREATED.pid`) or carried in a ledger record the observer wrote from such a message (`FORKED.pid` of a ticketed node). | node (creator) | Hypothesis to verify. | Evidence of identity, lineage or attribution. |
| **KERNEL_IDENTITY** | `(boot_id, pidns inode, pid, starttime)` read by the witness at a recorded monotonic time, optionally pinned by a pidfd. starttime resolution is 1/CLK_TCK. | witness (`/proc`, pidfd) | "This process, at this time, is this pid instance." | Lineage, creator, role, gate membership. |
| **KERNEL_PARENT_AT_T** | `ppid` read from `/proc/<pid>/stat` at time T. | witness | Parent at T (the pre-release read is the only independent kernel parent evidence while the child cannot act). | Parent at any other time; creation history after reparenting. |
| **GATE_HOLD_PROOF** | Before `R` is written: `/proc/<claimed pid>/fd/*` contains a link `pipe:[gate_ino]` (gate read end; `gate_ino` is the pipe inode known to the observer as `rec.gate_ino`, `observer.py:267`), and the **number of other observed holders** of that inode is reported with the enumeration regime. | witness, **only if a hold point exists** (O-2) | "The claimed pid holds the read end; second holders observed or not observed under regime R." | Exclusivity ("nobody else holds it"), which a scan cannot prove (§3.5). Any time after release. |
| **CREATION_LINEAGE** | Chain: creator KERNEL_IDENTITY (pinned) + ticket issuance record + claim receipt + pre-release KERNEL_PARENT_AT_T equals creator pid + GATE_HOLD_PROOF + registration. | judge, from the above | "Authorized child of this creator" — only when every link is present and pre-release. | Anything if any link is missing (then UNKNOWN / BLOCKED). |
| **SESSION/GROUP FACTS** | `sid`, `pgrp` as separate time-indexed fields. | witness | Observing `setsid` / `setpgid`. | Membership or lineage (a bystander can share a session; a true child can leave it). |

**Pre/post-release rule (F1).** Every evidence item carries the monotonic time of the `RELEASED` ledger record of its node as cutoff. Evidence older than the cutoff is PRE_RELEASE, otherwise POST_RELEASE. POST_RELEASE evidence — `READY`, `FIRST_ACTION`, post-release `/proc` reads, the node's self-reported `fp` — may **refute** (a mismatch is a violation or BLOCKED) or **corroborate**; it can **never** be the sole basis of "identity / gate hold was verified before release". In particular `READY.fp.pid == registered pid` is a mandatory detective check, not a preventive proof: by then the process has already been released and may have acted.

### 3.2 Counterexamples the design must handle (F1; derived from source, not run)

| ID | Counterexample | Why current frozen code accepts or mishandles it | Required outcome |
|---|---|---|---|
| CX-1 same-parent wrong PID | Released creator plain-forks Q, takes a ticket, forks the gated child G, reports `CREATED pid=Q`. | `_register` checks only starttime stability and `ppid == creator.pid` (106-116); Q passes; `R` goes to G; G runs unregistered; Q is the ledger identity; a later `kill_registered` / janitor kills Q. | Preventive tier: refuse before release (no `R`, no signal). Detective tier: post-hoc FAIL (misattribution) or BLOCKED; never PASS. |
| CX-2 duplicate PID | A creator reports a pid already registered to another node it parents. | No pid-uniqueness check anywhere in `observer.py` / `registry.py`. | Refuse / flag: (pid, starttime) must be unique over the whole ledger. |
| CX-3 shared gate fd | Creator forks Q after receiving `TICKET_OK` and before closing its copy of `gate_r` (`node.py`: closes after `fork_gated`). Q holds the read end too. | First reader consumes `R`; the registered G may time out (112) or abort (111) while the unregistered Q "received" release; `_probe_gate` EPIPE stays false (conservative). | Holder count > 1 observed -> violation / BLOCKED; `R` delivery recipient is UNKNOWN unless the first-action witness agrees. |
| CX-4 shared control socket | A plain-forked descendant inherits the creator's `ch` socket and sends TICKET / CREATED or steals `TICKET_OK`. | Node identity is the socket (`_handle`, 201-229); no per-message sender credentials. | Messages are claims; cross-check with `/proc`; fixture-only (D09). |
| CX-5 late / unreported creation | CREATED arrives after revoke / abort, or never. | Source is fail-closed (282-294) but `FORKED.pid` / `starttime` of the late path are unverified and may name a recycled pid. | Ledger FORKED pid of a ticketed node is labelled "creator-asserted, unverified"; never a signal target; unresolved -> BLOCKED. |
| CX-6 release not delivered | Gate reader vanishes between registration and `os.write(R)`. | `RELEASED` is already durable; the exception escapes `_on_created` (124-126). | RELEASED is intent; delivery requires `FIRST_ACTION`; undelivered -> BLOCKED. |

### 3.3 Exit, reap and disappearance (F3) — four states, kept apart

| State | Meaning | Evidence that establishes it | Does NOT imply |
|---|---|---|---|
| **EXIT_OBSERVED** | The pinned process instance has terminated. | pidfd for the pinned (pid, starttime) readable, timestamped. | Zombie vs reaped; who (if anyone) waited; the exit status. |
| **ZOMBIE** | Terminated, not yet waited for. | `/proc/<pid>/stat` state `Z` for the same starttime, with `KERNEL_PARENT_AT_T` recorded. | That anyone will reap it; that the parent is the intended reaper (check ppid). |
| **REAP_CONFIRMED** | The *lawful reaper* performed a wait that returned this pid. | All of: ZOMBIE observed earlier with `ppid == lawful reaper`; a wait record by the lawful reaper naming that pid with its raw status; reaper alive and SIGCHLD not ignored (independent `SigIgn` read) from ZOMBIE to PROC_GONE; PROC_GONE after the wait. A creator's wait record is a *claim*; the design therefore states the attribution strength as "corroborated by independent kernel facts", not "independently proven" (see O-3). | That the exit was signal-free unless the raw status shows a non-signal exit. |
| **PROC_GONE** | `/proc/<pid>/stat` absent (and pidfd still readable). | witness read. | Reaped by the lawful reaper (could be PID 1 after orphaning, or auto-reap), or even that the process ever existed. |

Rules:
- **R-F3-1:** `DEAD` records, `Observer._confirmed_dead`, `mark_dead`, `cleanup_ok`, registry `cleanup_confirmed`, `process_is_dead`, `ECHILD`, and pidfd readability are **each non-evidence for REAP_CONFIRMED** (they fold Z, ECHILD or exit into "dead").
- **R-F3-2:** `ECHILD` is classified `WAIT_ECHILD` and means one of: already reaped by someone, auto-reaped (SIGCHLD ignored / `SA_NOCLDWAIT`), never a child. It is BLOCKED unless an independent fact explains it; it is never a reap.
- **R-F3-3:** States that were not observed are UNKNOWN, not inferred. Skipping a state is allowed but lowers the claim: PROC_GONE without a prior ZOMBIE-with-lawful-parent is "disappeared, reaper unattributable".
- **R-F3-4:** A zombie whose parent is not the lawful reaper (e.g. PID 1) is *residue* until a lawful wait is recorded; the observer cannot wait for non-children and no signal may be sent, so it is BLOCKED with manual disposition (§9).

### 3.4 Messages, credentials and the ledger (F4, F5)

- **F4 limits.** Frozen `proto.py` carries no sender credentials. For a socketpair created by the observer, the kernel's peer credentials (`SO_PEERCRED`) are expected to name the observer, not the node, so they cannot serve as sender identity (expected kernel semantics; **not verified in this stage**, and the design must not depend on them). Per-message `SCM_CREDENTIALS` would carry the real sender pid but needs `SO_PASSCRED` on the receiver, i.e. a Bench change, which is outside G2 (O-11). Consequence: every node message (`TICKET`, `CREATED`, `READY`, `FIRST_ACTION`, wait reports) is a **CLAIM**; the judge only uses a claim after cross-checking it with KERNEL facts, and an unverifiable claim yields UNKNOWN.
- **F5 facts.** The frozen registry has no CREATED / EXIT / REAPED kind; `FORKED` is written at claim receipt and its pid is creator-asserted; its internal checks omit lineage consistency; `RELEASED` is intent. G2 must not extend the registry.
- **G2 SIDECAR (isolated evidence).** A separate append-only file `g2_sidecar.jsonl` in the run directory, written **only by G2 witness code**, never by Bench:
  - created exclusively; one `O_APPEND` write per line; own `seq`; each line carries `prev_sha256` (hash chain) so lost, reordered, torn or edited lines are detected; closure binds the final chain hash;
  - raw observations only, no verdicts: `CLAIM_RECEIVED` (node id, claimed pid, observer receive time, message hash), `KERNEL_ID`, `KERNEL_PARENT`, `GATE_HOLD` (claimed pid, holders seen, regime id, unreadable count), `RELEASE_CUTOFF` (time of the node's `RELEASED` record, taken from the in-memory ledger), `EXIT_OBSERVED`, `ZOMBIE_OBSERVED`, `WAIT_REPORT` (claim), `OBSERVER_WAIT` (observer's own wait calls with raw status or errno), `PROC_GONE`, `SCAN` (regime, entries, unreadable, vanished-during-read counters, pid-set hash), `GUARD_EVENT`, `GO_REAP_SENT`, `STOP_RULE`;
  - cross-reference to the frozen registry by node id and by the shared `CLOCK_MONOTONIC` only; the registry itself is read back as evidence of what the observer believed, never as truth.
  - derived verdicts live only in the judge output, never in the sidecar.
- Independence statement: sidecar and registry are written by the same observer process; the sidecar is independent in *code path* (it does not import `registry` / `observer` classification) and in *kernel source* (`/proc`, pidfd), not in process. A separate witness process is open choice O-3.

### 3.5 Completeness claims (F6) — nothing in this design proves an absence

- A `/proc` scan is a sequence of non-atomic reads. A process created after `listdir`, or forked and exited between scans, is invisible; `hidepid` or permissions can hide entries; pids can be reused; `scan_proc` does not flag vanished entries. **No scan regime, however many repetitions agree, proves that no descendant, unregistered process or residue exists.** The V0/review idea of "two stable scans" is therefore *withdrawn as a sufficiency argument*; repeated scans are retained only as a way to **find** violations and to detect instability.
- Every completeness-type statement is one of: `OBSERVED_VIOLATION` (a process was seen that breaks a rule), `NOT_OBSERVED_UNDER_REGIME(R)` (informational, with regime id, counts of unreadable and vanished entries, and the pid-set hash), or `UNKNOWN`. None of these is "absent".
- What a PASS may and may not say: it may say "no violation was observed under regime R"; it may **not** say "no hidden descendant exists" or "no residue exists", except for items covered by a *structural* proof (a gate-EPIPE proof for a never-released ticket; a pinned pidfd for a known identity; a guard-counted fork budget, which is itself only a Python-level count). Whether to allow any scoped negative statement in a PASS is open choice O-6; the default of this design is: required-for-safety items that would need an absence proof are UNKNOWN -> BLOCKED, and the summary lists the residual risk explicitly.
- `/proc/sys/kernel/ns_last_pid` deltas are at most a coarse indicator (other processes allocate pids, wraparound, namespaces) and are never evidence of absence.
- `scan_proc` problems, any unreadable `/proc/<pid>/fd` needed for GATE_HOLD_PROOF, and an unreadable `/proc` listing all make the dependent item UNKNOWN (BLOCKED if required).

## 4. Reaper design (F2) — two verifiable plans, no final choice

**Fact base (do not change under G2):** `node_main` never waits; `request_spawn` hard-codes it; the observer is not a subreaper and cannot wait for non-children; after a creator exits its children go to PID 1 (or a subreaper) where attribution is impossible.

**Reaper table (required for every node of every REAL card, filled before the run):** node id, role, expected parent (creator id), **lawful reaper** (exact node or observer), mechanism (`waitpid(pid, WNOHANG|0)` by specific pid, never `-1`), trigger (observer `GO_REAP` message or creator exit), deadline, evidence required (§3.3).

### Plan A — creator-owned reaping (feasible without touching Bench)
- G2 supplies its own creator entry `g2_creator_main`, started through the existing `Observer.spawn_direct(role, label, spec, entry, …)` (`observer.py:61-86`). The observer is its parent and its lawful reaper.
- The creator creates exactly the declared descendants through the ticket protocol (reusing frozen `node.request_spawn`, so descendants run `node_main`, or a G2 re-implementation — open choice O-12). A descendant created with `exit_after_ready` becomes a zombie that stays a zombie while the creator is alive and not waiting, which makes the ZOMBIE state stable and observable.
- Sequence: witness sees EXIT_OBSERVED (pidfd) -> ZOMBIE with `ppid == creator pid` -> observer sends `GO_REAP{node_id, pid}` over the creator socket (a message, not a signal) -> creator calls `waitpid(pid, 0)` for that pid only, records raw status or errno, reports `WAIT_REPORT` -> witness sees PROC_GONE, creator still alive and `SigIgn` SIGCHLD bit clear -> the judge may derive REAP_CONFIRMED.
- The creator then ends (message `EXIT` or socket EOF); the observer, its parent, applies the same sequence with its own `waitpid(creator_pid)` wrapper (a G2 wrapper recording raw status and errno; never the frozen `reap_direct`, whose ECHILD handling is excluded by R-F3-1/2).
- Verification gap, stated honestly: the creator's `WAIT_REPORT` is a claim. The corroboration is: pre-wait ZOMBIE with the creator as parent, PROC_GONE only after `GO_REAP`, creator alive and not ignoring SIGCHLD throughout, reported wait result names that pid. An independent wait witness does not exist without ptrace / audit; this limit is carried into the criteria (O-3).
- Orphans are **excluded** from the first REAL: the creator must reap every descendant before it exits. A crashed or early-exiting creator yields orphaned zombies under PID 1 -> R-F3-4 (BLOCKED, manual disposition). Existing scenarios E1A-d / E1A-e (deliberate orphans) are out of scope for G2 REAL.

### Plan B — observer as subreaper
- The observer sets `PR_SET_CHILD_SUBREAPER` before its first fork, so orphans reparent to the observer, which waits for them by specific (pid, starttime) after verifying the reparenting: ZOMBIE with `ppid == observer pid`, and an earlier KERNEL_PARENT record `== creator pid` (time-indexed lineage). It never waits with `-1`, and never for an identity that is not in the registered set.
- Verification: subreaper flag read back by an independent call (same process, so independence is weak, as in `sup_stub.my_prctl_get_subreaper`); adoption evidence from `/proc`; wait record from the observer itself (first-hand).
- Costs recorded, not decided: it changes the kernel behavior E1-A is about (`truth.py:64` requires subreaper unset), so G2 evidence would not transfer to E1-A; **any** orphan in the tree, including a bystander's child, is adopted and becomes an unreaped zombie owned by the observer that it must not `waitpid(-1)`; it needs a rule for adopted-but-unregistered zombies (residue + manual disposition).

**Decision status:** plan A, plan B, or A for the first REAL with B deferred is **OPEN (O-1)**; this document does not choose. No REAL card may run until the choice, its reaper table and its evidence rules are frozen and reviewed (DAC-05).

## 5. Experiment cards (F7) — SUT, truth provider, preventive vs detective

**Definitions.**
- **SUT-OBS:** the frozen observer ticket / registration path (`_on_ticket`, `_on_created`, `_register`, `release`), optionally wrapped by a G2 driver (O-2).
- **SUT-JUDGE:** the new G2 judge (pure function over sidecar + read-back registry + exit evidence).
- **SUT-GUARD:** the G2 runtime guard (§9).
- **Truth providers:** **TP-KERNEL** = witness reads of `/proc` / pidfd taken by G2 sampler code (not by `registry` / `observer` classification); **TP-FIXTURE** = synthetic ground truth authored *by hand in the fixture file* before and independently of the judge's output; **TP-NODE** = node claims (never truth).
- **Preventive requirement (P):** the observer/driver must refuse **before `R` is written**. **Detective requirement (D):** the judge must flag it **after the fact** from evidence. Because Bench is frozen, frozen `SUT-OBS` provides no prevention for CX-1/2/3 (§3.2); P is achievable only through a G2 driver that overrides `_register` using the existing `hold_release` parameter, verifies, then calls `release()` or `abort_held()` (open choice O-2). Where P is not available, the card can only demonstrate D, and the verdict text must say so.
- A mis-registered wrong pid is quarantined: never signalled, never waited, reported as residual until independently confirmed gone (§9).

| ID | Hypothesis / controlled input | SUT | Independent truth | P (before release) | D (after the fact) | Mode | Verdict boundary |
|---|---|---|---|---|---|---|---|
| G2-D01 | Released creator makes exactly one child through TICKET -> CREATED -> REGISTERED. | SUT-OBS (+driver), SUT-JUDGE | TP-KERNEL: pre-release KERNEL_PARENT, GATE_HOLD_PROOF; TP-FIXTURE for the expected tree | If driver (O-2): GATE_HOLD_PROOF present and uniqueness checked before `R`; else *not claimed* | `READY.fp.pid == registered pid`; registry / sidecar agree; no unregistered extra process observed | REAL candidate (after criteria freeze + separate authorization) | PASS: one declared child, lineage links all present, no violation observed under regime R. FAIL: positive evidence of wrong attribution. Any missing link / unreadable proof: BLOCKED. |
| G2-D02 | Same with `setsid` / `setpgid` after release (creator or child). | SUT-JUDGE (+observer) | TP-KERNEL time-indexed `sid` / `pgrp`, read after `READY` and compared with the pre-release values captured at `observer.py:118` | as D01 | attribution survives the expected change; membership never defined by sid/pgrp/ppid closure | REAL candidate | FAIL only if a registered true child is dropped or an outsider included on sid/pgrp grounds. Unverified history: BLOCKED. |
| G2-D03a | Wrong starttime in a reported identity. | SUT-JUDGE; SUT-OBS (existing `PidfdHandle` check) | TP-FIXTURE | refusal exists in frozen code (106-111) | judge rejects | CPU fixture | Accepting it as proven: FAIL. |
| G2-D03b | `CREATED` with foreign / unknown node id. | SUT-OBS (existing 278-280), SUT-JUDGE | TP-FIXTURE | frozen code records a problem (no register) | judge flags | CPU fixture | Accepted as descendant: FAIL. |
| G2-D03c (CX-1) | Creator reports the pid of a live non-ticket child (same parent). | SUT-JUDGE (+driver P) | TP-FIXTURE (REAL forbidden: it needs a deliberately misbehaving creator) | requires driver; frozen code does **not** refuse | judge must flag via missing GATE_HOLD_PROOF and `READY.fp.pid` mismatch | CPU fixture only | Judge accepts: FAIL. Frozen observer accepting it is the **documented, expected defect**, not a G2 PASS. |
| G2-D03d (CX-2) | Same (pid, starttime) registered twice. | SUT-JUDGE (+driver P) | TP-FIXTURE | requires driver | uniqueness check over ledger + sidecar | CPU fixture only | Accepted: FAIL. |
| G2-D03e | PID reuse / reused-pid starttime mismatch. | SUT-JUDGE | TP-FIXTURE (never forced on a live host) | frozen `PidfdHandle` order covers part | judge treats mismatch as identity unknown | CPU fixture only | Wrong identity accepted: FAIL; ambiguity: BLOCKED. |
| G2-D04 | Ticket revoked / late `CREATED` / unreported fork (CX-5). | SUT-OBS, SUT-JUDGE | TP-FIXTURE; gate EPIPE (structural) for never-released tickets | frozen code is fail-closed (282-294) | FORKED.pid of ticketed node labelled unverified; unresolved ticket -> BLOCKED | CPU fixture first; no real fault injection | PASS only with positive structural proof (EPIPE) or exact unresolved responsibility reported; guessing a pid or "clean" with unknown creator: FAIL; undecidable: BLOCKED. |
| G2-D05 | Sidecar or registry missing / torn / reordered / hash-chain broken; `/proc` unreadable; scan unstable. | SUT-JUDGE | TP-FIXTURE (intentionally altered files / injected read outcomes) | n/a | classification UNKNOWN / BLOCKED, never PASS, never a signal target | CPU fixture only | Fabricating a trusted identity: FAIL; everything else: BLOCKED. Real kernel disruption forbidden. |
| G2-D06 | Bystander with distinct verified identity, possibly in the same session; plus CX-4 shared control socket (spoofed sender). | SUT-JUDGE (+observer) | TP-FIXTURE (separate outside-truth record) | n/a | outsider is ignored: no signal, no wait, not in cleanup; messages treated as claims | CPU fixture only; real bystander **not authorized** | Action on an outsider: FAIL; outsider identity unprovable: BLOCKED. |
| G2-D07 | Lifecycle states: exit, zombie, lawful reap, disappearance (§3.3, §4). | SUT-JUDGE (+plan A or B creator/observer) | TP-KERNEL (pidfd, `/proc` state, ppid, SigIgn) + TP-FIXTURE for pure cases | n/a (reaping is not release) | all four states kept apart; `WAIT_ECHILD`, zombie-as-dead, readable pidfd never produce REAP_CONFIRMED | CPU fixture first; REAL only after O-1 is decided | A state skipped or `DEAD` accepted as reap: FAIL; evidence missing / reaper unattributable: BLOCKED. |
| G2-D08 (CX-3) | Shared gate fd (second holder of the read end). | SUT-JUDGE (+driver P) | TP-FIXTURE (REAL forbidden) | requires driver to count holders before `R` | holder count > 1, or recipient of `R` unknown | CPU fixture only | Judge says single recipient: FAIL; holder enumeration incomplete: BLOCKED. |
| G2-D09 (CX-6) | `RELEASED` recorded, delivery unconfirmed. | SUT-JUDGE | TP-FIXTURE | n/a | requires `FIRST_ACTION` evidence for delivery | CPU fixture only | Treating RELEASED as delivery: FAIL. |
| G2-D10 | Signal-free exit, guard traps, anomaly stop and manual disposition (§9). | SUT-GUARD | TP-FIXTURE (trap hits) + in a REAL run TP-KERNEL (non-signal wait status of the creator; creator-reported statuses of descendants are claims) | n/a | every trap hit and every non-clean status is recorded | CPU fixture; REAL as part of D01/D02/D07 | A signal call executed: FAIL; guard not installed / unverifiable: BLOCKED. |

One variable per card. A REAL card never contains a forged claim, a misbehaving creator, a bystander or a fault injection; those are CPU-fixture-only in this design.

## 6. Acceptance conditions (F9; still proposals, not frozen G2-Cxx)

- **DAC-01 scope:** source baseline and branch pinned; no edit of Bench, G0 / G1 frozen files, R3, Parcae or architecture.
- **DAC-02 truth:** identity, parent-at-time, gate hold, lineage, exit, zombie, reap and disappearance remain separate (§3); a judge never reuses the candidate's own decision as truth; POST_RELEASE evidence never supports pre-release safety.
- **DAC-03 safety:** zero signals *enforced by a runtime guard* (§9), not merely absent from the steps; no use of `finish_cleanup`, `final_cleanup`, `run_cleanup_full`, `e1a_runner`, `trial._cleanup`, janitor.
- **DAC-04 completeness of each card:** goal, environment, controlled input, SUT, truth provider, P and D requirements, FAIL witness, BLOCKED witness, safety stop, preserved evidence (table in §5).
- **DAC-05 reaping:** reaper table filled and plan A/B decided and reviewed before any REAL descendant; every wait is by specific pid; no `-1`.
- **DAC-06 completeness claims:** no absence claim without a structural proof (§3.5); unprovable required items -> BLOCKED.
- **DAC-07 stages:** criteria freeze, implementation, CPU suite, REAL authorization, REAL run and cross-review are separate (§8). A G1 authorization never authorizes G2.
- **DAC-08 disagreements:** reviewer disagreements stay OPEN and are resolved by a proposed minimal controlled experiment, not by electing one reviewer.

**Verdict policy (proposed).** Per card: FAIL only on *positive evidence* of a violation or of a wrong acceptance; anything undecidable, missing, unreadable or unattributable is BLOCKED (never FAIL, never PASS). Precedence **FAIL > BLOCKED > PASS** at card and run level. A run PASS needs every planned card executed and PASS; a card not run after an earlier non-PASS is `NOT_RUN` and, if everything executed passed, makes the run BLOCKED (incomplete). Damaged evidence is UNEVALUABLE (BLOCKED). Exit code 0 alone, or a pass by the run's own judge alone, never counts; read-back, hash-verified evidence plus a closure marker is required (as in G1). A CPU PASS is never a REAL PASS.

## 7. Evidence layout (for later freezing; no files are generated now)

Own closed schemas and hashes, frozen before implementation: execution HEAD; G2 authorization id and bindings (including the chosen reaper plan, the process budget and the guard version); run id; node table with expected parent and lawful reaper; writer-ledger and read-back hashes; **sidecar with hash chain** (§3.4); kernel snapshots with `boot_id` and pidns; pre-release / post-release classification per node; GATE_HOLD results with regime ids; the four lifecycle states per process with times; observer wait calls with raw status or errno; guard events (signal attempts must be zero); every STOP_RULE event; residual and manual-disposition records; scan regimes with unreadable and vanished counters; evidence / summary / closure marker bound by SHA-256 and byte length. G1 C01–C17 are not reused as G2 criteria.

## 8. Process budget and stage boundaries (F9)

**Process budget (proposed; numbers are open choice O-8).** Parent + descendant are concurrently alive by design (a ticket requires a RELEASED creator), so "no concurrent children" is replaced by explicit limits, enforced by the guard and counted in evidence: depth <= 2 (observer -> creator -> descendant), **total forks <= 2 per card** (creator by the observer, one descendant by the creator), **max live nodes <= 2**, **max descendants per creator = 1** in D01/D02/D07, no grandchildren, **0 signals**, 0 janitor, no fault injection. Timers: bench constants `T_GATE_MAX = 10 s`, `T_REG_MAX = 5 s`, `T_NODE_MAX = 120 s` (fail-safe, not the plan); G2 per-phase deadlines and a total run budget shorter than `T_NODE_MAX` (proposal: <= 60 s; open O-13).

**Stages.**
| Stage | Content | Needs |
|---|---|---|
| S0 | Design draft and cross-review (this document). | none |
| S1 | Freeze G2 criteria V1 (own hashes) after open choices O-1…O-14 are decided. | separate owner approval |
| S2 | Implement `gate_g2/` code (judge, sidecar writer, guard, optional driver) + static audit. | separate owner approval |
| S3 | **CPU-only:** pure fixtures and unit tests under a process-safety sentinel (no `fork`, no `exec`, no subprocess, no signal, no wait): D03a–e, D04–D06, D08–D10, pure parts of D07. At most the runs the owner permits. | separate owner approval; must run before any authorization file exists |
| S4 | Cross-review of S3 evidence; owner decision. | owner |
| S5 | G2-specific authorization (`e1a-gate-auth-g2-1`, proposed): own bindings, grants (forks, max live, depth, signals 0, reaper plan, no fault injection, expiry), single use, never committed. | owner |
| S6 | **REAL:** one run of D01, D02 and D07 (single or separate runs: O-9). Real processes only for honest creators; no forged claim, no bystander, no fault. | S5 |
| S7 | Evidence cross-review, then owner decision. G3 / BV / E1-A are not entered automatically. | owner |

CPU-only never creates a live process; REAL never contains a card marked "CPU fixture only".

## 9. Safe exit, reaping and exception handling (F8) — no original SIGKILL path

**SX0 Guard (installed before the first fork, verified, recorded).** Python-level traps that raise and record on: `os.kill`, `os.killpg`, `signal.pidfd_send_signal`, `PidfdHandle.send`, `Observer.kill_registered`, `Observer.kill_unregistered_direct`, `Observer.finish_cleanup`, `Observer.final_cleanup`, `Observer.finish_trial_cleanup`, `janitor.run_cleanup*` / janitor start, `subprocess`, `exec*`, `spawn*`, `system`, `popen`, `os.waitpid(-1, …)`, `os.wait*` other than the G2 wait wrapper; fork only through `gate.fork_gated` within the budget. As in G1, a Python-level trap is **not** proof that no kernel path exists. Allowed non-signal operations: `proto.send_msg` (including `GO_REAP`, `EXIT`), closing sockets (EOF), `close_intake()` (revokes tickets by writing the gate abort byte `A`), `abort_held()`, gate probes.

**No janitor, no `e1a_runner`.** No janitor process is started (it can SIGKILL autonomously); the `finally` of `e1a_runner.py:319`, `trial._cleanup` and `run_e1a.sh` are never used. The price — no automatic recovery — is paid by the manual-disposition flow below and by short budgets.

**SX1 Normal sequence (plan A shown; plan B changes only the reaper).** (1) descendants end by their own design (`exit_after_ready`, or a message `EXIT`); (2) witness records EXIT_OBSERVED and ZOMBIE; (3) `GO_REAP`, creator's specific-pid wait, PROC_GONE (§4); (4) creator told to end (`EXIT` / EOF); observer waits by specific pid for the creator with the G2 wrapper; (5) sockets closed, final scans (regime ids recorded), sidecar closed, evidence saved, read back, judged, closed.

**SX2 Anomaly stop rule.** Triggers: guard hit, identity mismatch, claim that fails cross-check, a live process outside the node table seen in the tree, deadline exceeded, enumeration unknown for a required item, sidecar torn / chain broken, unexpected exit status, a crashed creator. Actions in order, all non-signal: stop creating (no new fork), `close_intake()`, send `EXIT` to nodes that can still read it, then close their sockets so that every `node_main` self-terminates by EOF, wait a bounded settle time (shorter than `T_NODE_MAX`), take final snapshots; for each identity record EXIT_OBSERVED / ZOMBIE / PROC_GONE / still alive; judge on what was saved.

**SX3 Manual disposition.** If any identity is not confirmed gone, or a zombie is not reapable by the observer (non-child, PID 1), or a quarantined mis-registered pid exists: write `MANUAL_DISPOSITION_REQUIRED.json` listing every identity (pid, starttime, last state, last ppid, lawful reaper, last observation time), why each is unconfirmed, what was **not** done (no signal, no wait for non-children, no cleanup by name or token), and the evidence hashes; the verdict is BLOCKED. A human may act outside G2; G2 never signals, never `waitpid(-1)`, never matches by name.

**SX4 What stays out.** `mark_dead` may be called by a driver if it is needed to close sockets, but its `DEAD` records are non-evidence (R-F3-1). A creator that hangs lives at most until `T_NODE_MAX` by its own fail-safe, which is why the real run's creator entry must carry its own, shorter, deadline.

## 10. Risk register (F1–F9 mapped; V0 R01–R08 updated)

| Ref | Risk | Disposition in V1 |
|---|---|---|
| G2-R01 | No lawful waiter for descendants. | Design-resolved to two verifiable plans (§4); **choice OPEN (O-1)**; REAL blocked until frozen. |
| G2-R02 | Current `ppid` loses history after reparenting. | Time-indexed evidence (§3.1, §3.3); orphans excluded from first REAL; **OPEN** for plan B. |
| G2-R03 | SIGKILL-capable cleanup / janitor. | Guard, no janitor, no runner, safe-exit flow (§9); **enforcement design present, implementation OPEN**. |
| G2-R04 | Ticket INTENT / late CREATED / EPIPE. | CX-5, D04; structural EPIPE proof kept; ledger FORKED.pid labelled unverified. |
| G2-R05 | Witness independence, `/proc` completeness. | Sidecar (§3.4) and no-absence rule (§3.5); same-process independence limit stated; **OPEN (O-3, O-6)**. |
| G2-R06 | PID reuse / bystander hazards on live hosts. | Fixture-only; REAL honest creators only. |
| G2-R07 | R3 naming collisions. | Isolated; no R3 / CA / CB decision. |
| G2-R08 | Source inventory / thresholds unfrozen. | Inventory updated (§2); numbers OPEN (O-8, O-13). |
| G2-R09 | Reported pid not bound to ticket / gate (F1). | CX-1/2/3; GATE_HOLD_PROOF; preventive tier needs a driver (**O-2**). |
| G2-R10 | Zombie / ECHILD / DEAD taken as reaped (F3). | §3.3 R-F3-1…4. |
| G2-R11 | Socket-possession identity; ledger cannot hold lifecycle events (F4, F5). | §3.4 sidecar; claims-only messages; **O-11**. |
| G2-R12 | Budget and verdict structure (F9). | §6, §8; numbers OPEN. |

## 11. Open design choices (all remain OPEN; nothing here is decided)

- **O-1** Reaper: plan A, plan B, or A first and B later (§4).
- **O-2** Preventive tier: G2 driver overriding `_register` (via `hold_release`) to verify GATE_HOLD_PROOF / uniqueness before `release()`, versus detective-only (changes what is tested; V1 criteria wording depends on it).
- **O-3** Witness form: same-process sampler, separate witness process, or post-hoc only; and the accepted attribution strength of creator wait reports.
- **O-4** Capturing raw claims: log-then-delegate subclass of `_on_created` / `_on_ticket`, or wrapper of `proto.recv_msg`.
- **O-5** GATE_HOLD enumeration scope, permission failures, handling of unreadable `/proc/*/fd`.
- **O-6** Whether any scoped negative statement ("no violation observed under regime R") may appear in a PASS, and the exact wording of the residual-risk statement.
- **O-7** Sidecar details: hash-chain format, fsync policy, size limits.
- **O-8** Numeric process budget and timers.
- **O-9** One REAL run for D01+D02+D07 or separate authorizations.
- **O-10** Orphan handling: excluded from first REAL (default) or admitted with a verified PID 1 reaper.
- **O-11** Per-message credentials need a Bench change: accepted as out of scope (claims-only) or a separately authorized Bench revision (would change frozen hashes).
- **O-12** Descendants via frozen `node.request_spawn` or a G2 creator-side re-implementation.
- **O-13** Total run budget versus `T_NODE_MAX = 120 s`.
- **O-14** Whether CX-3 (shared gate fd) can be exercised for real at all (default: fixture only).
- **O-15** How G2 and E1-A relate if plan B is chosen (evidence transfer).

## 12. Stage result and the only next step

Documents only. Source re-read at baseline: **RECORDED**. F1–F9 handled in design text: **PREPARED** (resolution table in `G2_DESIGN_REVISION_001_RECORD.md`). Criteria: **NOT FROZEN**. Implementation, CPU tests, REAL: **NOT AUTHORIZED / NOT TESTED**.

**Only next step:** submit this revision (V1) to **ChatGPT and Grok** for independent design review; record specific disagreements and the decisions O-1…O-15; do not implement, test, fork, signal, change Bench or enter G3 / BV / E1-A without a distinct owner authorization.
