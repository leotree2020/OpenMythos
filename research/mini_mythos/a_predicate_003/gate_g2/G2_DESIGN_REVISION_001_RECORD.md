# G2-DESIGN-REVISION-001 — revision record

**Task:** `F3B-D1-A-CPU-003-E1A-G2-DESIGN-REVISION-001` (DOCUMENTATION ONLY).  
**Base:** `8f9e8b2c027b3f6c0b738650b57af62d52dce141` (V0 draft + G2-DESIGN-001 review **CHANGES REQUIRED**).  
**Result:** **G2 DESIGN REVISION PREPARED — CROSS-REVIEW PENDING. G2 CRITERIA NOT FROZEN. G2 CPU / REAL NOT AUTHORIZED.**  
**Files:** revised draft `G2_IDENTITY_DESCENDANTS_DESIGN.md` (V1); archived V0 `G2_IDENTITY_DESCENDANTS_DESIGN_V0_8f9e8b2.md` (byte-identical to the base blob except one leading HTML comment line); original review `G2_DESIGN_REVIEW_001_FINDINGS.md` (F1–F9 preserved, never edited by revisions); this record.  
"Addressed in design" means the draft now contains a specification that a reviewer can attack; it does **not** mean the property holds, was tested, or is frozen.

## Finding-by-finding disposition

| Finding | Requested revision | Where in V1 | Status |
|---|---|---|---|
| F1 pid not bound to ticket / gate | Separate claimed PID, kernel identity, gate-hold proof, true creation lineage; add same-parent wrong PID, duplicate PID, shared gate fd counterexamples; READY after release must not prove pre-release verification. | §3.1 (layers table, PRE/POST_RELEASE cutoff rule), §3.2 (CX-1 same-parent wrong PID, CX-2 duplicate PID, CX-3 shared gate fd, CX-4…6), §5 cards D03c / D03d / D08. | Addressed in design. **OPEN:** whether a preventive tier exists at all (O-2), holder enumeration scope (O-5), whether CX-3 is ever REAL (O-14). |
| F2 no lawful descendant reaper | Verifiable plan A / B, no final choice; state that `node_main` does not reap. | §2 (rows `node.py`, `sup_stub.py`, `reap_direct`), §4 (reaper table, plan A creator-owned, plan B observer subreaper, costs, verification gaps). | Addressed in design. **OPEN:** O-1 choice, O-3 attribution strength, O-10 orphans, O-12, O-15. |
| F3 DEAD / ECHILD / pidfd as reap | Separate EXIT_OBSERVED, ZOMBIE, REAP_CONFIRMED, PROC_GONE; DEAD, ECHILD, pidfd readable never alone prove reaping. | §3.3 (state table, R-F3-1…4), §2 (`reap_direct`, `_confirmed_dead`, `mark_dead` rows), D07. | Addressed in design. |
| F4 socket credentials | State limits. | §3.4 F4 paragraph (claims-only messages, `SO_PEERCRED` expected useless on an observer-created socketpair — marked *not verified*, `SCM_CREDENTIALS` needs a Bench change), CX-4, D06. | Addressed in design. **OPEN:** O-11. |
| F5 ledger cannot record CREATED / EXIT / REAPED | State fact; design isolated sidecar. | §3.4 (hash-chained append-only `g2_sidecar.jsonl`, raw observations only, independence statement), §7. | Addressed in design. **OPEN:** O-3, O-4, O-7. |
| F6 enumeration | Delete "two stable scans suffice"; unprovable completeness stays UNKNOWN / BLOCKED. | §3.5 (withdrawn, three-valued completeness statements, PASS wording limits, `ns_last_pid` only coarse), DAC-06, §6 verdict policy. | Addressed in design. **OPEN:** O-6 (whether any scoped negative statement may appear in a PASS). |
| F7 SUT / truth provider | Per card: SUT, independent truth provider, preventive and detective requirements. | §5 (definitions + 10-card table). | Addressed in design. **OPEN:** O-2 decides whether P columns are achievable. |
| F8 no SIGKILL cleanup path | Safe exit, reaping, exception / manual disposition without the original SIGKILL paths. | §9 (SX0 guard, no janitor / runner, SX1 normal, SX2 stop rule, SX3 `MANUAL_DISPOSITION_REQUIRED.json`, SX4), D10. | Addressed in design; guard is Python-level (limit stated). **OPEN:** implementation, O-13. |
| F9 budget, precedence, stages | Process budget, verdict precedence, CPU-only vs REAL boundary, all open choices. | §6 (verdict policy FAIL > BLOCKED > PASS; FAIL only on positive evidence), §8 (budget, stages S0–S7), §11 (O-1…O-15). | Addressed in design. Numbers **OPEN** (O-8, O-9, O-13). |

## Decision differences preserved

1. **Reviewer F1 suggestion (2) corrected.** The original review text listed "node self-reported `READY.fp.pid` equals the registered pid" next to the pre-release checks. READY is sent *after* release, so it cannot prove pre-release safety. V1 reclassifies it as a **mandatory detective** check (§3.1 rule, §5). This is a change of the reviewer's own text, recorded here rather than rewritten in `G2_DESIGN_REVIEW_001_FINDINGS.md`.
2. **Reviewer F6 suggestion withdrawn.** "At least two scans with stable pid set" was offered as a way to support absence claims. V1 withdraws it as sufficient evidence (it can only find violations); the original text stays in the findings file with a revision note.
3. **Reviewer F2 preference for plan A is not adopted.** The review leaned to A and advised against B; per this task's instruction V1 specifies both verifiably and leaves the choice OPEN (O-1).
4. **New observation in V1, not in the review:** `Observer._register` already has a `hold_release` parameter (`observer.py:103,124`), so a G2 driver subclass can create a hold point without editing Bench. Whether to use it changes what is tested, so it is open choice O-2, not a decision. Likewise the fact that `fork_gated` closes `gate_r` after release (`gate.py:77`) means gate-hold evidence can only be collected before release.
5. No ChatGPT or Grok design-review disagreement has been supplied yet; none is recorded. The open choices O-1…O-15 are the points to be decided by the next review round and the owner, not by electing one AI.

## OPEN issues (summary; full list in V1 §11)

O-1 reaper plan; O-2 preventive driver vs detective-only; O-3 witness form and attribution strength; O-4 raw-claim capture; O-5 gate-holder enumeration; O-6 scoped negative claims; O-7 sidecar details; O-8 process budget numbers; O-9 single vs separate REAL runs; O-10 orphans; O-11 per-message credentials (Bench change); O-12 descendant spawn path; O-13 total budget vs `T_NODE_MAX`; O-14 CX-3 real feasibility; O-15 G2/E1-A transfer under plan B.

## Not changed / not done

No change to `bench/`, `gate_g0/`, `gate_g1/`, prereg, R3, Parcae, model, tests, tools or any evidence directory. No G2 code, no CPU test, no process, no signal, no authorization file, no GPU. The G2 criteria are not frozen and no G2 CPU / REAL PASS exists.

## Only next instruction

Submit V1 (`G2_IDENTITY_DESCENDANTS_DESIGN.md`) with this record to **ChatGPT and Grok** for independent design review; record disagreements and the decisions O-1…O-15. Do **not** implement, test, fork, signal, freeze criteria, change Bench or enter G3 / BV / E1-A.
