# J1 original schema versus independent Lane S — direct CPU differential stage

**Date:** 2026-10-29. **Status:** TEST HARNESS AND ISOLATED CI PREPARED; NATIVE J1 CPU EXECUTION **NOT TESTED**. This is not a formal oracle run, not the 18 official S/O fixture suite, not SC-08 completion or native G2 REAL.

## Pinned source and execution boundary

- Repository: leotree2020/OpenMythos.
- Input branch: d1-r3-a-cpu-003-e1a-g2-j1-schema-boundary-probe-20261029, verified HEAD **ad499044e7e19129abe9c319f9703904bfbc7849**.
- New isolated branch: **d1-r3-a-cpu-003-e1a-g2-j1-direct-schema-differential-20261029**; first harness/workflow commit **baa13e8328bf4c7d4320479db9d69bb71746d33c**.
- Original j1/schema.py pinned blob **551c4a01ed37f73c809776e123f98f6d055ac998**; independent j1_iv_s/lane_s.py pinned blob **264971258c6e7ae709d0a884afb35c6538c668d0**. Neither file changed.
- New test harness j1_iv_s/tests/test_j1_schema_direct_cpu.py Git blob **c4009f2d17853863d2427098d7d86adcc90b0379**, byte-identical to the locally syntax-checked source. It directly imports the **actual** j1.schema.validate_input on execution, not the previous source-transcribed scalar comparator. It separately imports j1_iv_s.lane_s.validate_lane_s / validate_lane_s_bytes. The *test harness* intentionally imports J1; the independent implementation does NOT import J1.
- New targeted CPU-only GitHub Actions workflow .github/workflows/j1-ivs-schema-cpu-differential.yml. Runs only on pushes to this isolated branch, pins three Git blobs, uses Ubuntu + Python 3.11 + standard library and runs the direct tests followed by isolated test_*.py suite. It performs no pip installs, GPU, torch, network process test, model training, frozen Bench or Parcae execution.
- **GitHub Actions verification at authoring time:** branch/commit run search and check-runs returned **zero** runs. A declared workflow file is NOT proof of execution. Do not record the direct suite PASS until GitHub returns a completed run (with logs) or a reviewer runs the pinned checkout on CPU.
- The local container cannot clone or download GitHub content due DNS/network restriction, so the original 22.7KB j1/schema.py was **not locally executed**. The exact proposed Python harness was subjected to local Python 3.13.5 py_compile / AST parse and local Git blob check only. The previous 27 source-transcribed probes remain a separate historical CPU result.

## Eleven planned, currently unexecuted direct cases

| Case | Synthetic question | Expected native J1 structural schema | Expected isolated IV-S structural/byte checker | Actual native CPU result |
|---|---|---|---|---|
| DIFF-01 | Normal RUN_START evidence | ACCEPT | ACCEPT | NOT TESTED |
| DIFF-02 | A source handle with one final newline, matching trust-map key | ACCEPT (regex end-of-line) | REJECT (strict token) | NOT TESTED |
| DIFF-03 | SEAL_MANIFEST hash with one final newline | ACCEPT (schema regex) | REJECT (strict hex64) | NOT TESTED |
| DIFF-04 | R_WRITE_RESULT errno EPIPE + newline | ACCEPT (schema regex) | REJECT (strict errno) | NOT TESTED |
| DIFF-05 | Non-NFC ordinary run_id (decomposed e + acute) | ACCEPT (J1 schema) | REJECT (IV-S recursive NFC) | NOT TESTED |
| DIFF-06 | Non-NFC LOG_READBACK payload | ACCEPT (J1 schema) | REJECT (IV-S recursive NFC) | NOT TESTED |
| DIFF-07 | Event kind above assigned source role | REJECT | REJECT | NOT TESTED |
| DIFF-08 | Boolean monotonic order | REJECT | REJECT | NOT TESTED |
| DIFF-09 | Boolean identity.pid | REJECT | REJECT | NOT TESTED |
| DIFF-10 | Prohibited Lane O expected-verdict key | REJECT | REJECT | NOT TESTED |
| DIFF-11 | 520 valid synthetic LOG_READBACK records with 16k characters each (whole JSON >8MB) | ACCEPT under J1 *field/event* constraints | REJECT due unfrozen whole-document byte budget | NOT TESTED |

