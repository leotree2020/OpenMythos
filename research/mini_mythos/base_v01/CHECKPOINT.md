# Mythos Base v0.1 — B1 target run BLOCKED at A5

2026-11-01 (Asia/Tokyo). Experiment MYTHOS-BASELINE-B1. Run b1-20261101T021657Z.

## Current decision

The authorized target-machine run reached verify-load and stopped at A5. The official RoPE buffer freqs_cis differs from frozen native CPU recomputation: maximum absolute difference 0.00012207025429233909, above the preregistered 1e-6 threshold. Status: BLOCKED, not an implementation FAIL and not a demonstrated scientific cause. No threshold, buffer, model configuration or upstream code was changed.

The guard is before load_state_dict(strict=True). The binary was safely deserialized and its tensors accounted for, but strict model loading and post-load shared-weight verification were not completed. Generation and reload were not started. finalize was invoked once only to seal existing evidence. Its exit code 2 reports the existing BLOCKED state.

Engineering baseline: BLOCKED. Language quality: NOT TESTED. No real-weight continuations exist. This supersedes the implementation-only checkpoint at 0f072a4c5bbbc4f79e0f29732683e4e1db88eaed; that historical record remains in Git.

## Purpose

Controlled loading, fixed-prompt generation and save/reload of official Parcae-140M on CPU, toward a small trainable, resumable, text-generating research baseline. B1 contains no training; B2 and D2-A are not started.

## Git and frozen inputs

- Repository: leotree2020/OpenMythos. Branch: mythos-base-v01-b1.
- Target checkout: /workspaces/mythos-base-v01-b1.
- Frozen implementation origin: d39eabb0f1ec33230bfdd00337877c647dfa42db.
- Previous documentation HEAD: 0f072a4c5bbbc4f79e0f29732683e4e1db88eaed.
- Actual execution HEAD: f0541330868267af25c4d2d04f549bf3e4d77e2f. This adds only the reviewed requirements.lock to the previous HEAD; execution source is unchanged.
- This checkpoint belongs to a subsequent result/documentation commit descending from f054133; use the Git commit containing this file for its exact checkpoint identity.
- Upstream: sandyresearch/parcae@69284c13746e849104f738d6d1a347b1f457df76, /workspaces/mythos-parcae-pinned.
- Model: SandyResearch/parcae-140m@236739ce93ba1afc1b3f172fb4a509f4500d2852.
- Tokenizer: SandyResearch/parcae-tokenizer@6247b5d0592876b73660f34c2dd16c9db9e9045c.

All three artifacts were actually downloaded and hashed on this target:

| File | Bytes | Actual SHA-256 | Status |
|---|---:|---|---|
| pytorch_model.bin | 578361537 | ed6eb306464dd0d694e9eacd58f7e06ac3e44b43cb7c5c79dbcb1543059c6621 | PASS |
| config.json | 1741 | 5c8fc785c2f6dba67d0370ad715034860e3b22bfce850da825c06baa03923c13 | PASS |
| tokenizer.json | 2326980 | e0021e26057088d68047dbe6e77e2ba1c9fe9ae45bae3df9d67d48c82405ea77 | PASS |

The 12 prompts, 32 tokenizer probes, recurrence settings and numerical thresholds remain frozen.

## Environment and environment acceptance

Target Codespace: bookish-pancake-vwqx7rr9x5w3wxjr. Linux 6.8.0-1064-azure, AMD EPYC 7763, 2 visible logical CPUs. New isolated environment: /workspaces/mythos-base-v01-cpu312. Python 3.12.3; torch 2.11.0+cpu; numpy 1.26.4; einops 0.8.0; tokenizers 0.23.2; huggingface-hub 1.33.0.

Formal env-check recorded effective available memory 5534261248 bytes and free disk 7379808256 bytes, exceeding the 4 GiB / 5 GiB gates. CPU only, one thread, deterministic algorithms and FP32 checks passed. No historical D1/M2 environment was modified.

Expected: exact frozen direct dependencies, a complete hash lock, clean pip check, exact lock/freeze agreement and clean committed source. Actual: 25 packages hash-installed; no missing/extra/mismatched packages; pip check clean; all formal E checks PASS. Environment acceptance: PASS. Lock SHA-256: 84440f8945041ed314c29b205c5244e074116ede023d5aae0b11b633b4d6a51e.

