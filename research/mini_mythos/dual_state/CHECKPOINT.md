# D1 checkpoint — dual-state profiling implemented, native results NOT TESTED

2026-10-31. Experiment MYTHOS-D1-DUAL-STATE-PROFILE-V1.

## Current decision

Owner explicitly requested trying D to observe its measurement characteristics. Implemented a separate bounded dual-state study, not another A/C tuning attempt. Prior C1 fixed-recipe FAIL is preserved and its post-result Claude review remains DEFERRED. No claim that the earlier result audit authorized D; this owner's later request is the new authorization.

Development and fixture pipeline complete. **Original-runtime native preparation,12 model-training trajectories and D measurement results are NOT TESTED. Claude Code D review PENDING.** No new model advantage, candidate acceptance, hardware efficiency or native production execution claimed.

## Git and boundaries

Repository leotree2020/OpenMythos; branch mini-mythos-d1-dual-state-profile-cpu-20261031, based on C1 checkpoint4790d0cfd34c90df7be64a18eccd02deb3b74a92. New files ONLY under research/mini_mythos/dual_state/. No existing experiment code/results/protocol edited. Draft/unmerged.

**Executable/review pin:596af7f8997ca793e880a6e1d80c25c7b2043329.** Six published own source/protocol blobs exactly match locally tested/read bytes. Subsequent checkpoint/review text does not enter runtime identity. Run the original prepared pin throughout the study, not a later documentation HEAD.

Protocol FIRST committed355d0f5478f28d89e4e75317bf66c09c85077540, before implementation/model results. Read-only upstream sandyresearch/parcae@69284c13746e849104f738d6d1a347b1f457df76. Reviewed live native forward/iterate/core source and prior MECH-AB wrapper, plus C1 checkpoint before development. Reuse pinned M2 factory, old R1-B task, MECH-AB readout/evaluation and C1 initialization/snapshot utilities. Own source plus eight inherited paths are hash-bound. C1 helper reuse does NOT activate C adapters or C1T allocation/scoring.

Inherited local copies came from the retained C1 development artifact. Factory full bytes are not in that local artifact; fetched source was displayed with output truncation, so no full-factory-byte verification is claimed here. The production runtime checks its established SHA before importing it. No network dependency install or upstream checkout mutation performed.

## Mechanism, not a name change

Use original shared transition F(h,u). P4 performs four native calls with fixed e. D0/D1 keep z (working latent) and a (answer latent), initialize both to the original sampled h0, then execute TWO cycles:

    D0: z=F(z,e);   a=F(a,z)
    D1: z=F(z,e+a); a=F(a,z)

D1 reads the old a for feedback; answer update reads the newly updated z. Each cycle costs TWO native core calls; max training horizon stays FOUR calls, not eight. Original causal prefix handling, shared native suffix and final-only CE remain. No learned gate, damping, adapters, auxiliary supervision, new trainable parameters, inactive-path repair or cross-example memory. D0 is a dual-state no-feedback ablation, not native P4.

TRM's official README inspired separate latent/answer updates; this is NOT TRM reproduction, nor a claim that latent a equals text reasoning or the correct target. We keep Parcae's own transition and causal task interface. D-vs-P4 is a state/routing-package comparison, not a perfectly isolated state-count causal experiment; D1-vs-D0 isolates the feedback addition for this variant.

## Fixed bounded study

GPT/P4/D0/D1 x seeds2101/2202/2303 =12 trajectories,3000 updates each,batch32,original AdamW and clipping. Same data/updates,NOT equal compute. Preserve known8320 inactive paths; report gradient presence/nonzero separately. GPT remains an external reference. No historical A/C numbers used as new head-to-head measurements.

Use only original already-viewed19977-row train and1024-question development split. No H1,HC,H2,C1T or new holdout use. Save36 full model/optimizer/RNG/index snapshots at300/1500/3000. No checkpoint/seed selection based on scores.

