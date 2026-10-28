# F3B D1 CPU-003 E1-A G2 J1 — SCHEMA BOUNDARY PROBE CHECKPOINT (2026-10-29)

STATUS: CPU micro-probe 27/27 PASS, scope limited to transcribed scalar predicates. CONTRACT DECISION OPEN. Independent reviewer PENDING; Grok DEFERRED/NOT PERFORMED. Formal J1 Oracle BLOCKED/NOT_READY, FORMAL_ACCEPTANCE_READY=False unchanged; 18 official S/O NOT MATERIALIZED/NOT TESTED; G2 REAL BLOCKED.

## Git

- Repository leotree2020/OpenMythos, base verified SHA 0d440dd754c6b65d1508ca9367c94457f7f29fb6.
- New branch d1-r3-a-cpu-003-e1a-g2-j1-schema-boundary-probe-20261029, code commit e5f5f1eb711573f87a9dc7459a17c45169239a68; final HEAD shall be read from remote after checkpoint commit (do not infer a self-referential SHA).
- Additive source j1_iv_s/boundary_contract.py, blob 726c70a9414adc1c9d1c3ce8be9b979f769b3f49; additive tests j1_iv_s/tests/test_boundary_contract_cpu.py, blob bb3611bbc93061394befcd4665ee710ad0cae4fa.
- Report: a_predicate_003/gate_g2/j1_iv_s/SCHEMA_BOUNDARY_PROBE_CPU_REPORT_20261029.md; this checkpoint; append-only navigation files.
- No original J1, Oracle, Parcae, Bench, R3, G0/G1 or model edits; no merge. Remote GitHub used to review/push, local full clone unavailable.

## Acceptance-oriented CPU experiment record

| Purpose | Environment | Inputs | Expected | Actual | Status |
|---|---|---|---|---|---|
| Distinguish schema/IV-S regex, NFC and size predicate discrepancies without choosing policy | CPython 3.13.5 Linux x86-64 stdlib CPU | 27 in-memory, named test cases; no official S/O | 27 pass; no J1 or formal acceptance claim | 27/27 PASS, 0 FAIL/ERROR, 0.001 seconds | PASS, limited component CPU experiment |
| Demonstrate provisional size overflow must not be called a J1 error | same | measured length 8000001 | BLOCKED_RESOURCE_POLICY_UNFROZEN; NOT_DETERMINED validity | observed | PASS, limited |
| Original 67 component tests | different historical execution | not rerun | no false combined count | historical log only | NOT TESTED this stage |
| Actual schema.validate_input vs IV-S integration | separate future stage | not executed | distinguish source acceptance domains | none | NOT TESTED |
| Independent custody, official 18 cases, formal Oracle and G2 REAL | gating required | not exercised | BLOCKED | unchanged | BLOCKED |

Log SHA-256: 98f5d0a44af973b047dc4800a687685e2990c7e1c07d7570ed123d850a2a0d55. The test file and module are Git-blob identical to locally executed files, but this is not independent CI or external reviewer evidence.

## Open blockers

D-BC-01 regex accepted-domain policy; D-BC-02 NFC layering; D-BC-03 8MB resource-policy limit; source J1 versus independent canonical predicates; SC-08, IV-O/C/G and trust root; OBS-J1-SEAL-01; OQ-13; G2 O-1…15. Grok DEFERRED.

## Sole next instruction

Obtain genuinely independent source-grounded review and resolve or preserve the input contract questions with explicit owner decisions. Only after a separate stage gate, run minimal CPU tests against actual pinned J1 schema and IV-S. Do not freeze, generate official fixtures, modify original components, merge, run GPU or start G2 REAL.