The last test is resource-sensitive yet CPU-only; 520 events are below the J1 2,000-event maximum and each payload below its 1,000,000-character per-field limit. The test uses temporary in-memory values, no official cases or real logs. If its run is blocked by runner environment, record **BLOCKED**, not a J1 source FAIL.

**Important limitation:** A direct schema-valid input is not a valid *canonical S evidence artefact* or authenticated source by implication. A result difference is evidence of separate domain policies, not automatic evidence that either implementation is defective. J1 codec's manifest validation and independent S/O custody remain different layers.

## Explicit experiment accounting

| Field | Expected | Observed | State |
|---|---|---|---|
| Objective | Directly call pinned original J1 schema vs independent IV-S with 11 nonofficial controlled synthetic cases | Test module implementing both direct calls and expectations created | PREPARED |
| Environment | Linux CPU, stdlib Python 3.11 CI (no GPU) | CI workflow committed; no actual Actions run yet | NOT TESTED |
| Source inputs | Verify pinned schema, lane_s and test blob before invoking | Exact blob pin checks defined in workflow; local test file Git blob checked | STATIC CHECK PASS, CI NOT TESTED |
| Test logic | 11 expected behavior pairs; 0 failures/errors if hypotheses correct | Local AST parse and py_compile PASS; native calls not locally executed | LOCAL SYNTAX PASS / DIRECT CPU NOT TESTED |
| Existing 27 boundary probes / previous 67 component cases | Preserve separate outcomes | Historical records 27/27 and 67/67 from distinct runs; neither rerun here | NOT TESTED in this stage |
| Formal 18-case acceptance / independent O truth / custody / guard | Remain blocked | No inputs generated, no Oracle unlocked or G2 REAL tests | BLOCKED / NOT READY |
| Grok cross-review | Only real second-model report counts | No connected Grok execution or report | DEFERRED / NOT PERFORMED |

## What to run next / stop

From an authorized full pinned Git checkout, CPU only:

    PYTHONPATH=research/mini_mythos/a_predicate_003/gate_g2 python -m unittest discover -s research/mini_mythos/a_predicate_003/gate_g2/j1_iv_s/tests -p 'test_j1_schema_direct_cpu.py' -v

Then check source SHA pins and, separately, the complete isolated suite:

    PYTHONPATH=research/mini_mythos/a_predicate_003/gate_g2 python -m unittest discover -s research/mini_mythos/a_predicate_003/gate_g2/j1_iv_s/tests -p 'test_*.py' -v

Record actual command, Python version, test counts, failures, Git HEAD and independent reviewer source. Resolve failures with minimal controlled differential, not by altering original J1 or silently changing criteria. Owner decisions D-BC-01 (regex), D-BC-02 (NFC), D-BC-03 (resource budget) remain UNDECIDED. Earlier D-E02/D-E03, OQ-13, OBS-J1-SEAL-01, G2 O-1…O-15 are still open.

**No formal acceptance freeze; original J1, Oracle, Parcae, frozen Bench, R3 and model must stay unchanged.** Formal 18 cases are NOT MATERIALIZED / NOT TESTED. Oracle FORMAL_ACCEPTANCE_READY=False, BLOCKED/NOT_READY. G2 REAL BLOCKED. External peer/Grok cross-review still outstanding.

## CI launch-channel experiment (2026-10-29)

A branch-local, docs-only Contents API update was requested to test whether the pre-existing branch-specific CPU workflow receives a GitHub Actions push event. This is not a CPU test or an approval; if no workflow run and actual logs appear, preserve DIRECT_J1_CPU=NOT_TESTED. Do not infer success from a GitHub commit alone. Formal Oracle remains BLOCKED/NOT_READY.
