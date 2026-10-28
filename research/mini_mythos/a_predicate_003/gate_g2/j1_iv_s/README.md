# J1 IV-S independent sidecar verifier — isolated CPU candidate

Status: PROVISIONAL CODE; 23/23 LOCAL UNIT TESTS PASS; FORMAL J1 ACCEPTANCE BLOCKED/NOT_READY. This package is NOT an acceptance oracle, authenticated custody mechanism, or G2 REAL verifier.

## Functionality

- sidecar.py independently verifies nonempty newline-terminated canonical JSON records, strict field sets and duplicate keys, UTF-8, Unicode NFC, no floats, depth limits, sequence numbers, genesis, previous-record links and SHA-256 digests.
- verify_f05_reference(readback, reference, manifest, run_id) fully validates both sidecar chains, the manifest against the three-record reference, and a two- or three-record exact prefix. It returns INVALID_INSTRUMENT, VALID_SEAL_MATCH, or VALID_SEAL_MISMATCH, not a formal case verdict.
- Imports only Python standard library; NO import of existing j1.codec, j1.schema, j1.judge, j1.oracle, frozen Bench, Parcae or model code.
- The 4,000,001-byte safety cap is a provisional resource bound, NOT a certified equivalence to the original J1 input schema. This standalone tool does not verify independent origin of the reference, manifest, trust map or S/O truth.
- Test vectors are created deterministically in memory during local unit tests. There are no stored official Lane S/O fixtures, signatures or custody proofs.

## Reproduce CPU-only tests from repository root

    PYTHONPATH=research/mini_mythos/a_predicate_003/gate_g2 python -m unittest discover -s research/mini_mythos/a_predicate_003/gate_g2/j1_iv_s/tests -p 'test_*.py' -v

Author-side local execution: Python 3.13.5, Linux x86-64, 23 tests, 23 PASS, 0 FAIL, 0 ERROR, approximately 0.002 seconds. The executed local Python file Git blobs match the uploaded blobs for the branch commit. No GPU, native G2 process, or formal Oracle was run.

## Pending gates

Independent static code review; independent rerun on the pinned Git commit; review of byte cap, Unicode and reference provenance; complete Lane S validator; independently authored/sealed Lane O truth; trust-root and custodian; guard and runner; frozen acceptance criteria and official 18 cases. The formal Oracle remains BLOCKED/NOT_READY and FORMAL_ACCEPTANCE_READY=False.
