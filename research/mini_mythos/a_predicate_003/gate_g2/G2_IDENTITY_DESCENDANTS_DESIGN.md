# E1-A Gate G2 — process identity, descendant lineage and observation safety (DESIGN DRAFT V0)

**Task:** `F3B-D1-A-CPU-003-E1A-G2-DESIGN-001`  
**Date:** 2026-10-28  
**Scope:** DOCUMENT / SOURCE AUDIT ONLY. **G2 DESIGN PREPARED, NOT FROZEN, NOT IMPLEMENTED, CPU TESTS NOT TESTED, REAL G2 NOT AUTHORIZED.**  
**Starting repository evidence HEAD:** `450914367c247231c51be02e13775cb001e69c5d`, following the accepted G1 REAL-001 result.  
**Status boundary:** G1 here means E1-A negative gate; **do not confuse** this G2 with archived R3-A liveness-predicate “G1/G2 FAIL” or with later BV / E1-A experimental cells.

## 1. Why G2 is necessary

G0 checked a valid release in one controlled child, and G1 checked the four *negative* gate paths. Neither establishes that a released parent’s **ticketed children and descendants** are correctly attributed across `setsid` / `setpgid`, process exit and reparenting, or that an unrecognized process cannot be sent a signal/reaped by mistake.

**Proposed G2 research question:** Can the observer distinguish the authorized tree from outsiders and uncertain children using durable creation lineage plus kernel identity facts, without inventing a child, losing an unresolved child, or claiming cleanup success without trustworthy exit/reap evidence?

**Not in scope:** G3 crash recovery or fault injection; BV validity tests; E1-A candidate A/B performance or quality; architecture changes; model training; real data download; process-group cleanup or signal sends. A G2 design approval is not a runtime authorization.

## 2. Source audit — observed current code, not proposals

Paths below are relative to `research/mini_mythos/a_predicate_003/`. Read-only audit against the pinned source HEAD:

| Source | Present mechanism / fact | Open design risk or limitation |
|---|---|---|
| `bench/gate.py::fork_gated,gate_wait` | Child is gated until the release byte or a negative/timeout exit; child hygiene is performed before entry. | A gate alone does not attest descendant lineage or independent reaper ownership. |
| `bench/observer.py::spawn_direct,_note_forked,_register` | Parent INTENT → FORKED → REGISTERED, snapshot of `pid/starttime/ppid/sid/pgrp` before release, `PidfdHandle` identity check. | Real PID/starttime alone is not a parent/descendant proof; identity observation has races. |
| `bench/observer.py::_on_ticket,_on_created` | Released node requests a ticket; observer issues a gated child descriptor and later handles a CREATION report; ticket is bound to creator node id. | Ticket issued but CREATED missing, late CREATED, forged/foreign node id, denied ticket or creator exit require separate judgments. |
| `bench/node.py::request_spawn,node_main` | A released parent may create its child through TICKET/CREATED/REGISTERED; `node_main` supports `setsid`, `setpgid`, `children`, `exit_after_ready`. | `request_spawn` creates descendants but does not itself provide a recorded `waitpid` for each child. Real-case reaping responsibility must be explicit before running. |
| `bench/common.py::scan_proc,children_of,descendants_of,fingerprint` | Whole-`/proc` enumeration, current `ppid` ancestry, `pid/starttime` plus session/group snapshot. | Current `ppid` can change after reparenting; partial enumeration is not an empty tree; `sid/pgrp` mismatches do not disprove lineage. |
| `bench/common.py::PidfdHandle,process_is_dead` | pidfd pins one identity/lifecycle; comments explicitly say it says **nothing** about lineage; dead includes Z or reaped. | A pidfd-readable zombie must not be counted as confirmed `waitpid` ownership/reap; PID reuse and identity-unknown paths cannot be guessed away. |
| `bench/registry.py::RegWriter,parse_reg,integrity_issues,fold,cleanup_targets,unresolved_forked,unresolved_tickets` | Durable event ledger records node id / creator / PID and identifies unresolved FORKED and tickets. Corruption, torn tail and sequence gaps have explicit findings. | Durable fidelity and missing lifecycle records must be checked independently; `INTENT` alone does not establish that a child was forked. |
| `bench/observer.py::close_intake,_abort,_probe_gate,verify_run_set,final_cleanup` | Closing intake revokes outstanding tickets, EPIPE may prove no gate reader, final cleanup verifies the run-set. | `finish_cleanup` and `final_cleanup` call SIGKILL-capable helpers while live; not safe as a default for an unapproved G2 run. |
| `bench/janitor.py::run_cleanup_full,reg_integrity,unresolved_report,decide` | Janitor acts only on complete REGISTERED candidates and verifies pidfd/starttime; unresolved unregistered entries are reported without signalling. | `run_cleanup_full` may send SIGKILL to registered targets; real G2 must not invoke it without a separate signal/fault authorization. |
| `bench/truth.py::kernel_defects,topology_reasons,bystander_reasons` | Outside-candidate observations of topology and bystander conditions already exist. | Candidate/observer and external-truth evidence must remain independent; a single snapshot of current ancestry is insufficient for historical lineage. |
| `bench/validity.py::bv2,bv6,bv7` | Existing BV design touches observer death, wrong-identity janitor and torn registry. | These are **BV**, some inject death or signals; **do not execute or relabel them as G2 PASS**. |
| Prior R3 CPU-001/002 checkpoints | Previously observed that zombies complicate killpg/live classification, A/B cleanup strategies do not have a settled winner, and an omitted reaper can leave zombies. | Do not choose CA/CB or edit frozen R3 based on this G2 document. |

