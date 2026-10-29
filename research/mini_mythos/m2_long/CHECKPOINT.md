# Mythos M2-L — negative result and Claude review checkpoint (2026-10-29)

**Decision: preserve M2-L as a limited negative research record, with explicit unresolved reproducibility.** Existing saved-artifact integrity checks PASS; frozen 1920-step validation-quality gate FAIL; A-M2L-01 inactive-path finding is corroborated by a user-supplied Claude single-batch diagnostic; whole-model initialization reconstruction is **NOT REPRODUCED (6/6), cause unknown**. Do not call the entire review PASS or discard the six failed checks.

Sealing a negative research record does not imply complete reproduction, Grok acceptance, permission to merge, or proof that recurrence is ineffective. This recording stage ran no new model/gradient experiment and modified no model, training program, protocol or threshold. Both PR #13 and its base PR #12 remain Draft.

## 1. Read first: provenance and exact scope

- Repository `leotree2020/OpenMythos`, branch `mini-mythos-m2l-long-curve-cpu-20261029`, PR #13.
- Original training code: `09d0d508fa0eef459c8b767b109b236f9490c014`.
- Original native upstream: `69284c13746e849104f738d6d1a347b1f457df76`.
- Pre-training protocol freeze: `3bf4be4b8463d13ae83636c977fb89ac66862ee9`. Protocol and runner remain unchanged.
- Previous actual-upload audit checkpoint is preserved at `76c4075d63da40f23ac019bbadcc71c427267179:research/mini_mythos/m2_long/CHECKPOINT.md`; prior terminal-only review remains at `9741c867b71b872678115a27be35678ef09ee413`.
- Actual archive: `M2L_CPU_3seeds_20261029_085315.tar.gz`, 10,555,397 bytes, SHA256 `0f14ef97493c86f04b02c2d62b381142599fe0640e8729d215a723753172a257`.
- Actual pilot JSON SHA256: `c5be0f6da8eab77ab499ad97a3aaf318633d2d44f234083165ffcacc3b26d7bb`.
- Existing ChatGPT archive audit: `evidence/archive_audit_20261029.json`; original archive, JSONs and 18 snapshots were actually read in that earlier audit, without executing model code.
- **New source:** [user-supplied Claude report](evidence/claude_user_review_A_M2L_01_20261029.md), recorded at `0157e8d64047016ea87908d1c985c36294d7212f`. It includes the reviewer text and ChatGPT's limited disposition. The six underlying Claude files have not yet been received in this review; the preregistration digest `352379ab…` is incomplete and is not independently verified here.
- User-side original directory: `/workspaces/OpenMythos/mythos_evidence/m2_long_v1/`. No evidence overwritten.

## 2. Original model experiment and frozen result

Purpose: determine whether the fixed native GPT/Parcae validation gap shrinks after continuous 120/480/1920-step training. Inputs: fixed Tiny Shakespeare byte train/validation splits; fixed independent Alice OOD corpus; sequence 32, batch 8, original AdamW settings; GPT FFN60, Parcae FFN64 with `[0,2]`; seeds 42/20261029/20261030.

Producer environment: Python 3.12.3, torch **2.11.0+cpu**, NumPy 1.26.4, einops 0.8.0, Linux, CPU FP32, single thread, deterministic algorithms and math SDPA. Per model/seed token exposures: 30,720 / 122,880 / 491,520. These are exposures, not unique corpus sizes.

Expected quality rule: final mean Parcae-minus-GPT validation NLL <=+0.02 **AND** each seed <=+0.05. Do not revise after observing results.

| Step | Mean GPT validation NLL | Mean Parcae validation NLL | Mean delta |
|---:|---:|---:|---:|
|120|2.584669757|2.602355959|+0.017686202|
|480|2.247211185|2.269971461|+0.022760276|
|1920|1.995236877|2.029522952|**+0.034286075**|

Final seed deltas: +0.028008054284488493 / +0.033246230463386484 / +0.04160394121276756. Individual bounds PASS; mean **FAIL**; joint quality **FAIL**. Both models learn; mean gap widens, not every individual trajectory monotonically. Original M2 test-NLL +0.01877512 is not this validation metric.

Alice OOD deltas: +0.013180145836532375 / +0.0758198216802346 / +0.001803123090027281, mean +0.03026769686893142. Evaluation completed; no preregistered OOD quality gate and no new superiority claim. Do not retune on Alice.

## 3. Audit and reviewer status matrix

