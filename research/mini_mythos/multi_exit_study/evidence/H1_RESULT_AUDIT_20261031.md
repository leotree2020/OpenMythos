# MES-1 H1 uploaded-result audit — 2026-10-31

**Actual read-only record audit PASS: 353 assertions, zero failures; 40 conditions and 81,920 saved full answers independently rescored. Primary equal-budget, same-update, GPT safeguard and dedicated-P2 safeguard all FAIL. A within-trained-horizon depth benefit PASS.** This is not a native inference/training replay. Preserve every original scientific verdict.

## Inputs and identity

- Original uploaded `result(6).json`: 22,217,437 bytes; independently computed SHA256 **29ec484bf7e35e1d421ae4f12555f76e1eafc87e16eebf85f55553980730df1d**. No separate terminal result checksum was supplied; no external authenticity claim.
- Previous uploaded `training.json`: 16,257,800 bytes, SHA256 **318b0cfbca08f5c33f36b7514300186e63e3a404c8ee1aac7e1177e4de021f69**. Re-read here; all 20 embedded training rows and the review record match that original input exactly.
- Reviewed/executed source **7bcb08f480d0bda2dba5b1351442190001492782**. Upstream requirement remains sandyresearch/parcae@69284c13746e849104f738d6d1a347b1f457df76. No source, protocol, threshold, optimizer or model change in this audit.
- H1 reconstructed object SHA256 **f4e45835c2a9b38c2d5e0537f65996f006d26a7b0b837307858649fb3aa08328**, reconstructed producer-format file SHA256 **a7d878a5f35104581d7f9f5ec13887578e5ee031d72458b44d73f23a56561d03**; both match the result. Original H1 file bytes were not uploaded.
- Prior remote checkpoint read at df07985774fd4c4d9f2cdcdc782c94337617e603; PR22 was Draft/unmerged.

## Actual H1 endpoints

All values below are full-answer accuracy on the SAME 2,048 questions, four outgoing-carry strata of 512. Five seeds are 101/202/303/404/505. 81,920 evaluated responses are NOT independent questions.

|Seed|GPT@4,5941 updates|P2@2,5433 updates|P4@4,3822 updates|A@2,3000 updates|A@4,3000 updates|
|---:|---:|---:|---:|---:|---:|
|101|2039/2048|2018/2048|2011/2048|1957/2048|2013/2048|
|202|2033/2048|2028/2048|1968/2048|1859/2048|1931/2048|
|303|2037/2048|1898/2048|1978/2048|1644/2048|1772/2048|
|404|2037/2048|2043/2048|1969/2048|1706/2048|1832/2048|
|505|2016/2048|1841/2048|2030/2048|1904/2048|1940/2048|
|Mean|99.23828125%|95.9765625%|97.2265625%|88.57421875%|92.65625%|

Primary A4-P4 paired deltas in percentage points: +0.09765625,-1.806640625,-10.05859375,-6.689453125,-4.39453125. Mean **-4.5703125pp**, FAIL, not a ceiling condition. A's observed worst final seed86.5234375% is below P4's96.09375%; the previous three-seed worst-case improvement cannot be promoted to a general stability claim.

|Frozen comparison|Mean delta, percentage points|Recomputed status|
|---|---:|---|
|Equal-count budget A4-P4| -4.5703125|FAIL|
|Same3000 updates A4-P4| +0.517578125|FAIL|
|A4-GPT quality safeguard| -6.58203125|FAIL|
|A2-dedicated P2 safeguard| -7.40234375|FAIL|
|A4-A2 trained-horizon depth benefit| +4.08203125|PASS|

At step3000, P4 correct counts1879/1891/1813/1839/2013 give mean92.138671875%. A same-update advantage is below the1pp gate and has excessive seed regressions. A has27.42248062% more counted training cost per update. P4's predeclared budget endpoint3822 improves its saved trajectory mean by5.087890625pp relative to step3000. Do not generalize this to unlimited training always helping.

