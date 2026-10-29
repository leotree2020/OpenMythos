# M2-D measured terminal-outcome checkpoint — 2026-10-29

**Decision: preserve a negative fixed-weight inference-depth result.** User-supplied Codespaces output reports execution PASS and historical depth-2 baseline PASS. The frozen primary depth4-minus-depth2 improvement hypothesis is **FAIL**, independently recomputed from the 12 displayed NLL values. No new model run, training, GPU use or upstream change occurred in this result review. Do not call the entire stage PASS, loosen the criterion, substitute a secondary depth, or automatically test ever-larger depths to seek success.

## 1. Provenance and evidence boundary

- Repo: `leotree2020/OpenMythos`; branch `mini-mythos-m2d-fixed-weight-depth-20261029`; dependent Draft PR #14, base PR #13. Neither this review nor the reported evaluation merges any PR.
- Actual code shown in user's terminal: `1890faed8b7f17b87b88e1502da33c0de6760d7b`.
- Pre-execution protocol: `72b070722d09c3eb2ab2aac1591d3a164b655f95`, `m2_depth/PROTOCOL.md`.
- Unchanged evaluation harness Git blob: `7077353054bfb515b7712e8befc98960fb1cc60d`.
- Native GPT/Parcae pin: `69284c13746e849104f738d6d1a347b1f457df76`.
- Existing M2-L model/evidence: archive SHA256 `0f14ef97493c86f04b02c2d62b381142599fe0640e8729d215a723753172a257`, pilot SHA256 `c5be0f6da8eab77ab499ad97a3aaf318633d2d44f234083165ffcacc3b26d7bb`. Prior M2-L audit is not an audit of this new result.json.
- New result evidence: `evidence/user_supplied_terminal_20261029.txt`, a copied and explicitly labelled user terminal excerpt (commit `d471b8ca179690f7c3bfcb30e404293aa61b4010`), NOT independently captured stdout or raw result bytes.
- User-reported new result: `/workspaces/OpenMythos/mythos_evidence/m2_depth_v1/result.json`, SHA256 **`f9f3d42ef69241ee9b511154e65b1b7754294e83240763cfe29c8002956115dd`**. Original result.json has NOT been uploaded/retrieved or independently rehashed in this review. Companion console log: `/workspaces/OpenMythos/mythos_evidence/m2_depth_v1.console.log`.
- Preparation-only checkpoint and tests remain in Git history at `1890faed8b7f17b87b88e1502da33c0de6760d7b`. This checkpoint supersedes its NOT TESTED status only at the evidence levels expressly identified below.

## 2. Purpose, environment, input and expected output

Scientific question: with the SAME saved native Parcae weights trained at depth 2 for 1920 optimizer steps, does changing inference recurrence to 4 reduce validation NLL? Depths 1 and 8 are secondary diagnostics, not replacement primary hypotheses.

Frozen protocol uses original Linux Python3.12.3 / torch2.11.0+cpu / NumPy1.26.4 / einops0.8.0, FP32 CPU, one thread, deterministic algorithms and math SDPA. Source re-read confirms these are runtime preconditions; a fresh dependency dump was not retrieved in this review.

Input: three existing seed42/20261029/20261030 final snapshots; fixed Tiny Shakespeare validation interval, byte vocabulary256, sequence32, 3485 windows / 111520 next-token targets; fixed eval batching and RNG1212 for each seed/depth. All three depth-2 evaluations must exactly match original saved validation fields before off-depth scoring. Official forward uses num_steps_pair=[0,d] under no_grad and eval, without changing model configuration. No backward, optimizer, Alice, training, package installation or model/source mutation.

Frozen primary PASS requires **mean[NLL(d4)-NLL(d2)] <= -0.01 AND every seed delta <0**. It is an exploratory validation criterion, not statistical significance or a fresh held-out confirmation.

## 3. Actual terminal-derived results and arithmetic

