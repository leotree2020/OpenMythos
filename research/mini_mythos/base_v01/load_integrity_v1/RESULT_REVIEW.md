# CPU complete checkpoint restoration — PASS

Date: 2026-11-01. Experiment: `MYTHOS-CPU-LOAD-INTEGRITY-V1`. All 63 checkpoint state entries were restored byte-identically through the pinned official evaluation loader. This establishes loading integrity only; it does not amend historical B1 A5 or establish forward, generation, training or training-resume success.

## Acceptance record

| Field | Record |
|---|---|
| Purpose | Verify every actual parameter and buffer tensor against an independent read of the original published weight file, including aliases and complete byte coverage. |
| Environment | Codespace `bookish-pancake-vwqx7rr9x5w3wxjr`, frozen Python 3.12.3 / torch 2.11.0+cpu environment, CPU FP32 defaults, one intra/inter-op thread, deterministic algorithms, CUDA uninitialized. Full dependency inventory matched the frozen B1 record. |
| Input | Base `a20ec439`, pinned upstream `69284c13746e849104f738d6d1a347b1f457df76`, original B1 local config/weight bytes, frozen new implementation. |
| Expected | L0–L5 PASS; complete bidirectional key/metadata coverage; finite float values; every canonical logical byte equal; RoPE and tied embedding/head identities verified; protected state unchanged; complete evidence. |
| Actual | L0–L5 PASS; 648 check records PASS; 63 tensor rows PASS; no missing/unexpected keys, nonpersistent tensors, None buffer slots, save errors, unavailable protection checks or emergency artifacts. |
| Status | **PASS — official CPU checkpoint loading integrity.** |

The operator recorded one formal invocation, from 14:54:39 to 14:55:19 JST on 2026-11-01 (evidence timestamps 05:54:39 to 05:55:19 UTC). That interval includes all guards and sealing; it is not a loading-performance benchmark. The official model loader was called once. The independent reference read plus the official loader's internal read do not constitute two model executions.

## Exact coverage

| Item | Actual |
|---|---:|
| Original checkpoint keys | 63 |
| Completely compared keys | 63 |
| Parameter paths, including aliases | 62 |
| Unique parameter tensors | 61 |
| Unique parameter elements | 144,323,136 |
| Persistent buffer paths | 1 |
| Buffer elements | 262,144 |
| Logical bytes compared per side | 679,004,416 |
| Missing / unexpected keys | 0 / 0 |
| Nonpersistent tensor / None buffer slots | 0 / 0 |

The byte total includes both paths of the shared embedding/head parameter. It is not the weight-file size or unique parameter storage size. Both sides' block lengths and complete byte totals were checked; direct byte comparisons, not hash equality alone, supplied the equality verdict. All floating values on both sides were finite.

The RoPE buffer `freqs_cis` has shape `[1,2048,1,64,2]`, dtype FP32 and 1,048,576 compared bytes. Its source and restored canonical-byte SHA-256 are both:

`abffe7d0ca6dd0684317f48a2dce9d24e825f63e5e1facb9c8a259ca1d4a302b`

`lm_head.weight` and `transformer.wte.weight` remain the same Parameter object with the same storage, offset, shape and stride. Both named paths independently matched their original checkpoint values. No harness assignment, dtype cast, config override or buffer substitution was used.

## Versions and evidence

- Branch: `mythos-base-v01-cpu-load-v1`, using the existing isolated worktree `/workspaces/mythos-base-v01-rope-diag-v11`.
- Implementation A: `aa26e7023d4f634dd6f65e259e5a04f47da2578d`.
- Execution/checkpoint B: `acf0ffce9a6a16ab3e11de719fae5459061c96cd`.
- Run: `load-v1-20261101T055439Z`.
- Frozen lock SHA-256: `84440f8945041ed314c29b205c5244e074116ede023d5aae0b11b633b4d6a51e`.
- Target run directory: `/workspaces/mythos-evidence/base_v01/load_integrity/load-v1-20261101T055439Z`.
- Operator records: `/workspaces/mythos-evidence/base_v01/load_operator/load-v1-20261101T055439Z`.
- Summary: 1,292 bytes, SHA-256 `7e9463fb9f58f5b692e8ac1daebe35513ce5618bcbf2d4f8c32737055df127db`.
- Full manifest: 129,670 bytes, SHA-256 `fbef83e3acb8e98446d2bff5dabe7b3d89c26dc891549c3895b40bcc64b788e4`.
- Public manifest: 128,755 bytes, SHA-256 `d42a000b167c682c0f03c2613c12757226911eaebe6562d885b89b1448535146`.

The full manifest's 723 entries were re-hashed on the target with no discrepancy. There are 725 actual run files and two directories; the only unlisted files are the two explicitly excluded manifests. The public bundle has 718 listed files plus its own manifest. Its relative `public/` prefix is preserved in the Git export.

L5 verified 362 protected files, original B1 and completed RoPE evidence membership, and the protected Git states without changes. No source repair or repeated execution occurred after observing the formal result. Original weights/configuration remain in the original B1 run; no copy of weight values or a restored model was published. Private logs and baseline metadata stay on the target.

An independent read-only evidence review re-hashed all 718 publicly listed files and cross-checked the 648 check records, 63 tensor rows, complete key coverage, aliases and byte accounting against the frozen implementation. Verdict: APPROVE. This review did not load the model or recompute tensors; private-file integrity was reviewed through the target-side full-manifest audit, not independently re-hashed locally. The reviewing agent had reviewed the runner but did not author it; this is evidence review, not an independent experimental replication.

## Scientific interpretation and remaining work

The previous RoPE diagnostic showed that five reconstructed buffers did not match the artifact under the frozen A5 screen. This new result establishes a different fact: the official CPU loading path restores the original artifact's actual parameters and persistent buffer exactly. It does not identify how the historical artifact's RoPE values were originally computed or prove that their difference from a freshly constructed buffer is harmless.

B1 A5 stays **BLOCKED** with threshold `1e-6`; B1 A3 overall and A8–A11 are not retroactively upgraded. Forward, generation, language quality, training and training-resume remain **NOT TESTED**. Historical creation/export environment remains **UNKNOWN**. Formal Oracle stays **BLOCKED / NOT_READY** and `FORMAL_ACCEPTANCE_READY=False`.

No upstream modification, B1/RoPE rerun, GPU, B2/D2-A, PR creation or PR #24 operation occurred. This stage ends after evidence/checkpoint submission.

Next single instruction: prepare and review a separate CPU forward, fixed-prompt generation and fresh-process reload-consistency protocol using the now-verified official loader and existing frozen prompts. Specify backend compatibility, finite outputs, deterministic comparison and language-quality reporting separately. Do not execute that next stage automatically or rewrite original B1 acceptance.
