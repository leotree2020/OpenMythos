# M2-T — user-reported outcome and decision checkpoint

**Decision: preserve a negative equal-counted-budget training-depth intervention result.** The user read an existing Codespaces result: execution, baseline and budget PASS; primary FAIL; depth2 safeguard PASS; combined intervention FAIL; extra inference-depth benefit FAIL. ChatGPT independently recomputed those scientific verdicts and the difference-in-differences identity from the pasted numeric arrays. This review did NOT rerun training, inspect original result.json bytes, inspect new binary snapshots, or execute Grok/Claude. Do not call the entire stage PASS or hide the failed primary behind the safeguard.

## 1. Provenance and evidence boundary

- Repository: leotree2020/OpenMythos; branch mini-mythos-m2t-mixed-depth-control-20261029; Draft PR #15, dependent on PR #14. No merge.
- Code HEAD displayed by the user: **6bd5dd0de4d6c98cb35e0ae263a555544f5a325b**. Initial protocol committed first at **a28cd9026d1074d059d2402cd172e8c9e6d32fa6**.
- Training harness blob: e9391b9728768da37b4171c03e74284616915221; launcher blob: 52b96d1a7943ad519f0060714eb415de400bbff6. Neither code nor frozen protocol was modified by this outcome review.
- Original native Parcae remains pinned to 69284c13746e849104f738d6d1a347b1f457df76. The shared initial inputs are the already audited M2-L model/AdamW/CPU-RNG snapshots, not replacements for missing M2-D evidence.
- User-side new result: `/workspaces/OpenMythos/mythos_evidence/m2_trainmix_v1/result.json`.
- USER-REPORTED SHA256: **874a4199ce781632160ff4ea95b59d1e25cdcc792fa0276e303a9b06e2f2bcf7**. Original result bytes have NOT been retrieved or independently rehashed in this review.
- User-provided summary is preserved as `evidence/user_supplied_result_summary_001.txt` in commit 2a79e30d1ba6638c2e9987906e1db057673fd214. It is explicitly labelled as copied terminal output, not original JSON or independently captured stdout.
- Six groups are reported. Their absolute NLLs, full traces, snapshots, measured costs, RNG pairing and original dependency dump require the original result and, where necessary, referenced files. No absolute final NLL, measured wall time or hardware performance was inferred from differences alone.
- The worktree already existed, and the last user command read an existing result instead of starting training. The directory conflict was not a new training failure. Preserve the actual run independently of that failed worktree-creation attempt.
- Preparation checkpoint and limited controller/snapshot tests remain immutable in history at the original code HEAD. Those preparation PASS results are not promoted into independent model execution evidence.

## 2. Purpose, fixed environment, inputs and expectations

Question: after the fixed-weight M2-D screen failed, can brief balanced training at depths1/3 improve depth4 prediction over equally budgeted fixed2 continuation? This compares two training schedules on the SAME native model, not GPT versus Parcae or an architectural repair.

Frozen runtime: Linux Python3.12.3, torch2.11.0+cpu, NumPy1.26.4, einops0.8.0; FP32 CPU, single thread, deterministic algorithms, math SDPA. These are source preconditions, not a fresh environment measurement by this reviewer.

Inputs: the same per-seed native Parcae step1920 model, AdamW and CPU RNG snapshots for both arms; Tiny Shakespeare training and already-explored validation intervals; byte tokenizer256, sequence32, batch8; seeds42/20261029/20261030. No Alice or original test evaluation. A-M2L-01 inactive native paths remain unchanged, and A-M2L-02 is not resolved by using complete stored state.

FIXED: 480 additional updates at depth2. MIXED: 480 updates, exactly240 depth1 and240 depth3, predefined adjacent-pair order. Both: 960 core calls,122880 new target-token exposures and identical sampled batches. Before training the harness requires counted C1+C3=2*C2; compare paired pre-forward RNG identities and all initial model/optimizer/RNG digests. Equal counted operations does not prove equal hardware time, memory or energy.

Let F2/F4 denote FIXED validation NLL at depths2/4, M2/M4 denote MIXED validation NLL. Lower NLL is better. Frozen criteria:
- Primary: mean(M4-F4)<=-0.01 AND every seed delta<0.
- Safeguard: mean(M2-F2)<=+0.02 AND each<=+0.05.
- Combined intervention: primary AND safeguard.
- Separate extra-inference benefit: mean(M4-M2)<=-0.01 AND each<0.
- These are exploratory validation screens, not statistical significance or a fresh held-out superiority claim.

## 3. Independently recomputed summary arithmetic

