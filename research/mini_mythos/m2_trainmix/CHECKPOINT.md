# M2-T — actual uploaded-JSON audit and stage checkpoint (2026-10-30)

**Uploaded file identity / recorded-data consistency: PASS. Primary intervention: FAIL. Depth2 safeguard: PASS. Combined intervention: FAIL. Extra-inference-depth benefit: FAIL.** The actual original `result.json` has now been received, read and independently hashed. Do not keep requesting it, and do not replace these results with another training run.

This is a read-only artifact audit, integer-index/schedule regeneration and linkage to existing M2-L input states. It is **not** a new model run, independent NLL/profiler evaluation, audit of six new final binaries, Grok/Claude review, or permission to merge. Formal Oracle remains BLOCKED/NOT_READY, `FORMAL_ACCEPTANCE_READY=False`; no G2 REAL.

## 1. Version and evidence provenance

- Repository `leotree2020/OpenMythos`; branch `mini-mythos-m2t-mixed-depth-control-20261029`, Draft PR #15, dependent on PR #14. Do not merge automatically.
- Original executed source: `6bd5dd0de4d6c98cb35e0ae263a555544f5a325b`. Protocol frozen first at `a28cd9026d1074d059d2402cd172e8c9e6d32fa6`. Neither protocol nor runner changed.
- Untouched upstream pin: `69284c13746e849104f738d6d1a347b1f457df76`.
- Prior terminal-summary checkpoint remains in history at `3ede67c0b3e02278b9bcd25edd38ab5180576bd5`; copied terminal summary remains `evidence/user_supplied_result_summary_001.txt`. This audit supersedes its pending-JSON status only, not its scientific FAIL or other outstanding evidence.
- Actual uploaded JSON: **430,774 bytes**, SHA256 **`874a4199ce781632160ff4ea95b59d1e25cdcc792fa0276e303a9b06e2f2bcf7`**, independently computed and exactly matching the prior user digest. Input was unchanged after analysis.
- User-side source remains `/workspaces/OpenMythos/mythos_evidence/m2_trainmix_v1/result.json`. No output directory, snapshots or old evidence overwritten.
- Saved summary: [`evidence/uploaded_json_audit_20261030.json`](evidence/uploaded_json_audit_20261030.json), initial commit `9f653cf78ab127be3f70b5894acd93bd840d5145`.
- Conversation audit bundle `Mythos_M2T_JSON_Audit_20261030.zip`, SHA256 `05a4a2de8b6a504ac2d1090ba561cba5fcf212858995633958a280124bc60ab4`, contains original uploaded JSON bytes, actual audit script, detailed assertions/results, log, Chinese report and manifest. Original full JSON is in this bundle; this commit records its summary, not a fabricated replacement raw file.

## 2. Purpose, frozen input, environment and expected outcomes

Question: does balanced depth1/3 continuation improve depth4 validation NLL relative to equally budgeted fixed2 continuation of the SAME native Parcae starting state? Three paired seeds 42/20261029/20261030, old step1920 model/AdamW/CPU RNG states, 480 new updates per arm, unchanged Tiny Shakespeare byte train/validation intervals, sequence32 and batch8. No old test or Alice metrics.

Each arm has 122,880 new target-token exposures and 960 core calls. FIXED uses depth2 at every update; MIXED has exactly240 depth1 and240 depth3, one of each in every adjacent pair, order from seed+37000. Identical sampled batches and recorded pre-forward RNG digests are mandatory.

Producer environment recorded in the file: Python3.12.3 / torch2.11.0+cpu / NumPy1.26.4 / einops0.8.0, Linux. This audit runtime: Python3.13.5 / torch2.10.0+cpu, CPU one thread. Different versions are used only for safe tensor reading, hash arithmetic and integer generation; no cross-build model-execution equivalence claim.

Frozen success requires mean(MIXED d4 - FIXED d4)<=-0.01 and each seed<0, together with d2 safeguard mean(MIXED d2 - FIXED d2)<=+0.02 and each<=+0.05. Separate extra-depth screen requires mean(MIXED d4 - MIXED d2)<=-0.01 and each<0. No post-hoc tolerance change.

## 3. Actual audit results

