# P1-R1 — uploaded-result audit and scoped closure (2026-10-30)

**Original uploaded JSON identity and record consistency: PASS. Six historical initializer targets: matched against the actual old M2-L pilot. Producer-path replay: PASS supported by the user's native run and audited records, NOT a new native run by this auditor. Claude discrepancy root cause: OPEN.** The requested raw-result handoff is now complete; do not request this JSON again or rerun either initializer tool.

## 1. Consolidated tracking and provenance

Use PR #17 / branch `mini-mythos-p1r-init-origin-20261030` as the single follow-up entry. PR #16 / INIT-01 remains supplementary same-environment evidence. The duplicate preparations are not two independent research milestones, twelve independent initial targets, or a Grok/Claude cross-review. Neither PR is merged, closed or deleted by this update.

- Repository: `leotree2020/OpenMythos`; base `4d1ecadc062e190a9bfc8b66b8e2d2962abb266a`.
- Executed P1-R1 source: `a097562ca8085eecd49c53f59a8ad83bc66ce066`; protocol frozen first at `ce46fc2a7d053e609c94fed7ecf67ba3f6bc171d`.
- Untouched native upstream: `69284c13746e849104f738d6d1a347b1f457df76`.
- Producer runner SHA256 `d6bf602f2f714b9d232da927ebc49a684d40fe1289005dc4531970681b759070`, Git blob `6d4e65424d52145d44a275a0012b56798aec913c`; independently recomputed from the previously uploaded preparation package, not executed here.
- Prior terminal-only checkpoint remains in history at `aaf09608c91793ab4569555ec172f3ef511191f0`. The copied dual-run transcript at `evidence/user_supplied_init_dual_run_20261030.txt` remains unchanged.
- Actual new upload: `result(1).json`, **352,876 bytes**, independently calculated SHA256 **`bf2b75fbcc49179cbdb059916a744ae8fa4cc682675bd802b662b32e791126ea`**. Matches the prior terminal digest. Its user-side source is `/workspaces/OpenMythos/mythos_evidence/p1r_init_v1/result.json`.
- Prior M2-L archive was opened read-only for its original `pilot.json` only; independently calculated pilot SHA256 **`c5be0f6da8eab77ab499ad97a3aaf318633d2d44f234083165ffcacc3b26d7bb`**. No binary weights loaded and no repeat 18-snapshot audit. The matched-M2 pilot digest is linked through this pilot; its bytes were not independently reopened in this audit.
- Actual audit summary: [evidence/uploaded_json_audit_20261030.json](evidence/uploaded_json_audit_20261030.json), first committed at `809ee0041913833de159836ee2b78942dd03ce74`.

## 2. Purpose, input, environment, expected and actual

Purpose: verify the completed original-producer initialization replay, not change models or find a beneficial depth schedule. Three seeds (42,20261029,20261030) times original GPT/Parcae; original constructors, shared IO pairing, original synthetic preflight and count in their historical order.

Recorded producer environment matches frozen Python3.12.3/torch2.11.0+cpu/NumPy1.26.4/einops0.8.0, Linux, FP32, CPU single thread. This is inspection of the saved environment/build record, not a new measurement in the user's Codespace. Auditor: Python3.13.5 standard library only; no Torch/model import.

Expected audit acceptance: exact uploaded byte identity, six unique rows/four stages, direct comparison to historical initial hashes, independently recomputed changed-fingerprint lists and preservation checks, and classification consistency. Actual: **138 record/identity assertions PASS, zero failures**. These are audit assertions, not 138 new model tests.

