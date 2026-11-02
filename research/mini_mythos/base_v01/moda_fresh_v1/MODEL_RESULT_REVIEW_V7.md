# MoDA fresh-text CPU V7 final evidence review

Engineering acceptance: **PASS**. MoDA versus native fixed32 performance screen: **FAIL**. MoDA versus parameter-matched shared adaptation screen: **PASS**. Native fixed32 remains the strongest tested configuration on this frozen new-text sample.

## Purpose, environment and inputs

Purpose: test zero-training transfer of frozen MoDA H and shared S adapters against unchanged native32 F, with paired initial state and full pretokenized CPU endpoint timing. Designated Codespace, CPU FP32, Python3.12.3 / Torch2.11.0+cpu / NumPy1.26.4,2 intra-op and1 inter-op threads; no dependency change or GPU.

Restore checkpoint50966e6faded76cbf8f64cf085748ff2df0ccddb; branch `mythos-moda-fresh-cpu-v1`; execution freeze `6a87446f8a146f62cae30ae75f986d2b30d30f60`; numerical evidence publication `a0ccda074bc0f9e57d5a47b21bc95efb03eae32c`; read-only review source commit `57d54605a1077c08be85072864727569e51960be`. This document and LATEST_CHECKPOINT.json are frozen by the commit containing them. Target checkout was kept at the clean result publication during both independent reviews; only after both passed was it fast-forwarded to the review source commit.

Input:20 fixed AG News train-split texts,5 per class,129 token IDs each; score64 next-token targets per text. Two h0 seeds5101/5202 and frozen adapter training seeds4101/4202. Full120000-row source scan,1052 eligible and736 project-history exclusions;20 selected. Frozen input32692B SHA2562b740275785c4920ff59bcf3b76b2a81cce24597e4f5de1f491b8ea3357890db. Historical scope32603 physical file records, including tracked historical repository snapshots. Prior independent data audit6/6 PASS; no source resampling, retokenization or historical rescan in this model stage.

## Expected and actual

Expected:405 model calls =5 separate historical sentinel bridges +200 unique quality rows +200 exact repeats;400 timed new-text calls,80/configuration;2560 scored observations/configuration. Zero training/backward/optimizer. Every unique64x32768 FP32 matrix audited in full by an independent live NumPy stream, complete matrix hash repeated in pass2, final retained8MiB sentinel audited again. All original input/source/environment/weight/adapter preservation, startup/storage checks and original12MiB nonraw/8MiB raw/256MiB reserve bounds must pass.

Actual: {"backward_calls": 0, "bridge_calls": 5, "calls_completed": 405, "calls_started": 405, "model_loads": 1, "optimizer_steps": 0, "quality_rows": 200, "repeat_rows": 200, "train_steps": 0}.69 target development helper checks PASS. Final numerical audit1818 PASS/0 FAIL. Operator/custody/publication PASS; both post-publication reviews PASS, with zero extra model calls.200 live full matrices audited and200 complete-hash repeats verified; final sentinel retained, not all original raw matrices. The199 other unique raw matrices are unavailable retrospectively; retained per-token metrics, raw digests, full live audit receipts and all comparison rows remain in evidence.

## Prediction quality and complete CPU endpoint cost

NLL is in nats/token; lower is better. Accuracy is next-token top1, not text coherence or task-solving accuracy. CPU mean covers the complete pretokenized instrumented prediction endpoint, including tensor construction, RNG/h0 and all32 recursive calls, output scoring and hook cleanup; it excludes model load, tokenization, raw serialization, independent audit and I/O.

| Configuration | Mean NLL | Token top1 accuracy | Mean endpoint seconds |
|---|---:|---:|---:|
| fixed32 | 3.61012481 | 36.64062% | 2.264494 |
| shared_4101 | 3.81394196 | 33.98438% | 2.336134 |
| depth_4101 | 3.80348560 | 34.60938% | 2.348285 |
| shared_4202 | 3.87409346 | 33.75000% | 2.339832 |
| depth_4202 | 3.83432708 | 34.60938% | 2.371064 |