This is a source-grounded audit of available methods, **not** proof that an as-yet-unwritten G2 protocol satisfies any property.

## 3. Proposed independent-truth model (not yet frozen)

- **Identity = (pid, starttime)** cross-checked with a pinned pidfd, with explicit observation times. Only the described process identity follows; this does not prove lineage.
- **Lineage = independently witnessed creation chain:** creator identity + ticket issuance + fork/CREATED evidence + registration + a consistent parent-child link observed at a valid time. A `sid` / `pgrp` transition may be expected and must not erase a proven relationship.
- **Current kernel tree = time-bounded observation, not eternal truth:** `/proc` `ppid` ancestry is a snapshot; monitor reparenting, short-lived children, and incomplete enumeration.
- **Separate observers:** (A) persistent writer ledger; (B) the kernel evidence recorded by a read-only witness that does not call the tested identity classifier; (C) the candidate decision itself. A test must not use candidate output as its ground truth.
- **Uncertainty:** missing CREATED, changed PID identity, non-enumerable `/proc`, missing ledger records, uncertain reparenting, or unclear reaper ownership => `UNKNOWN / BLOCKED`, never PASS and never a signal target.
- **Reaper ownership:** distinguish “exit observed”, “zombie still exists”, “specific parent/reaper performed wait”, and “process disappeared”. The observer must not `waitpid` an indirect child it never parented. Never infer successful reap from `ECHILD` or pidfd readability alone.
- **Bystanders:** deliberate outsiders require an independently proven identity and out-of-scope relationship; they may be observed, but must not be signalled, waited, or included in cleanup.

## 4. Minimal controlled experiment cards (PROPOSED ONLY, no execution authorization)

| ID | Research hypothesis / intended input | Independent observable truth | Expected result / verdict boundary |
|---|---|---|---|
| G2-D01 | Released parent creates exactly one child through a valid TICKET → CREATED → REGISTERED chain. | Creation chain in writer ledger, read-back registry, kernel fingerprints and independently observed parent-child relation at creation. | PASS if one declared child is linked to the right creator and there are no outsider inclusions; proved wrong identity/lineage => FAIL; any missing required evidence => BLOCKED. |
| G2-D02 | Same chain with child or parent changing `sid`/`pgrp` via `setsid` or `setpgid` after release. | Identity + witnessed creation history, current `sid/pgrp` as separate fields. | PASS if attribution survives the expected session/group change; dropping true child based solely on changed SID/PGID => FAIL; unverified history => BLOCKED. |
| G2-D03 | Synthetic wrong-starttime, forged CREATED, reused PID or foreign node-id reports (CPU fixtures first). | Frozen synthetic independent identity, forged candidate input, ledger owner. | PASS if wrong/foreign identity is rejected with zero signal/wait; accepting it as a proven descendant => FAIL; unresolvable ambiguity => BLOCKED. Do **not** force real PID reuse. |
| G2-D04 | Ticket issued and revoked before CREATED; delayed CREATED; no-reported-fork path (CPU simulation first). | Ticket history, gate holder/reader closure and EPIPE observation, delayed report timing. | PASS only with positive absence/exit proof, or accurate unresolved responsibility; guessing pid or claiming clean despite unknown creator => FAIL/BLOCKED per evidence. No real fault injection yet. |
| G2-D05 | Synthetic missing, torn, reordered registry lines or inaccessible `/proc` snapshots. | Independent intentionally altered file/read outcome. | PASS if classifier returns UNKNOWN/BLOCKED and prevents cleanup PASS or signalling; fabricated trustworthy identity => FAIL. Real kernel disruption forbidden. |
| G2-D06 | A bystander process with a distinct verified identity, possibly in the same session; synthetic first. | Separate outside-truth record proving it is not a registered descendant. | PASS if ignored and neither signalled nor waited; action on outsider => FAIL; inability to prove outsider identity => BLOCKED. **Real bystander run is not authorized**. |
| G2-D07 | Legitimate descendant exits, becomes Z, is reaped by its lawful reaper (pure simulation first). | Exact creator-reaper wait record, Z-before-wait, /proc disappearance, no other reaper consuming state. | PASS only if “exited” and “reaped” are distinct and correctly proven; zombie or `ECHILD` incorrectly marked reaped => FAIL/BLOCKED. No live case until the reaper design is approved. |

These are **candidate test cards**, not frozen tests or promises of functionality. One variable per card; forbid concurrent children until a deliberately justified later study.

## 5. Proposed design acceptance conditions (not frozen G2-Cxx)

