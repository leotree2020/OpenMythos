# MYTHOS-DEPTH-LORA-CPU-V1 — completed checkpoint

Engineering execution/acceptance: **PASS**.
Primary depth-LoRA vs fixed32 exploratory screen: **PASS**.
Shared-LoRA vs fixed32 and secondary depth-vs-shared screens: **PASS**.

**Positive local result:** both trained LoRA recipes improve validation prediction relative to the unchanged official fixed32 model. Depth LoRA has lower NLL than shared LoRA, but slightly lower top-1 accuracy. The additional NLL gain cannot yet be attributed solely to depth specialization.

## Identity and environment

- Base: `e24d053f482a96bcc2ab207c1be73e4c91fcd721`.
- Branch/worktree: `mythos-depth-lora-cpu-v1`, `/workspaces/mythos-depth-lora-cpu-v1`.
- Data preparation freeze: `916e87ace8aa080529c5d5ce84378b8a52b52fda`; preparation evidence: `b879743591c27a40b039609084911cae2e0b8317`.
- Execution freeze: `083192871d6cc3abff0cd5a01fa6f628c7cf29ec`.
- Original result/evidence commit: `3537b51d72b10f70cc41d60d9b0a1a3793f0366d`. This subsequent acceptance commit only updates this checkpoint and adds `ACCEPTANCE_REVIEW.json`.
- Designated Codespace: `bookish-pancake-vwqx7rr9x5w3wxjr`.
- Existing Python3.12.3/Torch2.11.0+cpu; CPUFP32,2 intra-op/1 inter-op threads, deterministic algorithms, no enabled autocast. Existing NumPy1.26.4/PyArrow19.0.1 data environment.
- Upstream remains clean/read-only at `69284c13746e849104f738d6d1a347b1f457df76`. All original144,323,136 parameters remain frozen.63 state entries are byte-verified after loading and hash-identical after work.

## Purpose, inputs and fixed budget

Test depth-specific rank2 LoRA against unadapted fixed32, with shared rank2 LoRA as an adaptation control. Both trained arms modify only external research-side contributions to the two recurrent attention output projections. D has196,608 trainable parameters; S has6,144. No early exit is used; all32 iterations participate in backpropagation. Original files/modules/weights are preserved.

Official WikiText2 raw train and validation splits were acquired at frozen revision6231e49f19a707241d6b84d9cff60a3a86b85a85. Sixteen articles per split, one129-token intro window each, selected without model scores; no title/text/selected32-token overlap between train and validation. No historical test data was used for training. Inputs81885 bytes, SHA256 `b730b54aa1896227a67e25e6f422ea66f7c9d04ac1a17d98cfef5416d44653cc`.

Training seeds4101/4202,32 steps per arm/seed:16 examples repeated twice,128 shifted targets per step, AdamW LR0.001, rank2/alpha2, no dropout, weight_decay0, clipnorm1. Four final adapters were retained. No tuning, extra steps, checkpoint selection or retry.

Evaluation uses16 validation articles and h0 seeds5101/5202,128 input tokens, final64 causal prediction positions. There are1024 distinct target positions and2048 repeated observations per model, not2048 independent examples. The same input and actual h0/RNG bytes were matched across arms. This is a new evaluation sample and metric; its absolute NLL must not be compared directly with the earlier single-next-token quality/cost experiment.

## Expected / Actual / Status

| Gate | Expected | Actual | Status |
|---|---|---|---|
| Development checks |Frozen local/target fixture coverage, no skips |59/59 final tests pass |PASS |
| Main coverage |5 zero controls+128 training+160 evaluation calls |293/293 calls,128 updates,4 adapters |PASS |
| Zero initialization |Zero LoRA bitwise equals native fixed32 |All4 zero-adapter configurations pass |PASS |
| All-depth learning |Every A/B bank gets expected gradient and changes; base gradients absent |All banks pass; first-step A gradients zero as expected |PASS |
| Original state |63 loaded entries match original bytes and remain unchanged |PASS in main and reload processes |PASS |
| Main checks |No engineering FAIL/BLOCKED |1145 PASS/0 FAIL/0 BLOCKED |PASS |
| Fresh-process reload |One frozen case per final adapter reproduces logits/h0/RNG exactly |4/4 calls;115 PASS/0 FAIL |PASS |
| Independent raw-logit audit |Recompute metrics and frozen screens |1454 PASS/0 FAIL;335,544,320 saved logit components finite |PASS |
| Operator/custody |All required stages and preservation |93 PASS; no changed protected files/environments, no active worker |PASS |
| Primary quality screen |BOTH training seeds: mean NLL decrease>=0.01, top1 loss<=1 percentage point |NLL−0.128256/−0.130740; top1+2.0508/+1.6602pp |PASS |
| Evidence acceptance |All raw hashes/public copies/frozen inputs match |216 sealed files,52 public copies,22 frozen sources,15 input files verified |PASS |

