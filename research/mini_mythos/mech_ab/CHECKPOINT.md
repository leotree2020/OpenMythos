# MECH-AB checkpoint — 2026-10-30

## Current deliverable and goal

User explicitly requested implementation after selecting independent mechanism comparisons. Read live PR19 and checkpoint at78d9c49112f5e1299767d450593f3db08feaf7c6 before development. R1-B qualification FAIL remains historical; final test/depth benefit there remain NOT TESTED. This new stage is mechanism exploration, not another difficulty search, initialization audit, or relabelled old experiment.

**Implemented:** P4 native four-step control, A same-trajectory exit2/4 supervision, B whole-iteration damping. **Local component/fixture checks PASS. Pinned-native compatibility gate and nine native training runs NOT TESTED. No mechanism-quality result yet.**

## Git and isolation

- Repository leotree2020/OpenMythos; new branch mini-mythos-mech-ab-cpu-20261030, based on PR19 HEAD78d9c49112f5e1299767d450593f3db08feaf7c6. Keep Draft; no old PR merges or branch resets.
- Protocol committed FIRST atafb21e5409264a9b609ab727fd1e640d35a2700c before any native result. Code-only delivery through4b5f2b32783781d94d308e53c6593404bca5ade4. The current PR HEAD additionally carries this checkpoint/preparation evidence.
- Only new directory research/mini_mythos/mech_ab is changed. Original Parcae source69284c13746e849104f738d6d1a347b1f457df76, old factory, task, protocols, scores, J1/Bench/R3 untouched.
- Live GitHub directory metadata confirms all six published blobs equal the bytes actually tested locally: protocol233fbb67b9c3562885121bc1d861226fa2da1201; wrapper e1d531d7f2940602442e85625f6fd094fc59a19c; metrics a935f19f4d694c12a9574b5454bdd19dc4181a1a; runner22cb2fa359b27f45fb74990b3e64029b63e036d0; tests c27dea09ff05c0ebf41cba5c83a2885213837242; launcher f3d7f2f3d3d74758747b540971fef1958fffbc94.

## Implemented experiment

All arms retain the exact original paired Parcae configuration/initial weights; explicit [0,4] controls unrolling without changing config mean_recurrence, layer IDs or initialization. All train3000 updates/batch32 from scratch for seeds42,20261029,20261030; same sampled data and training RNG.

P4: native transition, final-only CE. A: native transition,0.25*CE(exit2)+0.75*CE(exit4) from ONE trajectory, same output modules, no detach. B: h_old+0.5*(native_candidate-h_old), final-only CE. No added trainable parameters. Separate scoped PyTorch hooks on adapter input and last core output are removed in finally; no upstream method replacement or global hook. A's auxiliary suffix is read after the final forward under fork_rng, preserving subsequent caller RNG.

Reuse R1-B's existing10000 canonical training pairs and1024 balanced development pairs; reserved test stays unused. New code does not call the old qualification gate or impose a90% upper capability bound. Only a mathematical >99% control ceiling is disclosed for the new1pp exploratory improvement screen. The already-viewed development set is not a confirmatory holdout.

Each arm runs in its own child process. Save all nine final model/AdamW/RNG states, batch-index arrays, initial/final hashes, every500-step progress, full loss/norm/RNG traces, all18 development predictions at depths2/4, per-category accuracy, teacher-forced answer CE, correction/corruption counts, supported-op compute, descriptive timing and worker-process peak RSS. Process RSS is lifetime usage including imports/evaluation, not isolated training tensor memory. Teacher-forced CE is separate from prompt-only free generation. Auxiliary and damping costs are not claimed free; supported counters may omit elementwise/optimizer work.

Primary A/B vs P4: mean d4 exact-answer gain>=1pp, each seed loses<=1pp; separate extra-depth screen, separate cost record. This is same data/updates, NOT equal compute. Equal-compute efficiency and fresh held-out confirmation are NOT TESTED. Full criteria and stopping in PROTOCOL.md. All9 arms run regardless of another arm's scientific result; numerical/source errors retain partial evidence and block completion. No automatic hyperparameter/depth search or C/D/E/combined intervention.

