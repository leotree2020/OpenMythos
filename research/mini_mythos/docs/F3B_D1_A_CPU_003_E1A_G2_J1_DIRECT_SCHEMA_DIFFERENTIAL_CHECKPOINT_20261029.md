# F3B D1 CPU-003 E1-A G2 J1 — direct schema differential execution gate checkpoint

**Date:** 2026-10-29. **Task:** F3B-D1-A-CPU-003-E1A-G2-J1-DIRECT-SCHEMA-DIFFERENTIAL-001.

**Current state:** CPU DIRECT DIFFERENTIAL HARNESS PREPARED; GITHUB ACTIONS DECLARED BUT **NO RUN VERIFIED**; 11 NEW J1 ACTUAL-SOURCE TESTS **NOT TESTED**. Existing 27/27 and 67/67 are separate historical CPU experiments, NOT rerun during this stage. Original Oracle BLOCKED/NOT_READY, FORMAL_ACCEPTANCE_READY=False; official 18-case S/O NOT MATERIALIZED / NOT TESTED; G2 REAL BLOCKED; criteria NOT FROZEN; Grok DEFERRED / NOT PERFORMED.

## Git / environment / files

- Repo leotree2020/OpenMythos, input branch d1-r3-a-cpu-003-e1a-g2-j1-schema-boundary-probe-20261029 at verified HEAD **ad499044e7e19129abe9c319f9703904bfbc7849**.
- New isolated branch **d1-r3-a-cpu-003-e1a-g2-j1-direct-schema-differential-20261029**. Initial code/CI commit **baa13e8328bf4c7d4320479db9d69bb71746d33c**. Final HEAD is obtained by GitHub branch readback after this checkpoint; no guessed self-referential SHA.
- j1/schema.py original Git blob 551c4a01ed37f73c809776e123f98f6d055ac998 (read-only); j1_iv_s/lane_s.py blob 264971258c6e7ae709d0a884afb35c6538c668d0 (read-only).
- New nonofficial synthetic CPU test j1_iv_s/tests/test_j1_schema_direct_cpu.py, blob c4009f2d17853863d2427098d7d86adcc90b0379. New branch-limited .github/workflows/j1-ivs-schema-cpu-differential.yml; pins original J1, independent checker and test blobs.
- New report at a_predicate_003/gate_g2/j1_iv_s/J1_SCHEMA_DIRECT_CPU_DIFFERENTIAL_PREP_AND_CI_STATUS_20261029.md; this checkpoint; navigation-only appends in docs/PROJECT_MAP.md and docs/SESSION_START_PROTOCOL.md.
- Local CPython 3.13.5 Linux x86-64 used for AST and py_compile syntax checks; exact test Git blob matched. **Local J1 schema runtime could not be obtained from GitHub due DNS/network restriction**. Actions run/check-run query returned zero; no independent CI success is inferred. Local Git full clone/dirty status unavailable.

## Explicit test plan / observed evidence

| Purpose | Input | Expected | Actual | Status |
|---|---|---|---|---|
| Reproduce original J1 source acceptance versus independent IV-S | 11 temporary in-memory cases; J1 schema+lane_s from pinned Git; role, digest, errno, NFC, budget, invalid controls | 11 direct paired results as matrix in report, 0 unexpected differences | Harness committed, not executed against actual J1 | NOT TESTED |
| Verify test module is parseable and exactly submitted | Local complete 135-line file | py_compile PASS; Git test file blob equals upload | py_compile PASS, Git blob SHA matched c4009f2d... | PASS (local syntax/identity only) |
| GitHub Actions lightweight CPU run | Branch-specific workflow, no pip installations, J1 and IV-S pinned | completed logs and explicit pass/fail | No workflow runs or check-runs visible as of last query | NOT TESTED / TRIGGER UNVERIFIED |
| Prior boundary and component tests | 27 tests, 67 tests from earlier runs | Do not silently add counts to this run | Not rerun | NOT TESTED in this stage |
| Formal Oracle / case truth / upstream integrity | Unmodified base and guard conditions | No bypass | J1/Parcae/Bench/R3/model untouched | BLOCKED / NOT READY |

## Blockers and only next instruction

D-BC-01/02/03 (regex, NFC, full document resource budget) are not owner-approved science criteria. SC-08 case-specific semantics, trusted Lane O, IAV custody, source authenticity, guard, formal Oracle, Grok second-model peer review and G2 REAL remain blocked/not verified.

**Next only:** run test_j1_schema_direct_cpu.py on the exact pinned Git checkout in a genuine CPU environment (GitHub Actions if a run is actually triggered, otherwise a separate authorized Codespace/local environment), capture logs/exit code and a test-verdict matrix. If a predicted outcome differs from actual J1, keep FAIL evidence and design a minimal controlled follow-up; no unsanctioned source fixes. Do not freeze, merge, generate official fixtures, or enter G2 REAL.
