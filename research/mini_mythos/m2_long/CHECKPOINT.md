# Mythos M2-L — measured outcome checkpoint (2026-10-29)

**Current decision: execution completed according to user-supplied Codespaces output; preregistered 1920-step validation-quality gate FAIL.** This is a useful negative model result, not an environment failure. Do not relax the tolerance, overwrite the result, call the entire stage PASS, or rerun until it passes. Raw artifact review and Grok review of this new outcome are still pending.

## 1. Provenance and evidence limits

- Repository: `leotree2020/OpenMythos`; isolated branch `mini-mythos-m2l-long-curve-cpu-20261029`; Draft PR #13 depends on Draft PR #12. No merge performed.
- Actual experiment code recorded by the user's terminal: `09d0d508fa0eef459c8b767b109b236f9490c014`.
- Fixed native GPT/Parcae upstream: `69284c13746e849104f738d6d1a347b1f457df76`.
- Protocol freeze: `3bf4be4b8463d13ae83636c977fb89ac66862ee9`. `PROTOCOL.md`, `experiment.py`, the launcher and thresholds are unchanged by this result review.
- Input terminal excerpt is preserved in `evidence/user_supplied_terminal_20261029.txt` (commit `c540242d1d794cf89678648bffafc54fcf8064f5`). This is user-provided output, not a remotely acquired raw log.
- Original user-side evidence directory: `/workspaces/OpenMythos/mythos_evidence/m2_long_v1/`.
- User-reported `pilot.json` SHA-256: `c5be0f6da8eab77ab499ad97a3aaf318633d2d44f234083165ffcacc3b26d7bb`. The reviewer has NOT downloaded that file or independently recomputed this digest. Binary checkpoints, optimizer/RNG snapshots, full traces and raw logs have NOT been inspected in this review.
- ChatGPT re-read the pinned protocol and result-classification source, and recomputed averages/differences from the 18 displayed validation values. This was arithmetic/source review, NOT retraining, binary audit, or an independent model rerun.
- The pre-execution checkpoint remains available in Git at experiment commit `09d0d508fa0eef459c8b767b109b236f9490c014`; its historical NOT TESTED status is superseded only as qualified below.

## 2. Purpose, environment, inputs and expected outcome

Purpose: determine whether the fixed native GPT/Parcae validation-quality gap closes or persists with continuous training at 120/480/1920 optimizer steps, without modifying the upstream architecture or optimizing on the already viewed test split.

Protocol environment: Linux CPU, Python 3.12, torch 2.11.0+cpu, NumPy 1.26.4, einops 0.8.0, one thread, deterministic algorithms, math SDPA. The supplied terminal explicitly reports `M2-L CPU ENV PASS 2.11.0+cpu`; a separate current pip freeze has not been retrieved by the reviewer.

Inputs: frozen Tiny Shakespeare UTF-8 bytes, sequence 32, batch 8, AdamW settings retained, GPT FFN60 versus Parcae FFN64 with recurrence `[0,2]`, seeds 42/20261029/20261030. Target-token exposures per model/seed: 30,720 / 122,880 / 491,520 at 120 / 480 / 1920 steps. These are exposures, not unique corpus sizes. Three seeds times two arms yields six training runs and 18 displayed validation measurements.

Frozen acceptance: exact step-120 reference continuity; complete finite-loss/finite-gradient training; max/min parameter and counted-operator FLOP ratios <=1.10; and, separately, final mean paired validation NLL delta <=+0.02 AND each seed delta <=+0.05. The quality thresholds were frozen before this run and must not be changed after viewing these results.

## 3. Actual results from the supplied terminal

All deltas below are **Parcae minus GPT**, where lower NLL is better. All entries are validation NLL; do not mix these with the earlier M2 test-NLL delta +0.01877512.

| Seed | Step | GPT validation NLL | Parcae validation NLL | Delta |
|---|---:|---:|---:|---:|
| 42 | 120 | 2.581361235231375 | 2.615692199148783 | +0.034330963917408 |
| 42 | 480 | 2.256879207701389 | 2.2658601216298435 | +0.008980913928454 |
| 42 | 1920 | 1.9965992146277187 | 2.024607268912207 | +0.028008054284488 |
| 20261029 | 120 | 2.5890875615895736 | 2.594146877587098 | +0.005059315997524 |
| 20261029 | 480 | 2.246342994971802 | 2.268721171944179 | +0.022378176972377 |
| 20261029 | 1920 | 1.9938065591809397 | 2.0270527896443262 | +0.033246230463386 |
| 20261030 | 120 | 2.5835604742233516 | 2.597228800241369 | +0.013668326018017 |
| 20261030 | 480 | 2.2384113528636127 | 2.275333089431697 | +0.036921736568084 |
| 20261030 | 1920 | 1.9953048563756082 | 2.0369087975883757 | +0.041603941212768 |