Age-review scope must remain explicit: the frozen tool checked 23 PyPI artifacts and used its pre-existing non-PyPI exception for Jinja2 and the CPU PyTorch wheel. Its original uploaded=null entries are preserved. A separate official-metadata supplement matched Jinja2's exact SHA to a 2025-03-05 PyPI upload; PyTorch's exact official index SHA, 2026-03-23 release announcement and 2026-03-24 Last-Modified support the age review. Last-Modified is server metadata, not signed proof of historical first publication. Do not claim 25/25 built-in upload-age checks. See operator/nonpypi_age_metadata.json.

## Development helper checks

Purpose: verify the helper implementation using fixtures, including a random tiny-model rehearsal. Input: the committed test_base_v01.py, new target environment and pinned upstream. Expected: all 28 tests execute, with zero skips/errors/failures and no upstream changes. Actual: one invocation, 28/28 PASS, zero skips/errors/failures, 77.742 seconds reported by unittest; upstream status remained empty. This is development evidence, not A1-A11 acceptance.

## Formal acceptance results

Formal env-check, fetch and verify-load were each invoked once. No automatic retries or later model stages were launched.

| Item | Expected | Actual | Status |
|---|---|---|---|
| A1 | All fixed sizes and hashes match | All three actual artifacts match | PASS |
| A2 | weights_only load returns tensor dict | 63 tensor entries | PASS |
| A3 | Accounting plus post-load sharing pass | Accounting coverage 1.0; no missing/unexpected/shape/dtype/nonfinite errors; tied values/storage match in file. Post-load shared check not reached | NOT TESTED overall |
| A4 | Authorized config facts and built-in comparison match | No effective, derived or label-only differences | PASS |
| A5 | Native RoPE buffer max absolute difference <= 1e-6 | 0.00012207025429233909; shape [1,2048,1,64,2] | BLOCKED |
| A6 | Tokenizer identity and all probes pass | BPE, 32768 case-sensitive tokens/IDs, special IDs 0/1/2; 32/32 round trips | PASS |
| A7 | CPU SDPA fallback, no FA3 or override | Frozen flash selector resolves to fallback; MATH acceptance backend | PASS |
| A8-A10 | Logit equivalence, generation and same-process repeat | generate not run | NOT TESTED |
| A11 | New-process reload equivalence | reload-check not run | NOT TESTED |

The frozen verify_load.json U.upstream check remains NOT TESTED because execution stopped before reaching it. A separate post-stop Git audit confirmed upstream HEAD and tracked/untracked/ignored file state unchanged; that supplemental audit does not rewrite the original stage record.

## Evidence and integrity

- Full formal run, including private local artifacts: /workspaces/mythos-evidence/base_v01/b1/b1-20261101T021657Z.
- Environment build evidence: /workspaces/mythos-evidence/base_v01/env/20261101T021657Z.
- Operator/preflight/test/sealing records: /workspaces/mythos-evidence/base_v01/access/20261101T021657Z.
- Portable small reports: evidence_b1/b1-20261101T021657Z/ under this directory, including environment/ and operator/.
- Original manifest: 8/8 file sizes and SHA-256 values independently rechecked after the stop, zero mismatches. summary.json and manifest.json are excluded from the original manifest by design; both are covered by the portable bundle manifest.
- Portable bundle: 36 files, 455445 bytes before adding evidence_bundle_manifest.json. Bundle-manifest SHA-256: 7df79cfd5536f47f0effc4c306222ed509cd12f3838c5a35546947ac5bc1427d.
- No model weights, tokenizer binary/content, virtual environment or package binaries are committed. Weight/tokenizer license status remains UNCONFIRMED; no redistribution.

## Unresolved questions and boundaries

The origin and practical effect of the RoPE difference are unknown. Numerical precision, computation device, implementation version, RoPE parameters and buffer provenance are hypotheses, not established causes. No conclusion about generation quality can be made. Strict loading, post-load shared storage, logits, generation and reload remain untested.

No training, backward pass, optimizer step, GPU, KV cache, seed increase, threshold change, model change or upstream edit occurred. No B2/B3 or D2-A was started. PR #24 was not modified or merged. D1 findings and its frozen execution remain unchanged. Formal Oracle remains BLOCKED/NOT_READY; FORMAL_ACCEPTANCE_READY=False.

## Next single instruction

Draft and cross-review a minimal controlled RoPE buffer provenance/numerical-difference diagnostic protocol using these sealed artifacts and frozen source. Preserve the original binary, configuration, upstream revision and 1e-6 gate. The next task is read-only source audit, experimental design and review only: do not execute diagnostics, replace the buffer, relax the threshold, rerun B1, or start B2/D2-A without a new decision.
