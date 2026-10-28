# J1 IV-S input-boundary CPU experiment — source-transcribed probe

Date: 2026-10-29. Research scope: three discrepancy classes identified in the 2026-10-29 handoff review. This report is NOT a frozen contract or an independent review of original J1. This stage does NOT modify the prior J1, Lane S verifier or Oracle.

## Sources and scope

- Pinned OpenMythos base Git SHA: 0d440dd754c6b65d1508ca9367c94457f7f29fb6, verified on the source branch.
- New isolated branch: d1-r3-a-cpu-003-e1a-g2-j1-schema-boundary-probe-20261029. Source commit: e5f5f1eb711573f87a9dc7459a17c45169239a68.
- Existing read-only source blobs: j1/schema.py 551c4a01ed37f73c809776e123f98f6d055ac998; j1/codec.py bb486c922b945dd30edb003a11fe7758bd13c2fb; j1_iv_s/lane_s.py 264971258c6e7ae709d0a884afb35c6538c668d0.
- New implementation: j1_iv_s/boundary_contract.py, exact Git blob 726c70a9414adc1c9d1c3ce8be9b979f769b3f49.
- New unit tests: j1_iv_s/tests/test_boundary_contract_cpu.py, exact Git blob bb3611bbc93061394befcd4665ee710ad0cae4fa.
- This comparator reproduces only scalar predicates transcribed from pinned J1 source. It does NOT import/execute J1, perform a complete validate_input differential, authenticate a manifest, or issue any subject/case/run verdict.

## Findings tested

| Finding | Minimal input | Transcribed J1 structural predicate | Proposed stricter IV-S predicate | Status |
|---|---|---|---|---|
| BC-01 token | token hL followed by one newline | regex match with end-of-line dollar accepts | strict fullmatch with end-of-string anchor rejects | observed difference, policy UNDECIDED |
| BC-02 hex | 64 lowercase hex digits followed by newline | schema hex regex may accept | strict 64-character hex rejects; codec.manifest_problems additionally checks exact length | observed difference, policy UNDECIDED |
| BC-03 errno | EPIPE followed by newline | schema errno regex may accept | strict end-of-string rejects | observed difference, policy UNDECIDED |
| BC-04 Unicode | decomposed e plus combining acute | J1 ordinary string shape permits it | new Lane S recursive scan enforces NFC; J1 codec canonical serialization separately enforces NFC | observed domain distinction; policy UNDECIDED |
| BC-05 resource | measured document length 8000001 bytes | no equivalent whole-document ceiling found in original schema | new Lane S has provisional 8000000-byte guard | resource BLOCKED, NOT a J1 source FAIL |

No owner decision has selected which domain is the official scientific acceptance predicate. A self-consistent external reference log or declared trust role still does not establish provenance. Independent custody, IV-O/C/G, and SC-08 case-specific semantics are absent.

## Explicit CPU test record

| Element | Record |
|---|---|
| Objective | Check expected scalar comparator behavior for normal, malformed and boundary cases without mutating existing J1 or IV-S. |
| Environment | Local CPython 3.13.5, Linux 6.18.55 x86-64, CPU, standard library only. No GPU, Parcae, Bench, model or G2 REAL execution. |
| Inputs | 27 in-memory tests: token/hex/errno normal and trailing-newline cases, Unicode NFC and non-NFC, invalid types, resource 7999999/8000000/8000001 and bad size measurements. No official S/O fixtures. |
| Expected | 27 assertions pass; budget overflow is BLOCKED_RESOURCE_POLICY_UNFROZEN with formal_input_validity NOT_DETERMINED; no test pretends to authenticate data. |
| Actual | Ran 27 tests in 0.001s. OK. 27 PASS, 0 FAIL, 0 ERROR. |
| Exact command | PYTHONPATH=/mnt/data/mythos_boundary_stage python -m unittest discover -s /mnt/data/mythos_boundary_stage/j1_iv_s/tests -p test_*.py -v |
| Evidence | Local log /mnt/data/mythos_boundary_stage/boundary_cpu.log, SHA-256 98f5d0a44af973b047dc4800a687685e2990c7e1c07d7570ed123d850a2a0d55. Git blobs match exactly the locally tested Python files. |
| Scope result | PASS for this specific 27-test CPU micro suite only; direct J1 runtime differential NOT TESTED; independent external review PENDING. |

The previous 67/67 component test count is a historical separate test run. These 67 tests were NOT rerun here. Do NOT claim a single 94-test suite was executed.

## Open decisions and next action

D-BC-01: How to report J1-schema-valid but independently strict-IV-S-rejected inputs. D-BC-02: Whether NFC applies to official S bytes only or also changes the J1 input schema. D-BC-03: Resource ceiling, guard provenance and timeout policy. Existing OQ-13, OBS-J1-SEAL-01, D-E02/E03, G2 O-1…15 remain open.

Only next action: an externally independent reviewer verifies source-transcribed rules and proposes a versioned input policy; after a separate stage authorization, run minimal CPU probes against actual J1 schema.validate_input and the independent checker. No criteria freeze, official fixture materialization, Oracle unlock, G2 REAL, GPU, upstream source edit or merge.
