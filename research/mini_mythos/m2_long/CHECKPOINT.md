# Mythos M2-L — independently read uploaded-archive checkpoint (2026-10-29)

**Artifact integrity / saved evidence consistency: PASS. Frozen 1920-step validation-quality gate: FAIL.** This update supersedes the earlier terminal-only review: the actual uploaded tar, all JSONs, raw log and 18 binary model/optimizer/CPU-RNG snapshots have now been read. No model training, inference, native NLL reevaluation, GPU use, upstream changes or PR merge occurred.

## 1. Git and evidence provenance

- Repository `leotree2020/OpenMythos`, branch `mini-mythos-m2l-long-curve-cpu-20261029`; PR #13 remains Draft, dependent on Draft PR #12.
- Actual training code recorded in archive: `09d0d508fa0eef459c8b767b109b236f9490c014`.
- Original native upstream: `69284c13746e849104f738d6d1a347b1f457df76`.
- Protocol freeze: `3bf4be4b8463d13ae83636c977fb89ac66862ee9`. Frozen runner, models, protocol and thresholds are unchanged by this audit.
- The prior terminal-only checkpoint remains in history at `9741c867b71b872678115a27be35678ef09ee413`; terminal excerpt remains in `evidence/user_supplied_terminal_20261029.txt`.
- Original uploaded archive: `M2L_CPU_3seeds_20261029_085315.tar.gz`, **10,555,397 bytes**. Independently computed SHA256 **`0f14ef97493c86f04b02c2d62b381142599fe0640e8729d215a723753172a257`**.
- Independently computed `pilot.json` SHA256 **`c5be0f6da8eab77ab499ad97a3aaf318633d2d44f234083165ffcacc3b26d7bb`**. Both match the user's earlier terminal hashes.
- Original user evidence directory remains `/workspaces/OpenMythos/mythos_evidence/m2_long_v1/`. Original files have not been overwritten or re-evaluated.
- This review's summary is `evidence/archive_audit_20261029.json` (initial commit `e001db7532d8a8b463b6f261617b6b6e60a4fff8`). The local detailed audit JSON/script/manifest/report are supplied in `Mythos_M2L_Archive_Audit_20261029.zip`, SHA256 `4483b2e39a34145c3d33bbef3070c36c86cdd032e673e608fdeefccfb7c0604f`. The original 10 MB tar and binaries were not newly uploaded to GitHub by this review.

## 2. Actual read-only audit

Purpose: verify the actual archive against frozen experiment identities, file hashes, checkpoint state, paired data and quality arithmetic. Not another training experiment or Guard version.

Auditor: Python 3.13.5 / PyTorch 2.10.0+cpu / Linux / one CPU thread. Producer reports Python 3.12.3 / torch 2.11.0+cpu / NumPy 1.26.4 / einops 0.8.0. Different auditor dependencies are used only for tensor inspection, hash arithmetic and integer-index regeneration; no cross-version training equivalence claim.

Method: reject unsafe/duplicate tar paths, links and special members; extract only the expected 26 ordinary files; load all `.pt` with `weights_only=True, map_location='cpu'`; never execute archive code.

| Check | Actual outcome | Scope |
|---|---|---|
| Archive and pilot byte identity | PASS | Both complete SHA256 digests independently calculated |
| Exact file set | PASS | 7 JSON, 1 raw log, 18 model/AdamW/RNG snapshots; one directory entry |
| Six per-arm JSONs vs pilot rows | PASS | Full object equality |
| Binary snapshot hash vs JSON | PASS 18/18 | All expected files read and hashed |
| Semantic state_dict hash vs report | PASS 18/18 | Sorted tensor names and exact tensor byte streams |
| Saved tensor finiteness | PASS | Model and all existing AdamW state tensors finite |
| AdamW state counters/shapes | PASS with finding below | Existing states are at exact 120/480/1920 steps; parameter groups retain all model parameters |
| CPU RNG state loadability | PASS 18/18 | Valid uint8 states accepted by CPU Generator; not a resume test |
| Loss/norm trace lengths and prefixes | PASS | Six final traces each 1920; first 120/480 exact prefixes; final trace hashes match |
| Train input start regeneration | PASS | All seeds independently regenerate exact first120/all1920 hashes; paired arms match |
| Token/window/tail/PPL arithmetic | PASS | Validation:111520 targets; Alice:167488 targets; PPL=exp(NLL) |
| Raw log vs JSON | PASS | 18 checkpoint lines plus summary consistent |
| Prior M2 step120 fields | PASS limited | Six weight hashes and validation NLL values match previously retrieved fixed reference values; full original M2 loss arrays not re-downloaded in this review |
| Native model NLL reevaluation | NOT TESTED | No forward/backward executed |
| Interrupted/resumed numerical parity | NOT TESTED | Snapshots present does not prove exact recovery |
| New Grok review of this archive | NOT TESTED | Earlier Grok M1/M2 report is not an audit of this new artifact |

