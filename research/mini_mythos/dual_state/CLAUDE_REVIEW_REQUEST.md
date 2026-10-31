# Claude Code — D1 focused pre-training review

Review repository leotree2020/OpenMythos at executable commit596af7f8997ca793e880a6e1d80c25c7b2043329, diff from4790d0cfd34c90df7be64a18eccd02deb3b74a92. New directory research/mini_mythos/dual_state/. Later CHECKPOINT/review text is documentation only. Previous C1/MES approvals do NOT cover this code. Owner authorized an independent D mechanism profiling study; failed C/A recipes and pending C1 result review remain unchanged.

## Required checks

1. Read PROTOCOL.md, dual_state.py, measurements.py, run_cpu.py, test_d1.py and launcher, plus necessary unchanged dependencies. Confirm no upstream edits or A/B/C activation. Code must use original pinned Parcae transition/suffix, not silently replace the architecture or TRM training recipe.
2. Check equations and order: D0 z=F(z,e),a=F(a,z_new); D1 z=F(z,e+a_old),a=F(a,z_new). z/a start at the original sampled h0, no detach. Two cycles=FOUR native calls. P4/native identity, reference-unroll gradients/RNG, state reset each prefix, causal input handling, hook cleanup and no added parameters. The original random initial a0 need not require gradients before it is updated.
3. Verify data/initialization/optimizer/sample and RNG pairing. Twelve jobs GPT/P4/D0/D1 x2101/2202/2303,3000 updates,checkpoints300/1500/3000. Same data/steps is NOT equal compute. Original8320 inactive paths stay disclosed. Pin remains sandyresearch/parcae@69284c13746e849104f738d6d1a347b1f457df76.
4. Check measurements: old1024-question development only; no reserved H1/HC/H2/C1T scoring. Final full-answer d2/d4 predictions are different autoregressive policies, not same-answer editing. Same-prefix latent profile uses SIX prompt digits only; final readout must match native suffix. Work/answer separation is not semantic proof; P4 z=a is bookkeeping. Logical state payload is not actual peak memory. No-op intervention exact; zero_z and zero_a act only before second cycle on final weights, no optimizer step. Local next-token sensitivity is not general reasoning proof.
5. Check full snapshot metadata/file/full-state binding, no evaluation before all12 complete jobs, immutable data-byte parsing, duplicate-worker evidence retention, report provenance and phase guards. All36 full snapshots and21 final conditions must be accounted for. GPT loss/logits remains the safe split API. No resume equivalence claim from save/load.
6. Check exploratory screens and summaries. Candidate selection remains NOT ASSESSED; exit0 signifies complete measurements even if screens FAIL. No new equal-compute/fresh-test/statistical advantage claim. No threshold/rank/learning-rate/seed selection after results.

## Evidence and permitted actions

Development logs report25 fixture unit tests,18 launcher tests,and a full affine/tanh pipeline with36 tiny optimizer updates,36 snapshots,21 final conditions. These are NOT native model quality results. Local Python3.13.5/torch2.10CPU differs from production3.12.3/2.11.0+cpu. Production local entry was blocked before native models. Do not inherit PASS without checking.

Actual new preparation, when the owner has run it:
/workspaces/OpenMythos/mythos_evidence/dual_state_v1/prepared.json

No prepared bytes or checksum exist in this development delivery. If an attachment arrives,read/hash it directly; inability to access /workspaces does not prove attachment absence. If it truly is unavailable,explicitly retain prepared-file verification NOT TESTED and state the scope of any code approval. Do not request another prepare run as a substitute for an existing file.

Allowed: read source/evidence,necessary CPU component tests or no-optimizer native synthetic probes; report environment deviations. Do NOT run production prepare/train/evaluate,generate/score reserved targets,modify source/protocol,install dependencies,GPU,commit,push,merge or launch workers by hand. No need to re-audit the whole project.

Return a full Markdown report with reviewed commit/files,findings and line references,actual commands/results,untested limits,and APPROVE / CHANGES_REQUIRED / BLOCKED. APPROVE means code may enter later owner-authorized training,NOT that D improves quality. Stop after reporting. Formal Oracle stays BLOCKED/NOT_READY,FORMAL_ACCEPTANCE_READY=False;no G2 REAL. Claude Code is the assigned reviewer;there is no additional Grok dependency.