| Seed | M4-F4 primary | M2-F2 safeguard | M4-M2 extra-depth | (M4-M2)-(F4-F2) |
|---|---:|---:|---:|---:|
|42|+0.0008100684096175037|+0.0051906591166384075|+0.0062266141817595155|-0.004380590707020904|
|20261029|+0.0005262664264038541|+0.0064143481179324|+0.007826318084081851|-0.005888081691528546|
|20261030|+0.0010453290542535854|+0.00637812764949075|+0.004165987099602031|-0.005332798595237165|
|Mean|**+0.000793887963424981**|**+0.005994378294687186**|**+0.006072973121814466**|**-0.005200490331262205**|

Primary **FAIL**: all three deltas are positive (slightly worse), and the mean is not <=-0.01. This is a failure to show the prespecified benefit, not a claim of statistically significant harm.

Safeguard **PASS**: the observed depth2 degradation stays within the preregistered allowable loss. Safeguard PASS does NOT mean improved or exactly unchanged depth2 quality. Combined intervention **FAIL** because its primary failed.

Extra-inference benefit **FAIL**: after mixed training, depth4 still has higher NLL than depth2 in every seed. The mean +0.006072973121814466 is not the required <=-0.01 improvement.

### Do not misread the negative difference-in-differences

The identity is `(M4-M2)-(F4-F2) = (M4-F4)-(M2-F2)`; the four supplied arrays are numerically consistent with it. Inferred from these differences (not new absolute NLL measurements): FIXED's mean d4-minus-d2 gap is +0.01127346345307667, MIXED's gap is +0.006072973121814466.

The gap contracted by about0.00520049, but BOTH fixed-depth endpoint comparisons worsened: MIXED d2 is about0.00599438 higher and MIXED d4 about0.00079389 higher than their FIXED counterparts. The reduced gap therefore does not establish improved deep prediction; it largely reflects relatively greater deterioration at d2. Do not select this secondary contrast as a replacement success metric. All twelve absolute NLLs still need the original JSON for inspection.

## 4. Gate matrix

| Gate | Status | Actual evidence level |
|---|---|---|
| Six completed paired continuation groups | PASS as reported | Existing result-reading terminal excerpt; no independent inspection of all480-step traces yet |
| Original depth2 baseline replay | PASS as reported | Runner status, not independent fresh evaluation |
| Matched counted budgets/data/start/RNG controls | PASS as reported | Frozen harness checks verified in source; raw measured cost/pairing fields not yet received |
| Primary intervention benefit | **FAIL** | Independently recomputed from all three supplied deltas and frozen rule |
| Depth2 quality safeguard | **PASS** | Independently recomputed; permits small loss, not quality gain |
| Combined intervention | **FAIL** | Primary failed despite safeguard PASS |
| Extra inference-depth benefit | **FAIL** | Each mixed d4-minus-d2 delta positive |
| Difference-in-differences arithmetic | PASS | Computed identity consistent; not assigned a benefit verdict |
| New result.json byte identity/full record audit | NOT TESTED | Only user-reported digest received |
| Six new final binary model/optimizer/RNG states | NOT TESTED by this review | Prior M2-L snapshot audit does not cover new M2-T states |
| New M2-T Claude/Grok review | NOT TESTED | Earlier reviews are different stages |
| General efficiency/ACT/reasoning/statistical superiority | NOT TESTED / NOT ESTABLISHED | This narrow pilot does not establish any of these |

## 5. Decision and next single action

**NO-GO for automatic tuning of further depth schedules, extending this continuation, or scaling to GPU merely to seek a green result.** Preserve the failed primary and all secondary contrasts. Under this fixed micro-configuration, the preregistered480-step mixed1/3 intervention did not deliver its intended benefit. This does not disprove all mixed-depth training, other scales, or models trained with different depth distributions from the start.

M2-L longer-training quality FAIL and M2-D fixed-weight depth4-benefit FAIL remain separate limited results. Do not combine the three pilots into a universal disproof of recurrence or use the inactive paths as an untested causal explanation. No automatic next experimental branch is created by this checkpoint.

**Next only:** transfer the existing `m2_trainmix_v1/result.json` (not M1/M2-L/M2-D result files) and independently verify its user-reported SHA256, six full rows, all12 endpoint NLLs, counts, paired identities, schedules and recorded traces. Do not retrain, reinstall, delete outputs or repackage the already-audited old M2-L archive. The six new snapshots are a separate stronger integrity check if provided; JSON-only review must not claim binary audit. Keep PR #15 Draft and preserve the existing output directory. Claude's original A-M2L-01 reviewer files and M2-D raw JSON remain pending separately.

This outcome review changed documentation/evidence only, not the frozen protocol, runner, upstream, earlier results, J1, Oracle or G2 REAL. No model forward/backward, optimizer updates, GPU use or PR merge were performed here. Formal Oracle and G2 REAL remain gated.