Frozen exploratory improvement criterion per training seed: deltaNLL<=-0.01 and deltaAccuracy>=-0.01; both seeds required for the group. No post-hoc threshold change. Negative screen outcomes are valid scientific findings and do not turn a completed engineering pipeline into an execution failure.

| Comparison | Seed | Delta NLL | Delta accuracy percentage points | Screen |
|---|---:|---:|---:|---|
| depth_vs_fixed32 | 4101 | +0.19336079 | -2.03125 | FAIL |
| depth_vs_fixed32 | 4202 | +0.22420227 | -2.03125 | FAIL |
| depth_vs_shared | 4101 | -0.01045636 | +0.62500 | PASS |
| depth_vs_shared | 4202 | -0.03976638 | +0.85938 | PASS |
| shared_vs_fixed32 | 4101 | +0.20381715 | -2.65625 | FAIL |
| shared_vs_fixed32 | 4202 | +0.26396865 | -2.89062 | FAIL |

Group screens: {"depth_vs_fixed32": "FAIL", "depth_vs_shared": "PASS", "shared_vs_fixed32": "FAIL"}.

CPU endpoint H/F ratios: seed4101 1.037002x (+3.700%); seed4202 1.047061x (+4.706%). H/S ratios: 1.005201x / 1.013348x. These are descriptive CPU timings on this machine, not equal-compute superiority or production serving measurements.

Whole numerical worker wall 1051.861249s; model load 24.479913s; live independent audit 49.046708s; raw serialization 2.658597s; whole-worker peak RSS 2052112384B. Separate adapter loading and all400 raw timing rows are retained. Whole-worker wall is not pure model latency.

## Interpretation and unresolved questions

The frozen MoDA variant has an incremental signal relative to its matched shared-adapter control, while both adapted variants degrade against the unchanged native baseline on these20 new project texts. Therefore this is not positive evidence that the current MoDA candidate improves the base model on new text. Candidate promotion and mechanism stacking are not justified by this sample. Training/domain adaptation versus architectural causes remain competing hypotheses; these comparisons do not identify the cause of degradation.

Limits:20 conditional source texts, only2 trained adapter seeds and2 h0 evaluations; no statistical confirmation or broad generalization claim. Project-history exclusion is bounded by recorded physical scope; shared parser logic means absence was not independently fully retokenized. Base pretraining overlap is unknown. Endpoint includes instrumentation and excludes serving overhead. Post-review independently reconciles retained numbers and recorded old-file custody; it does not rehash every old file a second time or reconstruct199 missing full matrices. AI peer review is non-independent; external human/Grok review NOT TESTED.

## Evidence, preservation and next instruction

Numerical evidence: `evidence_v7/`, `MODEL_V7_EXTERNAL_EVIDENCE_MANIFEST.json`, `MODEL_CHECKPOINT_V7.md`; external run `/workspaces/mythos-evidence/base_v01/moda_fresh/attempt-v7`. Independent reconciliation, its exact source, original publication receipt and closed operator log: `post_review/`. Frozen inputs, weights, raw sentinel and adapters remain external and are not redistributed. All V6 BLOCKED records and the complete prior historical scope are retained. The explicitly proven never-created V5 draft log/directory stayed absent; no real old file was skipped. Lossless gzip preserves full physical path inventories; no protection scope reduction.

No upstream, weights, early-stop/A5 thresholds or architecture changes; no B1 rerun, GPU, B2, D2-A, MoE/other mechanism stacking, or PR24 operation. B1 A5 remains BLOCKED. Formal Oracle remains BLOCKED/NOT_READY; FORMAL_ACCEPTANCE_READY=False. No checkpoint claims production language quality or Claude capability reproduction.

Next unique instruction: keep native fixed32 as the reference; perform a read-only comparison of the existing old-domain versus these new-domain per-text degradation patterns and freeze a separately reviewed, minimally controlled follow-up protocol before any retraining or mechanism stacking. Do not tune this sample, change frozen weights/thresholds, or repeat V7. This execution stage is complete and stopped.