## What actually ran in this development session

Local environment: Python3.13.5, torch2.10.0+cpu, numpy2.3.5, einops0.8.2, CPU. No package/GPU purchase, no Codespaces terminal connection. A public raw-source download failed DNS; primary source was read through the live GitHub connector. Published byte identities verified via Git blobs.

| Check | Actual result | Scope |
|---|---|---|
| Python AST / Bash syntax | PASS | All new Python and launcher |
| Component mathematics/plumbing |16/16 PASS|Affine/tanh fixture, not a new Transformer or native Parcae result |
| Nine-worker-path integration |PASS|Fixture only,3 updates each; save/load metadata, eval/summary and RNG pairing; NOT9x3000 native training |
| Launcher evidence preservation |7/7 PASS|PASS/FAIL/BLOCKED/wrong experiment/corrupt JSON/partial directory/log-only, existing bytes unchanged |
| Incompatible actual local runtime |Expected rejection PASS|Process exits2 before source/native construction, rows empty; actual run status BLOCKED, not native PASS |
| Published source identity |PASS|Remote blobs listed above match local checked bytes |
| Native disabled-wrapper logits/loss/gradient equivalence |NOT TESTED|Executable gate automatically precedes all training in original runtime |
| Native nine-arm quality/cost results |NOT TESTED|No scores invented or borrowed from fixtures |
| Fresh held-out/equal-compute result |NOT TESTED|Outside this stage |
| Grok/Claude review |NOT TESTED / DEFERRED|No report yet |

Local fixture checks cover disabled logits/loss/gradients/None patterns/RNG, same-trajectory auxiliary values, auxiliary-only core gradients, no added parameters, independent whole-iteration interpolation, suffix/softcap reuse, no state mutation, error cleanup, invalid inputs, prompt-only unconstrained decoding, quality/depth/ceiling separation, transition accounting and incomplete result rejection. Fixture optimizer updates exercise plumbing only; no native model was trained.

## One next execution

Fetch this branch and create an isolated worktree at the delivered PR HEAD only if absent, verify exact path/HEAD, then:

    bash research/mini_mythos/mech_ab/run_codespaces_cpu.sh

Defaults reuse /workspaces/mythos-m2-cpu312/bin/python and /workspaces/mythos-parcae-pinned. No installation or downloads. Output:

    /workspaces/OpenMythos/mythos_evidence/mech_ab_v1/result.json

Existing results are read only; partial directories/logs are preserved without retry/resume. Native gate fails -> no optimizer updates. Exit0=complete and both primary screens PASS;1=complete and any primary FAIL;2=operational/native block or ceiling (inspect reason). A result FAIL does not mean a process crashed. Hand off only this new JSON/console first; do not rerequest already audited R1-A/R1-B/P1-R1/M2-T files.

## Review, unresolved items and erratum

Focused reviewer: ensure native alpha1/aux0 output AND gradients match; intermediate exit shares trajectory/parameters; no auxiliary RNG drift; damping acts before/after the whole iteration; fair same-start/data/update comparison with actual extra compute; no hidden test access; source/partial-output protection. New positive findings require actual independent review before promotion/merge. A-M2L-01 inactive tensors are intentionally not fixed; A-M2L-02 reviewer mismatch remains OPEN separately.

Documentation erratum to prior PR19 wording: carry3 exceeds carry2 in TWO Parcae seeds, not all three. Counts are209>189,250>247,244<247. Original raw metrics and qualification FAIL remain unchanged. This is not a new scientific result or a reason to alter old acceptance.

Formal Oracle stays BLOCKED/NOT_READY, FORMAL_ACCEPTANCE_READY=False; no G2 REAL or upstream/J1/Bench/R3 edits. C low-rank phase adapters, D dual-state architecture and E stopping remain planned, NOT IMPLEMENTED/NOT TESTED; this delivery is only the agreed first P4/A/B batch.
