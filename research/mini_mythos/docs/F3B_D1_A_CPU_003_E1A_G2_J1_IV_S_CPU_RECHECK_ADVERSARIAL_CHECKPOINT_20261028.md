# J1 IV-S CPU source replay + adversarial additions — CHECKPOINT (2026-10-28)

**Stage:** `F3B-D1-A-CPU-003-E1A-G2-J1-IVS-CPU-RECHECK-NEGATIVE-CONTROLS-001`.
**Actual result:** 23 pinned-byte-matched original CPU tests PASS; 10 new independent-helper adversarial tests PASS; **33/33 local nonformal CPU unit PASS** (0 failures/errors). **External independent code review PENDING**. Formal 18-case acceptance **NOT TESTED**. Oracle `BLOCKED/NOT_READY`, `FORMAL_ACCEPTANCE_READY=False`; G2 REAL `BLOCKED`; Grok `DEFERRED`; criteria NOT FROZEN.

## Git

- Repository `leotree2020/OpenMythos`.
- Base `5c3a14b45322da4ca4d748477789e9ebc30158a3`, `d1-r3-a-cpu-003-e1a-g2-j1-iv-s-cpu-unit-candidate-20261028` HEAD independently fetched from GitHub before work. Previous branch unchanged.
- New branch `d1-r3-a-cpu-003-e1a-g2-j1-ivs-cpu-recheck-negative-controls-20261028`, from that fixed commit.
- One new test source: `a_predicate_003/gate_g2/j1_iv_s/tests/test_sidecar_adversarial_cpu.py` (Git blob **`ea72b6d429f1d3d2cc64c014e235e88014308fbb`**).
- New review record: `a_predicate_003/gate_g2/j1_iv_s/IV_S_CPU_RECHECK_AND_ADVERSARIAL_REVIEW_20261028.md`; checkpoint this file; navigation-only append to `docs/PROJECT_MAP.md` and `docs/SESSION_START_PROTOCOL.md`.
- Final head and diff must be confirmed by remote GitHub after commit. No local Git clone available due network DNS restriction; exact retained local Python file hashes matched GitHub blobs. No modifications to `j1/sidecar` production implementation, the original 23 tests, J1/oracle, Bench, Parcae, R3 or model.

## Explicit experiment record

| Field | Expected | Actual | Status |
|---|---|---|---|
| Purpose | Reproduce the exact pinned component and strengthen negative/semantic-boundary unit coverage | Original 23 cases + 10 supplemental independently built adversarial inputs | completed |
| Environment | CPU stdlib, no GPU / Bench / process side effect | CPython 3.13.5 Linux x86-64, no added dependencies | PASS |
| Input | Exact remote-blobs matched source/tests; 10 ephemeral new in-memory cases, not official S/O | Exact SHA match for original 3 files; test blob `ea72b6d…`; no persisted fixture data | PASS |
| Expected outcome | All 33 assert documented statuses and no failures/errors | Ran 33 in 0.008s, 33 PASS, 0 FAIL / 0 ERROR | PASS — local component only |
| Pinned Git checkout and CI | Full clone/re-run from remote desired | Git network DNS blocked; byte-by-byte blobs validated; no Git clone/CI | BLOCKED / NOT TESTED |
| External author-independent review and Grok | Real external report | None received; same assistant performed static scan | NOT TESTED / DEFERRED |

## Open findings

`IVS-RECHECK-01 HIGH` proof of independent evidence custody absent (ADV-09 demonstrates self-consistent fake reference remains a *byte* match); `IVS-RECHECK-02 MEDIUM` canonical byte validation is not full Lane S semantics / O-authored kind-body match (SC-08); `IVS-RECHECK-03 MEDIUM` 4_000_001-byte cap not frozen equivalent; `IVS-RECHECK-04 INFO` cross-platform and guard not validated. `OBS-J1-SEAL-01`, OQ-13, D-E02/D-E03, G2 O-1…15 continue unresolved.

## Next ONLY

Independent external code review and source-grounded cross-review, when genuinely accessible; keep Grok DEFERRED unless there is an actual report. Then start one separately scoped small CPU development of independent full-Lane-S semantic validation **without** upgrading Oracle, running G2 REAL or freezing criteria. Do not mistake 33 local unit passes for official 18-case acceptance.