A depth gains:2.734375,3.515625,6.25,6.15234375,1.7578125pp; carry0 deltas all positive. Across five seed-answer sets it corrects626 and corrupts208 responses, net418 additional correct. Models train4: d2 is supervised early readout, NOT extrapolation beyond trained depth, monotone every-iteration reasoning or ACT. It does not replace failed external comparisons.

## Cost and uncertainty

Per-seed budget ceiling436285440000 counted FLOPs and frozen allocations unchanged; maximum unused fraction0.017643%. Same supported-operator budget is not equal sample exposure, optimizer work or hardware cost.

Full2048-question answer-generation counted FLOPs: GPT5179965440; Parcae d2(P2/A/P4 early)5667553280; Parcae d4(P4/A)8053063680. A2 costs9.412955% more than GPT; A4 costs55.465587% more. GPT has the highest mean quality and lowest saved generation counter in THIS configuration. No universal architecture ranking or measured hardware-speed superiority follows. A4 versus A2 adds42.090657% counts for its own4.08203125pp improvement.

Predeclared paired crossed bootstrap recomputed with5000 draws/seed731031: primary95% percentile interval **[-7.920166015625,-1.474609375]pp** (floating rounding applies). Diagnostic only with five seeds; no automatic population superiority/noninferiority acceptance.

## What was actually executed here

Auditor Python3.13.5/NumPy2.3.5; no Torch/model import, weights/logits loading, neural inference/backprop, optimizer, profiler or GPU. Full strict JSON and linkage, six own source/protocol copies matched both uploaded SHA256 and live pinned Git blobs; four inherited source copies matched declared hashes. Factory bytes were not freshly reconstructed, only their frozen declaration/training link used.

Independent reserved-pair allocation and H1 orientation/labels; all40 condition/category scores and invalid counts; all five gates, transition counts, descriptive statistics and fixed crossed bootstrap; probe/budget record arithmetic and finite NLL/timing checks. NLL is saved evidence, NOT recomputed without logits. Embedded original training records are identical, not rerun. HC/H2 allocations checked without creating their answer labels or scoring models.

35 .pt binaries, original prepared.json and evaluation_handoff_integrity.json were NOT uploaded. Do not claim independent binary audit, original preparation-byte audit or full auxiliary-handoff execution. Claude R02 missing per-worker read-time H1 checksum remains OPEN: deterministic endpoint reconstruction and matching answers do not prove absence of transient input changes. R03 duplicate-worker issue not modified. Native replay, resume equivalence and hardware efficiency NOT TESTED.

## Decision and next bounded instruction

Close this frozen MES-1 run and raw-result handoff. No repeat upload, prepare, training or H1 evaluation required for sealing. Current A0.25/0.75 recipe is a retained multi-exit mechanism observation, NOT a confirmed competitive candidate for automatic scaling. This updates the earlier prioritization; it does not declare all multi-exit methods or recurrence invalid.

Next: one focused Claude Code post-result review of existing predictions, budget/gates and interpretation. Pre-training APPROVE is not post-result approval; new result review NOT TESTED/DEFERRED. Grok was superseded by the owner's policy and is not an additional dependency.

Do not automatically launch MES-2 subtraction, MES-3 early exit, combinations, weight sweeps or GPU expansion. H1 is now viewed; no tuning on it followed by a fresh-holdout claim. HC/H2 remain unscored. Keep PR22 Draft/unmerged. Formal Oracle BLOCKED/NOT_READY, FORMAL_ACCEPTANCE_READY=False. No upstream/J1/Bench/R3/old-result changes.

Conversation audit bundle `Mythos_MES1_H1_Result_Audit_20261031.zip` contains byte-preserved inputs, actual independent audit code/log/results, reconstructed H1, reference sources, Chinese report and focused Claude result-review request. The request itself is not an executed review.