| Item | Status | Evidence and limits |
|---|---|---|
| Original archive/pilot byte identity and member set | PASS | Earlier ChatGPT actual read; Claude separately reports confirmation; 26 ordinary files, 7 JSON, 1 log, 18 snapshots |
| Saved trained model hashes and existing AdamW state counters/shapes | PASS | Earlier 18/18 actual snapshot inspection; Claude reports 18/18; all registered parameters present in optimizer groups |
| Saved finite tensors, trace lengths/prefixes, batch starts and NLL/PPL arithmetic | PASS in artifact audits | Six 1920-entry final loss/norm traces; no independent rerun of all training operations |
| CPU RNG loadability | PASS only for loading | Does not prove numerical interrupted-resume equivalence |
| A-M2L-01 static mapping and snapshot observations | PASS for this config | Old actual artifact audit plus source inspection |
| A-M2L-01 single-batch `.grad is None` diagnostic | PASS as reported by Claude | One preregistered synthetic forward/backward, no optimizer.step; raw reviewer files pending here |
| Claude entire archive-check suite | **193 PASS / 6 failed checks**, not all PASS | Per supplied report, all 6 failures concern full-model initial-hash reconstruction |
| Full-model initial-hash reconstruction | **NOT REPRODUCED (6/6)** | A-M2L-02 OPEN; environment/build difference observed, cause not established |
| Final frozen validation-quality margin | **FAIL** | +0.03428607532021418 > +0.02 |
| Independent native NLL reevaluation / interrupted-resume parity | NOT TESTED | Loading weights/RNG is not either runtime experiment |
| Actual Grok review of this new A-M2L-01/02 evidence | DEFERRED | Claude is not Grok; earlier Grok M1/M2 review remains historical |
| P2 efficiency advantage / statistical noninferiority / ACT or reasoning | NOT ESTABLISHED / NOT TESTED | No corresponding demonstration |

## 4. A-M2L-01 — corroborated inactive paths, not a causal explanation of quality

Two tensors lack AdamW state in all nine Parcae snapshots and remain byte-identical within each seed at 120/480/1920:

- `value_embeds.0.weight`: [256,32], 8,192 parameters.
- `transformer.core_block.0.attn.ve_gate.weight`: [4,32], 128 parameters.

Claude reports that they also equal the corresponding seed-rebuilt initial tensors and are the **only** Parcae `grad is None` tensors in one fixed synthetic-batch backward. GPT control reports zero None-grad tensors among 48 parameter tensors. The static unused paths and snapshots support the configuration-specific finding; do not describe one batch as a separately observed 1920-step per-parameter gradient history.

Source mechanism: `config.n_layer=2`; embedding construction for three physical modules gives keys {0,2}. Prelude id0 has no gate, so key0 is ignored. Core id1 has a gate but no key1 embedding. Coda id3 uses key2 with a gate and trains. Source blobs previously inspected: Parcae `e84aca22cbdf809693212c48470b43f67737b87b`, mixer `215d50827eaf6d02865acc4e94f211979cb2edc6`, config `8701866cc7124d79e4659290f0be2a4dffda1f15`.

| Arm | Total parameters | Parameters with saved AdamW state |
|---|---:|---:|
|GPT|65344|65344|
|Parcae|60224|51904|

Original total-parameter ratio 1.08501594 and counted-FLOP ratio 1.08201058 still satisfy the frozen <=1.10 gates. The post-hoc state-covered/one-batch-gradient-participating ratio 1.25893958 is a confounder, **not** a replacement acceptance rule or a measurement of equivalent effective capacity. Do not infer that the 8,320 inactive parameters caused the NLL gap or that a patch would reverse it. Do not generalize to all Parcae configurations.

## 5. A-M2L-02 — whole-model initialization mismatch OPEN

Claude reports 6/6 full-model initial hashes differ from the original reports; a GPT wte hash also differs. Its stated runtime is Python 3.12.3 / torch **2.11.0+cu130** / NumPy 1.26.4 / einops 0.8.0, CPU-only. Original producer used torch **2.11.0+cpu**. The two inactive Parcae tensors do reproduce, but the entire initialization does not.

**Root cause unknown.** Do not attribute mismatch to build differences without evidence, erase the six failures, claim full initialization reproduction, or treat trained-snapshot hash agreement as initial-hash reproduction. This new discrepancy does not by itself invalidate the original saved trained-weight hashes or the static inactive-path finding; it limits stronger independent reproduction claims.

If resolving initial conditions later is necessary for a new controlled comparison, preregister a narrow same-build/order/RNG comparison with complete expected and actual tensor hashes and native initialization ordering. Do not automatically run another gradient-coverage test or full training for this record's sealing.

## 6. Stage exit and next single instruction

**Seal the negative record with open items.** Stop repeating coverage diagnostics solely for sealing. No automatic longer training, GPU scale-up, architecture edit, upstream relayering, dropped parameters, threshold relaxation, Alice retuning, or PR merge.

**Next only:** preserve and transfer the six existing Claude files (`M2L_A-M2L-01_REPORT.md`, `PREREG_expectations.md`, `grad_diag.py`, `archive_diag.py`, `grad_diag.out.json`, `archive_diag.out.json`) plus complete file SHA256s. The report locates them in the Claude execution environment, not the user's Codespaces or this container. Import them as reviewer evidence without rerunning. Reconcile their contents with this pasted report; carry A-M2L-02 as OPEN if its cause is still unsupported.

After this administrative closure, any model intervention or active-parameter-matched comparison is a **new research stage**, not a fix to the frozen result. Define its single scientific question, source isolation, controls and acceptance before execution. No new experiment is launched by this checkpoint.

Formal Oracle and G2 REAL remain gated. Historical records, original model binaries and training code remain untouched. Current update is two documentation/evidence records only, not a new experimental result.
