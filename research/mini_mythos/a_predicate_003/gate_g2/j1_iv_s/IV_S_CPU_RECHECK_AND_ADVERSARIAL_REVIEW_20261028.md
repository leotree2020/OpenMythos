# J1 IV-S candidate — pinned-source CPU reproduction and adversarial review

**2026-10-28 · scope:** isolated `j1_iv_s` CPU component. **AUTHOR-ASSOCIATED STATIC REVIEW, NOT AN EXTERNAL INDEPENDENT APPROVAL.** Existing J1, Parcae, frozen Bench, model, R3 and Oracle unchanged. No official fixture/custody, G2 REAL or GPU work.

## 1. Provenance and environment

- GitHub repository `leotree2020/OpenMythos`, verified source branch `d1-r3-a-cpu-003-e1a-g2-j1-iv-s-cpu-unit-candidate-20261028`, pinned HEAD **`5c3a14b45322da4ca4d748477789e9ebc30158a3`**.
- Remote Git blobs rechecked: `j1_iv_s/__init__.py` `56717e45e023b3a484756247e5a77ae7b52c2986`; `sidecar.py` `4749913c7b2e3e46c0706564d394cacedac8ae12`; original `tests/test_sidecar_cpu.py` `c7e5ce70525b0a9641b6a72f560e6cc9fd96fdc8`. The local retained three source files give **identical Git blob SHA**. No full Git clone: local runtime DNS resolution to github.com failed; this is a **byte-matched file-level reproduction of pinned code**, not an independently cloned repository.
- Test environment: CPython **3.13.5**, Linux **x86-64**, standard library, CPU only. No CUDA, installed dependencies, Parcae, J1 judge/oracle call, G2 process, real network or benchmark.
- Original command (local exact byte-matched pinned source):

```bash
PYTHONPATH=/mnt/data/mythos_dev python -m unittest discover -s /mnt/data/mythos_dev/j1_iv_s/tests -p 'test_*.py' -v
```

- Original baseline after source identity check: **23/23 PASS, 0 failures, 0 errors**, `Ran 23 tests in 0.004s`. Author reviewer retained raw CLI output locally as `/mnt/data/j1_iv_s_pinned_cpu_baseline.log` (not independently signed, not an official fixture).
- A self-contained, nonofficial **10-case adversarial CPU suite** was added at `j1_iv_s/tests/test_sidecar_adversarial_cpu.py`. Its test-vector generator is authored separately from the original 23-case test helper and does not import that helper. New test file Git blob: **`ea72b6d429f1d3d2cc64c014e235e88014308fbb`**, locally calculated and matched to GitHub's created blob.
- Combined local result after the exact final test-file bytes were checked: **33/33 PASS; 0 failures; 0 errors; 0.008s**. This stage does not claim that the GitHub remote itself executed the tests, and has not run CI.

## 2. Ten added controlled tests (all are nonofficial component tests)

| ID | Input / adversarial factor | Expected | Actual | Status |
|---|---|---|---|---|
| ADV-01 | Canonical valid sidecar with NFC Japanese text | valid chain | valid | PASS |
| ADV-02 | Non-NFC string even when digest recomputed to match | invalid chain | invalid | PASS |
| ADV-03 | JSON-equivalent escaped key value with noncanonical bytes | invalid chain | invalid | PASS |
| ADV-04 | Reorder otherwise individually valid linked record lines | invalid chain | invalid | PASS |
| ADV-05 | Boolean `prev_digest` rather than hex string | invalid chain | invalid | PASS |
| ADV-06 | Canonically encoded body array with valid record digest | invalid chain | invalid | PASS |
| ADV-07 | Non-bytes caller input | `INPUT_NOT_BYTES` | `INPUT_NOT_BYTES` | PASS |
| ADV-08 | Reference manifest `last_digest` changed | `INVALID_INSTRUMENT` | `INVALID_INSTRUMENT` | PASS |
| ADV-09 | Attacker regenerates **both** a three-line reference and its manifest | byte relation `VALID_SEAL_MATCH` **but provenance remains unverifiable** | matched-byte status observed | PASS (known limitation demonstrated) |
| ADV-10 | Valid four-line reference used for F05 restricted 2/3 design | `INVALID_INSTRUMENT` | `INVALID_INSTRUMENT` | PASS |

The ADV-09 result **is not evidence of a successful authenticity attack against a promised authenticity check**: the module has always disclaimed that capability. It demonstrates that a future formal caller must never promote `VALID_SEAL_MATCH` or a self-issued manifest to a custody or truth verdict.

## 3. Source-static findings and acceptance consequences

| ID / severity | Observation | Current disposition |
|---|---|---|
| `IVS-RECHECK-01` **HIGH formal gate**, not a bug in this isolated parser | F05 reference and manifest are caller-supplied; co-authoring/replacing both produces a matching byte relation. No authenticity, independent O truth, seal timing or trusted signer is established. ADV-09 explicitly exercises this limitation. | **FORMAL ACCEPTANCE BLOCKED**; require independently sourced/sealed reference and trust root before any formal IV-O/IV-C claim. |
| `IVS-RECHECK-02` **MEDIUM scope** | `verify_chain` checks canonical record bytes, links, shape and digest, **not** the per-case semantic `kind/body` agreement with an independently authored O design (SC-08) and not the full Lane S `schema.py` contract. | Standalone bytes-only verifier can be described as **component PASS** only; formal independent IV-S remains incomplete. |
| `IVS-RECHECK-03` **MEDIUM boundary** | Hard-coded `_MAX_BYTES = 4_000_001` is an implementation defensive limit and not a proved equivalence to J1 `MAX_LOG_CHARS` or real fixture policy. | Resource policy/edge cases need independent criteria decision before formal use. No silent formal PASS. |
| `IVS-RECHECK-04` **INFO** | Local byte-level verification and isolated CPU tests cover the named inputs but do not prove cross-platform behavior, interpreter-version agreement, or executable guard effectiveness. | Independent review and pinned Git rerun by separate operator remain PENDING. |

**No confirmed positive-path source defect requiring a source correction was found in the tested slice.** Do not report absent bugs outside the tested slice as a correctness guarantee.

## 4. Stage statuses and next instruction

- `LOCAL COMPONENT CPU REPRODUCTION = PASS 23/23`; `EXTENDED NONOFFICIAL CPU REGRESSION = PASS 33/33`.
- `EXTERNAL INDEPENDENT STATIC REVIEW = PENDING`; `GROK = DEFERRED / NO REPORT`.
- `FORMAL J1 18-case acceptance = NOT TESTED`; `FORMAL_ACCEPTANCE_READY=False`, Oracle `BLOCKED/NOT_READY`. `PF-02…06/PF-08 = BLOCKED`; `G2 REAL = BLOCKED`.
- 18 expected *subject* results still **5 PASS/5 FAIL/8 BLOCKED**, none executed. No GPU, experimental model change or upstream modification.

**Next only:** obtain independent reviewer feedback on `j1_iv_s` (including ADV-09, schema/SC-08 semantic gap and byte cap), then decide a bounded follow-up: either independently implement per-case IV-S semantics and trust-root integration after owner decision, or revise only the isolated component/tests under a fresh checkpoint. Formal Oracle, official S/O materialization, freeze and G2 REAL need separately gated authorization.