- **DAC-01 scope:** source provenance and branch pinned, no modification of upstream, G0/G1 frozen files, Bench, R3, Parcae, or model architecture.
- **DAC-02 truth:** identity, lineage, current kernel topology and reaping facts remain distinct. Independent ground truth must not reuse the candidate’s own decision.
- **DAC-03 safety:** no signal, process-group operation, automatic kill, fault injection, outsider disturbance, or unsafe cleanup hidden in proposed steps.
- **DAC-04 completeness:** every proposed case identifies goal, environment, controlled input, expected observable result, FAIL witness, BLOCKED/UNKNOWN witness, safety stop and evidence to preserve.
- **DAC-05 reaping:** an explicit lawful reaper and bounded no-residue strategy must be designed and reviewed **before any real descendant run**; one parent/one descendant still needs an owner for each `waitpid`.
- **DAC-06 versioning:** separate future G2 criteria freeze, code implementation, CPU-only suite, real execution, and evidence cross-review. G1 authorizations cannot authorize G2.
- **DAC-07 disagreements:** ChatGPT and Grok disagreements remain OPEN and are resolved by a proposed minimal controlled experiment, **not** by electing one AI as authority.

Design-review decision `PASS` means the **draft covers these considerations**, not that G2 code/CPU/REAL passed. If any actual process-reaping safety design is unresolved, the **G2 REAL gate remains BLOCKED / NOT AUTHORIZED** even if the document itself is acceptable.

## 6. Evidence layout proposal (for later review; no files generated)

Future criteria should define their own closed schema and frozen hashes before implementation. Candidate evidence fields: execution HEAD; own authorization ID and binding; run_id; creator/child IDs; ticket ID; writer-ledger and read-back hashes; time-ordered INTENT/FORKED/CREATED/REGISTERED/RELEASED/EXIT/DEAD; kernel (pid,starttime,ppid,sid,pgrp,state) snapshots; separate external truth; pidfd identity/liveness; exact waitpid owner and outcome; /proc-disappearance proof; signal attempts (must be zero in initial non-signal experiments); bystander identity and untouched state; UNKNOWN/blocked reasons; process-tree residual; deterministic evidence/summary/closeout binding; checkpoint and source SHA. Every absence claim requires a bounded, complete observation regime; lack of evidence does not become a negative fact.

Do not reuse the G1 C01–C17 as if they were automatically valid G2 criteria. Propose and review G2-specific checks, then freeze a new `gate_g2` V1 **only after separate owner approval**. Do not create an execution authorization in the design stage.

## 7. Risks and unresolved design decisions

| Ref | Question / risk | Provisional disposition |
|---|---|---|
| G2-R01 | Current `node_main/request_spawn` does not show reliable descendant reaping evidence at the creator; child `exit_after_ready` might be a zombie until creator exits. | **OPEN**: design creator-owned reaper or independent lawful reaper with unambiguous ownership. No real G2 until resolved. |
| G2-R02 | Current-/proc ancestry loses reparented children. | **OPEN**: define time-indexed creation/truth and scoped completeness; never claim exhaustive history from one snapshot. |
| G2-R03 | Observer `finish_cleanup/final_cleanup` and Janitor `run_cleanup_full` can SIGKILL. | **RESTRICTED**: initial G2 REAL must be non-signal and cannot rely on live-child cleanup; any fault-injecting scenario needs a distinct authorization, not implicit from G2 design. |
| G2-R04 | Ticket INTENT / late CREATED / `_probe_gate` may be unresolved. | **OPEN**: define proof obligations for unreported fork and EPIPE; simulation first. |
| G2-R05 | Witness independence and `/proc` partial enumeration. | **OPEN**: design external read-only truth, ensure UNKNOWN/BLOCKED rather than false PASS. |
| G2-R06 | PID reuse, wrong-starttime, bystander scenarios create safety hazards if forced on live systems. | **RESTRICTED**: CPU fixtures first; never manipulate unrelated host processes. |
| G2-R07 | Historical R3 A/B variants and G2 naming collisions. | **ISOLATED**: keep archived R3 statuses intact; no architecture/cleanup algorithm decision from G2. |
| G2-R08 | Exact G2 source inventory and proposed thresholds have not yet been frozen or cross-reviewed. | **OPEN**: independent ChatGPT/Grok design review, reconcile to source inventory and choose minimum safe subset before owner decision. |

## 8. Stage result and unique next instruction

**Stage self-assessment (documents only):**
- Source read-only review: **RECORDED** (paths and functions above).
- Proposed questions, cases and safety boundaries: **DRAFTED**.
- Git/source-change scope check: to be recorded in the stage checkpoint on commit.
- G2 criteria frozen: **NOT TESTED / NOT AUTHORIZED**.
- G2 implementation: **NOT TESTED / NOT AUTHORIZED**.
- G2 CPU tests: **NOT TESTED / NOT AUTHORIZED**.
- G2 REAL: **NOT TESTED / NOT AUTHORIZED**.

**Only next step:** submit this G2 source audit and proposed design to **ChatGPT and Grok independently**, collect specific source-grounded disagreement and unresolved reaping safety questions, and record a design-review checkpoint. Do **not** implement, test, signal, fork, alter Bench/upstream, or automatically authorize any later gate.
