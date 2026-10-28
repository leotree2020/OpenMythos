# J1 IV-S — independent sidecar and Lane S structural candidates

**Status: ISOLATED CPU COMPONENT TESTS 67/67 PASS (LOCAL); INDEPENDENT REVIEW PENDING; FORMAL ORACLE BLOCKED/NOT_READY.**

This package imports no J1, Bench, Parcae, Oracle or model code. It consists of two separately isolated proposed checker components:

- `sidecar.py`: canonical sidecar bytes, record-chain integrity, and F05 reference-prefix comparison. It does not authenticate the reference/manifests. Its 4,000,001-byte safety bound is provisional.
- `lane_s.py`: independent **structural** validation of a Lane S input document (`assertion_id`, `subject_observables`, `declared_trust_model`). It enforces the nine assertion identifiers, 14 event kinds, seven hypothetical role ceilings/tiers, closed event/identity/raw-field whitelists, non-bool integer rules, source/order uniqueness, answer-firewall tokens, NFC and canonical UTF-8 JSON with duplicate-key rejection. `validate_lane_s_bytes(data: bytes)` returns a `LaneSResult(valid, reason, events, trust_handles)`, **never** a formal case/run verdict.
- `tests/test_sidecar_cpu.py`, `tests/test_sidecar_adversarial_cpu.py`, `tests/test_lane_s_cpu.py`: deterministic, in-memory, **nonofficial synthetic CPU** tests. No fixture bytes are written into the repository.

## CPU reproduction (from repository root)

```bash
PYTHONPATH=research/mini_mythos/a_predicate_003/gate_g2 \
python -m unittest discover \
  -s research/mini_mythos/a_predicate_003/gate_g2/j1_iv_s/tests \
  -p 'test_*.py' -v
```

The author ran byte-matched local files on Python 3.13.5, Linux x86-64 CPU; result: **67 tests, 67 PASS, 0 FAIL/ERROR, ~0.009s**. This is **not** a remote CI run or a separate external reviewer. Git blobs: `lane_s.py=264971258c6e7ae709d0a884afb35c6538c668d0`, `tests/test_lane_s_cpu.py=a8d9eacc8fb0d9095193a1c7fc15805bd034d3ae`.

## Scientific boundary and blockers

**STRUCTURE_VALID is not VERIFIED_VALID IV-S.** The checker does *not* validate each case's O-authored meaning (SC-08), cannot independently establish a source's authentic role or provenance, and does not implement trusted Lane O truth, IAV custody, signature/key trust root, formal run guard or formal case acceptance. The untrusted caller can supply self-consistent roles and a self-matching reference log. The `MAX_INPUT_BYTES=8_000_000` limit is an independent, unfrozen defensive cap, not a pinned J1 schema scientific limit. A non-OK `read_status` is structurally legal even though evidence may be unusable.

Review these distinctions before any integration. All official 18 planned J1 S/O cases remain `NOT TESTED / NOT MATERIALIZED`; `FORMAL_ACCEPTANCE_READY=False`, Oracle `BLOCKED/NOT_READY`, G2 REAL `BLOCKED`, Grok `DEFERRED`. No change to existing `j1/`, upstream Parcae, frozen Bench, V0.1, R3 or model architecture.