Command exit was never used alone as acceptance. Main worker elapsed1007.984 seconds; reload30.977 seconds. These are execution durations, not comparative throughput or efficiency results.

## Predictive results

NLL is in nats/token; lower is better. Accuracy is over2048 scored observations per model.

| Model | Training seed | Mean NLL | Top1 correct | Accuracy |
|---|---:|---:|---:|---:|
| Original fixed32 |N/A |3.287538548167015 |732 |35.7421875% |
| Shared LoRA |4101 |3.1923276044055173 |776 |37.890625% |
| Shared LoRA |4202 |3.199081915485763 |770 |37.59765625% |
| Depth LoRA |4101 |3.1592827033640383 |774 |37.79296875% |
| Depth LoRA |4202 |3.156798457743871 |766 |37.40234375% |

D−F NLL: −0.128255844803/−0.130740090423. Each depth seed improves14/16 article-average NLLs. New Jersey Route50 and Sailor Mouth worsen in both seeds; maximum article worsening is+0.03996694/+0.04764877 nats/token.

S−F NLL: −0.0952109437615/−0.0884566326813. D−S NLL: −0.0330449010415/−0.0422834577419. D has2/4 fewer correct predictions than S (−0.09765625/−0.1953125 percentage points), within the frozen1pp guard. Therefore D does not dominate S on every metric.

Both training recipes help on this validation cohort. D's larger parameter capacity and different optimization dynamics remain competing explanations for its extra NLL gain: clipping was triggered10/9 times for D and19/19 times for S. No capacity-matched or compute-matched superiority is established.

## Evidence, review and limitations

Public per-case metrics, all training curves, adapter hashes, reload records, environments, custody and independent audit are in `evidence/`. Preparation records and short attributed source-curation excerpts are in `preparation/`. `ACCEPTANCE_REVIEW.json` records root/internal-peer recomputation and scope.

External raw evidence: `/workspaces/mythos-evidence/base_v01/depth_lora/attempt-v1`. Raw scored logits and adapter+optimizer+RNG checkpoints remain there, bound by `EXTERNAL_EVIDENCE_MANIFEST.json`. Source/input evidence remains in `preparation-v1`, bound by `INPUT_MANIFEST.json`. All216 sealed files and52 public copies were independently hash-checked on target after completion. The later `publication.json` receipt is outside the original seal and identifies3537b51d; `acceptance-v1.json` is the separate root receipt. Result worktree was clean and matched remote.

Internal peers recomputed public aggregates,128step coverage, paired states, per-bank updates and reload references. Implementers participated; no external Claude/Grok approval or duplicate model run is claimed. Synthetic development test iterations and pre-model packaging errors are retained and distinguished from the single formal run.

This is a small-budget adaptation result on16 held-out development articles and two training seeds. Pretraining overlap is unknown; it is not a full official benchmark, statistical confirmation, broad language-quality result, or production model acceptance. Predictive reload was tested on one preregistered case per adapter; training-interruption/resume trajectory equivalence remains NOT TESTED. No generation, latency benefit, equal-compute superiority or mechanism stacking was tested.

Old records, original weights, upstream and the early-stop threshold0.01 remain unchanged. No B1 rerun/A5 relaxation/B2/D2-A/GPU/PR24 operation occurred. Formal Oracle remains **BLOCKED/NOT_READY**, `FORMAL_ACCEPTANCE_READY=False`.

## Next unique instruction

Plan and freeze mechanism3, loop-index encoding, as a separate fixed32 CPU comparison without stacking. Retain both LoRA variants and this positive local result for later confirmation and controlled combination. This stage is complete and stopped; no next experiment has begun.