| Depth | Mean validation NLL, 3 seeds | Mean delta vs depth2 | Counted forward FLOPs, full validation per seed | Cost / depth2 |
|---:|---:|---:|---:|---:|
|1|2.0765982754432315|+0.04707532339492859|9164267520|0.78484108|
|2|2.029522952048303|0|11676590080|1.00000000|
|4|2.0420414796233577|+0.012518527575054486|16701235200|1.43031785|
|8|2.047613176690626|+0.01809022464232261|26750525440|2.29095355|

Primary paired deltas (depth4 minus depth2):
- seed42: +0.008961138937360502
- seed20261029: +0.012542618090658042
- seed20261030: +0.016051825697144917

All three deltas are positive (worse), not strictly negative. Mean +0.012518527575054486 is above the -0.01 improvement requirement. **Primary FAIL is unequivocal under the frozen rule; it is not merely missing the requested improvement magnitude.** The declared exit code 1 is the hypothesis-failure result, not a crash.

Depth4 consumes **43.03178484% more counted forward operations** than depth2; depth8 consumes **129.09535452% more**. Both have worse validation NLL in every seed. Depth1 uses **21.51589242% less counted compute**, but has worse NLL in every seed; no acceptable-loss quality/cost gate was preregistered for it, so do not promote it as an efficiency success. Among the four tested depths, depth2 has lowest NLL for each seed.

These FLOPs are totals over the validation traversal, derived from full/partial batch supported-operator counts. They are not one-token cost, training FLOPs, elapsed-time ratios, inference latency, peak memory, or complete hardware FLOPs. No claim that recurrence doubling exactly doubles whole-model work.

## 4. Gate matrix

| Item | Outcome | Evidence level |
|---|---|---|
| Script syntax | PASS as reported | User terminal |
| 12 finite model evaluations | PASS as reported | Twelve displayed measurements; original per-window/raw result audit pending |
| Historical depth2 baseline | PASS as reported | All three displayed NLLs exactly match earlier M2-L final validation values; full metric/hash replay is reported by runner but raw new JSON not yet audited |
| Primary d4 improvement hypothesis | **FAIL** | Independently recomputed from user-supplied values and original protocol |
| Secondary d1/d8 | Descriptive only | No post-hoc PASS criterion assigned |
| Compute ratio arithmetic | PASS | Recalculated from displayed supported-op counts; no independent profiler rerun |
| Weights unchanged/no gradients/source integrity during execution | PASS as runner-implied, not independently re-audited | Verified pinned source requires these, full result records pending |
| New result.json byte identity and full recorded metadata | **NOT TESTED** | User SHA only; original result.json not received here |
| Claude/Grok review of M2-D | NOT TESTED | Previous A-M2L-01 report is a different task |
| Mixed-depth training, ACT, reasoning, general architecture superiority | NOT TESTED | No corresponding experiment |

## 5. Interpretation and development decision

The measured outcome does not support plug-in inference-depth scaling for THESE saved depth2-trained tiny weights on THIS validation interval. Extra computation did not automatically yield better predictive quality. Do not generalize to native Parcae at other scales, mixed-depth training, retraining at depth4, learned halting or reasoning tasks.

M2-L quality FAIL remains unchanged. A-M2L-01 inactive paths remain present and recorded, not repaired; this within-model depth comparison does not infer cross-model equivalent capacity or explain the GPT/Parcae gap. A-M2L-02 initial-hash reconstruction remains OPEN; loading and hashing full saved states avoids dependence on reconstructing initialization only for this diagnostic. Claude raw reviewer files remain pending; no new cross-review is fabricated. Formal Oracle and G2 REAL remain gated.

**NO-GO for automatic d16/d32 searches, longer training of this fixed configuration, or GPU scale-up solely in hope of turning these negative screens green.** Preserve the executed negative result and decide any genuinely different model intervention in a new, preregistered stage; no new experiment is launched by this checkpoint.

## 6. Next single action

Transfer the existing **result.json** (optionally its small sibling console log) from the user's Codespace. It is sufficient to audit this stage's recorded metrics, costs, full baseline checks, weight identities and source/environment hashes; do not repack or rerun the existing 18 M2-L training snapshots. Independently hash result.json against the user digest and reconcile its 12 rows with this terminal excerpt. Actual original inference reevaluation is separate and not required merely to preserve this negative record. Keep PR #14 Draft; no automatic merge.