Recorded final traces contain 11,520 finite loss samples and 11,520 gradient-norm samples. Individual per-parameter gradients were not saved and are not independently verified at every step. Source/corpus bytes and initial model tensors are absent from the archive. Internal consistency and matching hashes do not independently attest every training operation.

## 3. Frozen quality result stays FAIL

Delta is Parcae minus GPT validation NLL. Do not mix it with M2 test NLL.

| Step | Mean GPT validation NLL | Mean Parcae validation NLL | Mean delta |
|---:|---:|---:|---:|
|120|2.584669757|2.602355959|+0.017686202|
|480|2.247211185|2.269971461|+0.022760276|
|1920|1.995236877|2.029522952|**+0.034286075**|

Final deltas: seed42 +0.028008054284488493; seed20261029 +0.033246230463386484; seed20261030 +0.04160394121276756. Each <=+0.05, but the mean +0.03428607532021418 exceeds +0.02. Joint quality rule **FAIL**. Both models learn; the average gap widens, not every individual curve monotonically.

Alice deltas: +0.013180145836532375 / +0.0758198216802346 / +0.001803123090027281; mean +0.03026769686893142. Its NLL/PPL arithmetic and token coverage are consistent. `ood_status PASS` denotes evaluation completion, not quality superiority. Do not invent an after-the-fact Alice quality gate or retune on it.

## 4. New HIGH interpretation finding A-M2L-01

All nine Parcae snapshots show **two parameters without saved AdamW state**, unchanged within each seed across 120/480/1920:

- `value_embeds.0.weight`, shape [256,32], **8192** parameters.
- `transformer.core_block.0.attn.ve_gate.weight`, shape [4,32], **128** parameters.

The corresponding parameter IDs remain in optimizer param_groups. GPT has 48 parameter tensors and 48 AdamW states; Parcae has 44 parameter tensors and 42 states. The reported total parameter counts are correct when excluding the rotary buffer, but differ from state-covered parameter counts:

| Arm | Total registered parameter count | Parameters with saved AdamW state |
|---|---:|---:|
|GPT|65344|65344|
|Parcae|60224|51904|

Original total-parameter ratio 1.08501594 and supported-op FLOP ratio 1.08201058 still satisfy their **original** <=1.10 gates. Do not rewrite their historical PASS using a new criterion. However, the state-covered ratio is **1.25893958**, so total matching must not be described as update-participating capacity matching.

Read-only pinned source agrees with the observation: `has_ve` in `modules/mixer.py` alternates by layer_id and config.n_layer; Parcae config.n_layer is 1 core block x backprop depth2 =2, whereas embedding construction uses 1+1+1=3 physical modules -> embedding keys0,2. Prelude id0 lacks a gate; core id1 has a gate but seeks absent embedding key1. Thus the two unused paths above are consistent with source. This review did NOT run a native `.grad is None` probe; preserve that distinction and ask Grok to independently confirm the optimizer-ID/parameter mapping. Do not generalize this small configuration to all Parcae variants or silently fix upstream.

Source blobs inspected: Parcae `e84aca22cbdf809693212c48470b43f67737b87b`, mixer `215d50827eaf6d02865acc4e94f211979cb2edc6`, config `8701866cc7124d79e4659290f0be2a4dffda1f15`.

## 5. Decision and next single instruction

**Seal this limited negative result: artifact audit PASS, quality FAIL, efficiency/architecture superiority not established.** No automatic step-count/GPU escalation, no new hyperparameter search on this validation/Alice set, no merge or architecture edit.

Next: supply the original archive plus this audit to Grok for **targeted review of A-M2L-01 and the FAIL interpretation**. If disagreement needs evidence, preregister one fixed synthetic-batch native forward/backward with no optimizer.step to inspect the two tensors' gradients and value-embedding/gate indices. Do not retrain or change upstream merely to get green numbers. Depth/efficiency studies should not precede understanding this newly observed capacity confounder.

CPU process_maxrss is cumulative high-water and cannot support isolated per-model peak-memory comparisons. The audit validates saved optimizer/RNG content but not numerical resume equivalence. Formal Oracle and G2 REAL remain blocked; no new Grok result has been fabricated. Stage exit remains qualified by these limits.