After training:21 final free-generation conditions (GPT@4; P4/D0/D1@2,@4),21504 repeated answers on SAME1024 questions.36 checkpoint profiles on fixed32 development prompts;27 same-prefix latent profiles (nine Parcae jobs x three snapshots);six final dual-state intervention groups. Same-prefix profiles provide state RMS/change/separation/cosine and next-token confidence/entropy; full-answer transition counts compare two separate generation policies, not in-place answer editing. Zero-state interventions only assess local next-token sensitivity. No-op must match exactly. Logical state bytes are NOT peak memory or autograd storage.

Exploratory screens D0-P4,D1-P4,D1-D0: mean>=1pp and each loss<=1pp,ceiling>99% BLOCKED. Execution completion and screens are separate. **Evaluation exit0 means complete measurements, even if all exploratory screens FAIL. Candidate selection is NOT ASSESSED.** Equal-budget/fresh-test/statistical/hardware superiority and depth extrapolation NOT TESTED.

## Actually executed in this development session

Local Python3.13.5/torch2.10.0+cpu/numpy2.3.5/einops0.8.2; not original production environment. All numerical development tests use explicitly labelled affine/tanh fixtures, not native GPT/Parcae.

|Check|Actual result|Scope|
|---|---|---|
|Python3.12 AST and Bash syntax|PASS|four Python source files and launcher|
|CPU unit tests|25/25 PASS|routing equations,logits/loss/gradient/RNG equivalence against fixture references,causality-check plumbing,hooks,error cleanup,interventions,metrics,serialization|
|Full fixture phase pipeline|PASS|12 train/12 evaluation paths,36 tiny optimizer updates,36 snapshots,21 final conditions,36 profiles,27 latent profiles,six intervention groups|
|Shell evidence behavior|18/18 PASS|existing/partial/corrupt evidence,missing environment,invalid phase; no production model launch|
|Published local/remote source identity|6/6 PASS|protocol and five code files; Git blob match|
|Attempted original-runtime entry locally|BLOCKED as expected|Python3.12.3 requirement,before native construction; no waiver/install|
|Native D implementation/costs/model quality|NOT TESTED|requires owner's original Codespaces environment|
|Claude D code review|PENDING|old C1/MES approvals do not cover D|

The first unit run had one incorrect TEST expectation: it expected the untouched random a0 at the first working update to require gradients. Corrected the test to require gradients after each state actually has its first differentiable update; no model/protocol change. Initial failing log retained. Final gradient-through-both-state and independent-unroll tests pass. No native result was produced in either run.

Fixture pipeline mocks context and dispatch; it is not full original subprocess/native acceptance. Data fixture uses a subset of existing train/development only; no reserved labels. Existing error paths are preserved, not reclassified as successful production runs. Logs/scripts are in Mythos_D1_Dual_State_Development_20261031.zip.

## Next bounded action

Create separate /workspaces/mythos-d1-20261031 at596af7f ONLY if absent,verify HEAD/root,run ONLY:

    bash research/mini_mythos/dual_state/run_codespaces_cpu.sh prepare

Output /workspaces/OpenMythos/mythos_evidence/dual_state_v1/prepared.json. Existing Python /workspaces/mythos-m2-cpu312/bin/python and upstream /workspaces/mythos-parcae-pinned. No installation/download/GPU. Native preflight compares P4 to unmodified native path and D0/D1 to explicit two-state native-module unroll for all three seeds,lengths6/9,depths2/4; checks gradients,RNG,causal-prefix invariance,no-op,counts,starting identities. Zero optimizer updates. Any mismatch stops and preserves evidence.

Provide fixed source plus the actual prepared.json to Claude Code when available. Code review may use CPU tests and no-update probes, not train/evaluate or any test-target scoring. No generic project re-audit. Actual APPROVE plus owner's acknowledgement precedes separate train; separate evaluate follows completed12-run barrier. No hand-started workers or automatic retry/resume. Do not rerun old MES/C1 preparation or request old result files.

Formal Oracle BLOCKED/NOT_READY,FORMAL_ACCEPTANCE_READY=False. No G2 REAL,upstream/J1/Bench/R3 changes,automatic merge,parameter sweep,GPU scale-up or E. ChatGPT/Claude attribution and pending historical reviews remain explicit.