| Check | Actual status | Boundary |
|---|---|---|
| Raw SHA256 and strict JSON parsing | PASS | Actual new bytes; duplicate keys/nonfinite JSON constants rejected |
| Six unique seed/model targets; 24 stage records | PASS | Entire uploaded file read |
| 1,128 tensor fingerprint entries | PASS for metadata consistency | GPT49/Parcae45 state entries per phase, including persistent buffer; not raw tensor values |
| Six expected and final whole-state hashes vs old pilot | 6/6 PASS | Compared recorded hashes to actual old pilot, not only current expected fields |
| Pairing changed-name sets | PASS | Independently derived from complete tensor-fingerprint maps |
| Paired/preflight/count state maps | 6/6 PASS | Exact recorded whole-state and per-tensor metadata agreement |
| Caller CPU RNG before/after both probes | 6/6 PASS | Recorded digests equal; raw RNG bytes not provided |
| Parameters, counts and preflight results vs old pilot | PASS | Full saved objects equal; forward+backward equals total |
| Shared input and canonical Parcae output fingerprints | PASS | Linked to historical shared-IO fingerprints; input/norm metadata agree between arms |
| Producer script identity | PASS | Actual preparation-package bytes match new JSON and pinned Git blob |
| New independent native construction/probe run | NOT TESTED | No model computation by this auditor |
| Initial tensor binaries / raw RNG / INIT-01 .pt files | NOT TESTED | Not supplied by this JSON |
| New Grok/Claude review | NOT TESTED / DEFERRED | Two local replay tools are not two AI reviewers |
| Claude's six original mismatches explained | OPEN | Original reviewer code/output absent |

## 3. Confirmed phase pattern

| Model, all three seeds | Native constructor matches history | Paired IO | After preflight | After count | Pairing changes |
|---|---|---|---|---|---|
|GPT|true|true|true|true|none|
|Parcae|false|true|true|true|`lm_head.weight`, `transformer.wte.weight`|

Both probe changed-name sets are empty for every row; caller RNG digest remains equal at all three probe boundaries. Final LayerNorm metadata are identical on the two models after pairing. An equal-value copy does not require a changed fingerprint.

The historical Parcae target is the paired state, not the standalone constructor state, so native-constructor false is expected at that earlier boundary. Missing/changing pairing can explain a standalone Parcae-vs-paired-target mismatch. It does **not** show Claude omitted pairing and cannot by itself explain Claude's GPT mismatch. No unsupported attribution to CPU versus CUDA-enabled Torch builds.

## 4. Explicit evidence limits

This file contains SHA256 strings, shapes, dtypes and finite flags, not raw parameter arrays. A whole-state SHA is not independently recomputable from per-tensor SHAs. Likewise finite=true is a producer record, not a fresh finite-value measurement. GPT's transposed output-head byte identity cannot be proven from its untransposed digest alone; canonical Parcae head fingerprint is compared with the actual prior record. No full-binary, independent training, resume-equivalence, cross-build or model-quality claim is made.

The user-run report states six native sequences, zero optimizer updates and zero training batches. This auditor checked the stored scope and records; it did not re-execute native probes. Old M2-L quality FAIL, M2-D depth benefit FAIL, and M2-T intervention/extra-depth FAIL remain unchanged. A-M2L-01 remains unchanged.

## 5. Scoped closure and next instruction

**Close the requested P1-R1 raw-JSON handoff and recorded producer-recipe reconstruction subquestion.** Keep the separate Claude-discrepancy root-cause item OPEN, preserving its earlier six failed reconstructions. Do not repeat either tool, ask for this JSON again, create a third initializer diagnostic, or launch a build matrix by default.

The completed audit bundle in the conversation contains original uploaded bytes, old pilot bytes, producer-script reference, actual standard-library audit code/log/results, Chinese report and hash manifest. Any future root-cause work should compare Claude's already-existing procedure/output when available, not fabricate it. A new model intervention requires its own stage decision; this bookkeeping closure authorizes no new training, architecture patch, GPU or merge.

PR17 remains Draft and PR16 supplementary. This update changes only the existing checkpoint, a new audit summary and PR description. Original protocols, runners, upstream Parcae, Bench, J1, R3 and model architecture are untouched. Formal Oracle remains BLOCKED/NOT_READY, `FORMAL_ACCEPTANCE_READY=False`; no G2 REAL.