| Check | Actual result | Scope |
|---|---|---|
| Original uploaded SHA256 and strict JSON parsing | PASS | Exact bytes, no duplicate keys or nonfinite constants |
| Six unique seed/arm records and three baselines | PASS | Entire JSON parsed, not snippets |
| Twelve endpoint NLL/PPL values and window arithmetic | PASS | 3485 windows,111520 targets,18 discarded tail targets; PPL=exp(NLL) |
| Recorded training traces | PASS | 2880 finite loss values and2880 finite gradient-norm values;480 per row |
| Paired pre-forward RNG digests | PASS | All1440 stepwise pairs equal; raw per-step RNG states not supplied |
| Mixed schedules | PASS | Independently regenerated exact sequence for each seed; composition and pair order match |
| Sampled training windows | PASS | Independently regenerated old1920 prefix and new480 batch hashes using old pilot's recorded train length |
| Starting snapshot/model/AdamW/CPU RNG identities | PASS | Actually read only three original M2-L step1920 snapshots with weights_only=True; recomputed all four digests and matched both arms and baselines |
| Baseline records versus old pilot | PASS | Complete saved metric-object equality; not a fresh native evaluation |
| Counted training and inference budget arithmetic | PASS | Recalculated from saved operator counts, not a new profiler run |
| Producer script bytes | PASS | Prepared bundle script SHA matches result; Git blob e9391b9728768da37b4171c03e74284616915221 matches pinned record; script was not executed |
| All four scientific verdicts and paired deltas | PASS for classification consistency | Benefit verdicts below remain FAIL |
| Six new step2400 binary snapshots | NOT TESTED | Only filenames/digest fields supplied; old input snapshot audit does not cover new output binaries |
| Independent native NLL/FLOP reevaluation, training replay or resume parity | NOT TESTED | No model computation performed |
| New M2-T Grok/Claude independent review | NOT TESTED / DEFERRED | Earlier reviewers addressed other tasks |

Original M2-L archive SHA `0f14ef97493c86f04b02c2d62b381142599fe0640e8729d215a723753172a257` and pilot SHA `c5be0f6da8eab77ab499ad97a3aaf318633d2d44f234083165ffcacc3b26d7bb` were recomputed for the starting-state link and stayed unchanged. This was not another18-snapshot audit or repeat gradient diagnostic.

## 4. Absolute quality results and new clarification

| Seed | FIXED d2 | MIXED d2 | FIXED d4 | MIXED d4 |
|---:|---:|---:|---:|---:|
|42|2.012946388745|2.018137047862|2.023553593634|2.024363662044|
|20261029|1.981784499359|1.988198847477|1.995498899134|1.996025165561|
|20261030|2.001950007771|2.008328135421|2.011448793466|2.012494122520|
|Mean|1.998893631958|2.004888010253|2.010167095411|2.010960983375|

Mean starting d2 validation NLL was2.029522952048303. FIXED changes by -0.030629320089923102 and MIXED by -0.024634941795235916; both arms improve d2 relative to their own shared start in all three seeds. The failed hypothesis is incremental benefit over the equally trained control, **not** that continuation failed to learn.

- Primary M4-F4 mean **+0.000793887963424981: FAIL**; all three differences positive. Small magnitude does not establish statistically significant harm.
- Safeguard M2-F2 mean **+0.005994378294687186: PASS**, permissible relative loss only, not improvement.
- Combined intervention **FAIL**.
- Extra inference M4-M2 mean **+0.006072973121814466: FAIL**; deeper evaluation remains worse in every mixed seed.
- Difference-in-differences **-0.005200490331262205**, descriptive only. It reflects relatively greater MIXED deterioration at d2 versus FIXED than at d4; it does not substitute for the failed deep-endpoint benefit.

## 5. Counted budget, not hardware efficiency

Per-step saved operator counts: C1=63,111,168; C2=80,412,672; C3=97,714,176. Independently verified **C1+C3=2*C2=160,825,344**, separately for forward/backward as well as total. Both arms record **38,598,082,560** additional counted FLOPs per seed; all six runs sum to231,588,495,360. Target exposures sum to737,280 across all six runs, not unique corpus tokens.

Inference full-validation totals are11,676,590,080 at d2 and16,701,235,200 at d4 in both arms; last partial batch29 is correctly included. No end-to-end speed, memory, energy or full hardware FLOPs claim. Saved duration fields are descriptive only.

## 6. Open items and stage disposition

The requested uploaded-JSON audit is **complete**. Preserve M2-T as a limited negative mechanism result with open binary/reviewer items. No automatic new schedule, longer continuation, deeper sweep, GPU scale-up, protocol relaxation or merge.

Six new final binary states, full producer pip-freeze and independent native metric replay are outside this upload; do not claim those checked. Digest agreement establishes record consistency, not independent attestation of every operation. The corpus digest is linked to the old pilot; raw corpus bytes were not supplied again.

A-M2L-01 remains in both arms. A-M2L-02 initialization reconstruction remains OPEN; complete saved-state use does not resolve it. Claude's six original reviewer files and M2-D original result JSON remain separate pending records. Neither prevents recording the scoped negative outcome, but neither may be silently marked PASS.

**Next single action: stage decision / targeted independent review using the now-available source and raw M2-T JSON; no repeat upload request for this JSON, no retraining for sealing.** Binary-output audit, if separately supplied, must be labelled separately. Keep PR #15 Draft. Do not launch another research branch as a consequence of this bookkeeping update.

This stage update modifies only evidence summary/checkpoint and PR description; frozen models, scripts, protocol, upstream Parcae, J1, Bench, R3 and formal Oracle are untouched. No native forward/backward, optimizer update, GPU rental or merge was performed in this audit.
