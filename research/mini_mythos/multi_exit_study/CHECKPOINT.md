# MES-1 checkpoint — GPT interface fix, 2026-10-31

## Current state

**User's original-runtime prepare at a8f329ed3ae7e0e55a703dfaee9c2ce56339b953 is BLOCKED by a real MES/GPT interface bug. The scoped fix is committed and locally regression-tested. Original-runtime prepare AFTER this fix remains NOT TESTED. Twenty native training trajectories and H1 model evaluation remain NOT TESTED. Actual pre-training independent review remains DEFERRED.** This is not a model-quality failure, and no training result has been produced.

The previous preparation checkpoint remains available at the original delivery commit. Existing MECH-AB/C results, protocols, original JSON handoffs and old initialization evidence remain unchanged. Do not restart any of those tasks or infer that their models failed from this exception.

## 1. Sources, Git and incident

Repository leotree2020/OpenMythos; existing Draft PR22 and branch mini-mythos-mes1-budget-holdout-cpu-20261031, base4cf60b053c7b9c2e89e64646cd986d33a34a7657. No new PR or branch is needed for this integration fix.

Original delivery a8f329ed3ae7e0e55a703dfaee9c2ce56339b953; protocol preregistered at c74728c3efb6f27e29aacf146d719e37c5dbbd1c. Upstream sandyresearch/parcae@69284c13746e849104f738d6d1a347b1f457df76 remains unmodified.

User terminal reports `/workspaces/OpenMythos/mythos_evidence/mes1_v1/prepared.json`, SHA256 `5d1dfb655170b8e6bfb5c98f507b490266e708b65231fc053d0906cd2169589f`, status BLOCKED/exit2. The raw prepared.json was NOT uploaded, so this is terminal-reported identity, not an independently verified file hash. No optimizer updates occur in prepare; H1 model evaluation was not reached.

Root cause confirmed from live pinned source: GPT.forward defines `outputs` only when labels are absent but returns that variable when return_logits=True. MES requested labels and return_logits=True in BOTH GPTPath.forward and the subsequent preparation CE check. The old GPT fixture wrongly permitted that joint request. Existing m2_matched.call already separates the two supported paths. This is an integration/test-coverage mistake, not a reason to patch the pinned upstream model or change architecture.

Evidence: [evidence/gpt_interface_fix_20261031.json](evidence/gpt_interface_fix_20261031.json), first saved at3e44ced7724fcdb88aad93b2295d2e10ae8b4b92.

## 2. Fix and unchanged scientific design

- Runtime fix9833b407c31d4297b161074897749d8f872301e0: GPT training makes ONE native labelled loss call with return_logits=False. Generation makes ONE no-label logits call. Native CE, masking, gradients and counted training path are retained.
- Prepare fixa252aad2f67083008e970b800fdfc826f6ab55d3: separate no-grad native loss/logits calls for the masked-CE equivalence check; same RNG seed, caller RNG and training mode restored. This check is outside the counted training probe. Its results are saved under gpt_objective_checks and propagated to the final report.
- Regression testscf233e1629df4a43a7ba0ac337c0ab035d5ac03d: strict GPT interface, one-call training/inference, exact loss/gradient/RNG, probe cost, and full prepare fixture across all five seeds/four arms.
- Published tested code blobs: runtime5cec3241bb8a45f6559c9505793c598e6768390e; runner1f3c330d66d6e5c0a9d4ef647b09773972a2fa14; tests923993ae2d365e0624932f1b9d24542645cb6f20.

Protocol, policy constants, launcher, factory, task, upstream and reused A remain byte-unchanged. No threshold repair, budget relaxation, removed test or catch-and-ignore bypass.

Four arms GPT/P2/P4/A, five new seeds101/202/303/404/505. A remains0.25 exit2 +0.75 exit4 on the SAME four-step trajectory/shared suffix. Common supported-op budget436285440000; frozen steps GPT5941/P2=5433/P4=3822/A3000 with<=0.1% integer slack, still checked by native runtime profiling. Same budget is not equal sample exposure or hardware work. No B/C/D/E combination or inactive-path repair.

