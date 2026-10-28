# J1 IV-S isolated CPU component — checkpoint (2026-10-28)

Phase: F3B-D1-A-CPU-003-E1A-G2-J1-IV-S-INDEPENDENT-CPU-UNIT-CANDIDATE-001.
Current state: NEW ISOLATED COMPONENT IMPLEMENTED; LOCAL CPU UNIT TESTS 23/23 PASS (component scope only); INDEPENDENT REVIEW PENDING. Formal 18-case acceptance NOT TESTED; Oracle BLOCKED/NOT_READY; FORMAL_ACCEPTANCE_READY=False; G2 REAL BLOCKED; Grok DEFERRED/NOT PERFORMED; criteria NOT FROZEN.

## Git source, scope and reproducibility

- Repository leotree2020/OpenMythos, base f73d8c5ae9be2b3b0674c0c0ba89b36bb85b091f, source branch d1-r3-a-cpu-003-e1a-g2-j1-errata003-static-recheck-grok-handoff-20261028.
- New isolated branch d1-r3-a-cpu-003-e1a-g2-j1-iv-s-cpu-unit-candidate-20261028; source-code commit 7ae67c55b788c59730758a4c697598fb52377f36; final HEAD must be verified by fetching remote branch after adding checkpoint.
- New package: research/mini_mythos/a_predicate_003/gate_g2/j1_iv_s/__init__.py, sidecar.py, tests/test_sidecar_cpu.py, README.md; checkpoint (this file); append-only docs/PROJECT_MAP.md and docs/SESSION_START_PROTOCOL.md.
- Local Git blob IDs of exact executed package: __init__.py 56717e45e023b3a484756247e5a77ae7b52c2986; sidecar.py 4749913c7b2e3e46c0706564d394cacedac8ae12; tests/test_sidecar_cpu.py c7e5ce70525b0a9641b6a72f560e6cc9fd96fdc8. The committed blobs were checked against the executed copies.
- No existing J1 source/tests, Oracle, V0.1, frozen Bench, Parcae, G0/G1, R3 or model was edited; no merge. This session did not inspect local Git clone/dirty state.

## R&D experiment record — local nonformal component unit suite

| Field | Value |
|---|---|
| Purpose | Verify an isolated CPU-only parser so damaged internal sidecars cannot be mistaken for a valid contradiction simply because J1 sees a seal mismatch. |
| Environment | Local isolated tool runtime, CPython 3.13.5, Linux 6.18.55 x86_64, standard library only, CPU, no external dependencies, GPU, Bench or Parcae. |
| Inputs | 23 deterministic ephemeral in-memory unit probes: 2/3 canonical records, valid shorter prefix vs full reference, incorrect manifest/run id, torn tail, broken digests/links, seq gap, duplicate JSON key, noncanonical formatting, bool, floats, invalid UTF-8/NFC, alternate internally valid nonprefix log. Not official S/O fixtures. |
| Expected | All 23 assertions pass with expected valid chain, VALID_SEAL_MATCH, VALID_SEAL_MISMATCH or INVALID_INSTRUMENT behavior; 0 errors or failures. |
| Command | PYTHONPATH=/mnt/data/mythos_dev python -m unittest discover -s /mnt/data/mythos_dev/j1_iv_s/tests -p 'test_*.py' -v |
| Actual | 23 tests executed in 0.002 seconds; 23 PASS, 0 FAIL, 0 ERROR. Re-run after exact-file Git blob match: PASS. |
| Status | PASS (LOCAL COMPONENT UNIT ONLY); official formal J1 acceptance NOT TESTED, remains BLOCKED/NOT_READY. |

## Open blockers

- Provisional parser safety bound is not proven J1-schema equivalent; reference and manifest are caller-supplied, not cryptographically authenticated. Independent code review is PENDING.
- Official 18 S/O fixtures not materialized. Independent Lane O truth/custody/trust root, IV-C/IV-G, guard, runner, full criteria are not implemented/frozen. ERRATA 003 P09 cross-assertion issue, OBS-J1-SEAL-01, owner O-1…O-15, OQ-13 all open.
- Grok DEFERRED/NOT PERFORMED; no real cross-review obtained. G2 REAL BLOCKED. FORMAL_ACCEPTANCE_READY=False unchanged.

## Next only

Independent static review of the new isolated module + CPU re-run from the pinned final Git commit. Record actual findings, correct within a separately scoped development branch if needed. Do not infer formal PASS, freeze, produce official S/O custody, merge or enter G2 REAL from these local unit results.
