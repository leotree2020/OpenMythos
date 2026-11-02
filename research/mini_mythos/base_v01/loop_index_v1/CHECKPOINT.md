# MYTHOS-LOOP-INDEX-CPU-V1 — accepted result

Engineering: **PASS**. Root evidence acceptance: **382 PASS / 0 FAIL**.
The loop encoding improves slightly over native fixed32, but does not improve over the equal-parameter shared-bias control. Do not promote an encoding-specific advantage or stack it automatically.

## Purpose, environment and inputs

Test standalone fixed sinusoidal loop-index features, scaled by 96 zero-initialized trainable gains, against native fixed32 and 96 shared bias parameters. Injection occurs after the native adapter. This is an OpenMythos-inspired adaptation; its gain and placement differ from the source model. No LoRA/early-stop combination.

Designated Codespace bookish-pancake-vwqx7rr9x5w3wxjr; Python3.12.3, Torch2.11.0+cpu; CPU FP32,2 intra/1 inter threads, deterministic algorithms; no GPU/install. Base model144,323,136 parameters,63 state entries unchanged. Upstream sandyresearch/parcae@69284c13746e849104f738d6d1a347b1f457df76 remains clean/read-only.

Reused frozen16 WikiText2 training and16 validation articles,129 tokens each; inputs SHA256 b730b54aa1896227a67e25e6f422ea66f7c9d04ac1a17d98cfef5416d44653cc. Training32 steps per arm/seed, seeds4101/4202, actual h0 paired. Final evaluation128-token inputs,64 targets, h0 seeds5101/5202. There are1024 distinct scored target positions and2048 repeated observations per model, not2048 independent examples. Validation is a reused development benchmark.

## Expected and actual

Frozen practical screen: each training seed must reduce mean NLL by at least0.01 nats/token and lose no more than1 percentage point accuracy. NLL means average both h0 seeds and articles equally.

| Model | NLL | Top1 correct/2048 | Accuracy |
|---|---:|---:|---:|
| Native fixed32 |3.287538548167015|732|0.357421875|
| Shared bias4101 |3.2731715352252455|742|0.3623046875|
| Shared bias4202 |3.2731733507273866|742|0.3623046875|
| Loop code4101 |3.277532724970811|736|0.359375|
| Loop code4202 |3.277530450808194|736|0.359375|

C−F NLL: −0.010005823196204189 / −0.010008097358820842; accuracy +0.001953125 both. **Screen PASS**, only about0.000006–0.000008 nats beyond the registered NLL boundary. This is a marginal pilot pass, not robust/statistical confirmation.10/16 article means improve in each seed.

S−F NLL: −0.014367012941769203 / −0.014365197439628358; accuracy +0.0048828125 both. **Screen PASS**;11/16 article means improve.

C−S NLL: +0.004361189745565014 / +0.004357100080807516; accuracy −0.0029296875 both, six fewer correct observations. **Screen FAIL**, descriptive label NO_QUALIFIED_IMPROVEMENT. Shared bias is numerically better on aggregate NLL and top1. Equal96 parameters removes a capacity difference, but feature conditioning still differs. These results do not rule out other loop-encoding recipes.

No thresholds, seeds, training steps or settings changed after results.

## Engineering and evidence acceptance

-76/76 target developer checks;128 optimizer steps,293 main forwards,160 final evaluation rows.
-Worker1657 PASS /0 FAIL /0 BLOCKED; original63 model-state entries and absent base gradients preserved.
-All96 gain coordinates show gradients and final updates in all four adapters; all32 actual gain-gradient depth paths active.
-Four new-process reload checks are bitwise exact; reload115 PASS /0 FAIL.
-Independent NumPy FP64 audit1464 PASS /0 FAIL, recomputing all160 NLL/top1 cases and screens from335,544,320 finite raw logit components.
-Root acceptance382 PASS /0 FAIL verifies frozen source/input/external hashes and public copies, and all32 F32 rows match the prior LoRA baseline raw hashes, targets, actual h0/RNG, NLL and predictions.
-Main worker999.748765769 s; reload30.920472823 s. These totals include training/serialization/checks and are not a controlled throughput comparison.
-Original upstream, weights, controller hash/threshold, prior evidence and environments preserved; no active workers at seal.

External full raw logits/checkpoints: /workspaces/mythos-evidence/base_v01/loop_index/attempt-v1.
Root receipt: /workspaces/mythos-evidence/base_v01/loop_index/acceptance-v1.json.
The receipt is copied into ROOT_ACCEPTANCE.json in the acceptance commit; EXTERNAL_EVIDENCE_MANIFEST.json seals the original run, while the later receipt/publication are separately identified. No original evidence was deleted.

## Git and remaining limits

Base checkpoint: d2d6ddd1ca92a1bea31c5807306abf52e0f1aa85.
Execution freeze: c78be02123a39f54d60f406d3f4eeaf33dc67d50.
Original result: ea5d0ca3e2eb23b432cc50aabc955b251c4464f6.
Read-only acceptance program: c9551408f75ad727073a67fb6bcd3ec7a61a69b9.
Branch: mythos-loop-index-cpu-v1. Final acceptance commit is the commit containing this document and ROOT_ACCEPTANCE.json; confirm clean local/remote equality in its publication receipt.

Fresh-test generalization, statistical confirmation, generation quality, depth extrapolation, training-resume trajectory equivalence and mechanism combinations: **NOT TESTED**. Formal Oracle **BLOCKED/NOT_READY**, FORMAL_ACCEPTANCE_READY=False. Existing B1/A5 status unchanged; no B1 rerun/B2/D2-A/PR24 operation.

Next unique instruction: proceed to separately frozen, tiny CPU mathematical/gradient validation of the actual OpenMythos MoDA source, then MoE source, before either140M adaptation. Preserve this negative encoding-specific comparison; no automatic stacking or retuning. Subsequent real-model experiments require a separately fixed evidence/storage policy because target disk is limited.