Save step3000 and budget endpoint,35 deduplicated model/AdamW/RNG/index snapshots. H1=2048 reserved pairs is scored only after all20 runs and evidence barriers; HC1024/H2=2048 remain unopened. Primary equal-budget A4-P4 mean>=1pp and every seed loss<=1pp, with mathematical ceiling disclosed; other comparisons separate. Bootstrap diagnostic only, no automatic significance/noninferiority claim.

## 3. Checks actually executed for this fix

Local runtime Python3.13.5/torch2.10.0+cpu, not production Python3.12.3/torch2.11.0+cpu. No dependency installation, GPU allocation, native learning, original-runtime budget confirmation or user Codespaces shell access claimed.

|Check|Result|Scope|
|---|---|---|
|CPU components and prepare fixture|29/29 PASS|Strict interface fixture; five-seed/four-arm preparation plumbing; NOT native preparation|
|Before/after regression|PASS|Both targeted tests fail with original UnboundLocalError on old source and pass on fixed source|
|Pinned GPT.forward method|40/40 PASS|Exact byte-verified source method on tiny component doubles; old error, safe loss/logits, exact base gradients; NOT full native GPT construction|
|Fixture train/evaluate pipeline|PASS|20 training paths,20 evaluation paths,40 conditions,35 safe snapshots,90 FIXTURE optimizer steps|
|Launcher evidence preservation|21/21 PASS|Existing PASS/FAIL/BLOCKED, partial and corrupt outputs retained|
|Original-runtime prepare after fix|NOT TESTED|Must use user's existing pinned CPU environment|
|Twenty native trajectories/H1 quality|NOT TESTED|No new native model scores|
|Grok/Claude review|DEFERRED|Local checks are not an independent AI review|

Source-method regression uses pinned GPT file Git blob33ee78728306d6f64ca1cf50c861269c0748ad48, extracts its unedited forward method, and binds tiny embedding/linear fixtures. It covers5 seeds x2 lengths x2 tie settings x2 softcap settings; no optimizer. Do not label this full original-runtime acceptance. The source copy's trailing newline serialization was corrected to match the Git blob before this test; upstream bytes in the actual repository were never changed.

## 4. Single next action: retry prepare without deleting the failure

Retain BOTH old worktree `/workspaces/mythos-mes1-20261031` and old output `/workspaces/OpenMythos/mythos_evidence/mes1_v1` unchanged. Existing launcher intentionally reads old phase results, so pointing it at that directory will only repeat the BLOCKED report.

Fetch the same branch, create `/workspaces/mythos-mes1-gptfix1-20261031` at the fixed delivered HEAD only if absent, verify exact HEAD, then run:

    MES1_OUTPUT_DIR=/workspaces/OpenMythos/mythos_evidence/mes1_v1_gptfix1 bash research/mini_mythos/multi_exit_study/run_codespaces_cpu.sh prepare

The new output is `/workspaces/OpenMythos/mythos_evidence/mes1_v1_gptfix1/prepared.json`. Use this SAME explicit output override for future train/evaluate; never silently fall back to mes1_v1. No install/download/retry loop. Existing new outputs also stay read-only. Preparation PASS means source/runtime/objective/budget readiness, not model quality.

Keep the original training review requirement: actual focused report plus owner acknowledgement via --review-report/--reviewer/--review-approved. Missing review remains DEFERRED; never fabricate a report or count this self-test as cross-review. Do not train automatically after prepare, score H1 early, or waive a budget mismatch.

## 5. Boundaries

Old A primary FAIL, old results and both A-M2L limitations remain. MES-2/3, full independent native replay and formal efficiency acceptance remain NOT TESTED. Keep PR22 Draft/unmerged. Formal Oracle BLOCKED/NOT_READY, FORMAL_ACCEPTANCE_READY=False; no G2 REAL, J1/Bench/R3 changes, upstream patches or GPU expansion.