| Step | Mean GPT validation NLL | Mean Parcae validation NLL | Mean paired delta |
|---:|---:|---:|---:|
| 120 | 2.584669757014767 | 2.602355958992417 | +0.017686201977650 |
| 480 | 2.2472111851789345 | 2.2699714610019064 | +0.022760275822972 |
| 1920 | 1.9952368767280888 | 2.029522952048303 | +0.034286075320214 |

**Final quality verdict: FAIL.** The mean is +0.03428607532021418, above +0.02 by +0.01428607532021418. Every individual delta is below +0.05, but the protocol requires BOTH conditions. The individual-seed condition passing cannot cancel the mean failure.

Both models improve with longer training. Across the three seeds, the mean gap increases from 120 to 480 to 1920. This is not a claim that every seed's gap increases monotonically: seed 42 improves at 480 then worsens at 1920, and its final gap is smaller than its own step-120 gap. These data do not support the hypothesis that increasing this fixed training budget closes the average validation gap within the frozen tolerance.

## 4. Independent-corpus diagnostic

The terminal reports one-time Alice OOD evaluation completion and Parcae-minus-GPT NLL deltas:

- seed 42: +0.013180145836532375
- seed 20261029: +0.0758198216802346
- seed 20261030: +0.001803123090027281
- mean: +0.03026769686893142 (recomputed)

All three displayed OOD deltas are positive, so none favors Parcae on this diagnostic. `ood_status PASS` means the evaluation completed, NOT that OOD quality passed a tolerance or that Parcae generalized better. The OOD corpus is out of domain and had no preregistered quality gate; do not transfer the validation +0.05 threshold to the OOD row after the fact. Individual OOD NLL/PPL and full evaluation target counts require the original JSON for independent checking.

## 5. Acceptance matrix

| Item | Outcome | Evidence level |
|---|---|---|
| Six 1920-step native CPU runs | PASS as reported | Terminal has all 18 checkpoint measurements and final execution PASS; full training traces not yet retrieved |
| Exact historical 120-step continuity | PASS as reported | Native runner reports continuity PASS; reviewer checked visible step-120 NLLs, not original weight/gradient binaries |
| Frozen parameter/FLOP-budget tolerance | PASS as reported | Runner budget PASS; <=10% counted-op matching, not identical hardware cost |
| Final mean validation-quality margin | **FAIL** | Independently recomputed from the displayed values; +0.034286 > +0.02 |
| Final individual-seed quality margins | PASS | All three < +0.05; joint quality verdict remains FAIL |
| Alice diagnostic execution | PASS as reported | Completion and three deltas in terminal; no quality PASS assigned |
| Independent pilot.json and snapshot integrity audit | NOT TESTED | Original bytes not received in this review; user-supplied SHA only |
| Exact interrupted/resumed vs continuous parity | NOT TESTED | Snapshot saving is not proof of recovery equivalence |
| Grok review of the new M2-L results | NOT TESTED | Previous user-supplied M1/M2 review is not review of these new results |
| P2 efficiency superiority, statistical noninferiority, ACT/reasoning | NOT TESTED / NOT ESTABLISHED | No new end-to-end benchmark or reasoning experiment |

## 6. Development decision and next single instruction

**NO-GO for automatically scaling this fixed configuration or claiming efficiency/quality superiority on the basis of M2-L.** Stop blind step-count escalation and GPU scale-up justified solely by an expectation that this gap will disappear. Preserve both positive execution evidence and the negative quality result. This limited experiment does not disprove all recursive Transformers or Parcae at other scales/tasks. Existing M1 trainability and the older M2 exploratory result remain valid within their own scope.

Next single action: archive the existing `m2_long_v1` directory (pilot JSON, per-arm JSON, run log and all model/optimizer/RNG snapshots), independently verify its bytes and checkpoint metadata, and provide it with this FAIL interpretation to Grok. Do not rerun training or reevaluate Alice merely to create another archive, and do not overwrite original evidence. Keep PR #13 Draft.

After artifact review, a possible separately preregistered low-cost research step is a **validation-only inference-depth diagnostic using the existing Parcae weights**, with fixed RNG and explicit counted compute. This is only a candidate, NOT TESTED and not authorized as a silent new experiment by this checkpoint. A model trained at depth 2 extrapolated to other depths is not evidence of the benefits of retraining at those depths. Do not tune on the now-observed Alice diagnostic.

No upper-layer model, Parcae source, original training program, frozen thresholds, J1, Oracle or G2 REAL component was changed during this outcome review. No new training or GPU use occurred. Formal Oracle remains blocked; no G2 REAL claim follows from this model result.
