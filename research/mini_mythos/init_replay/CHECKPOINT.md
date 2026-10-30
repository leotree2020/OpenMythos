# P1-R1 — consolidated initializer outcome checkpoint (2026-10-30)

**Original-producer initializer replay: PASS as reported in the user's six-row terminal output. Probe preservation: PASS as reported. Claude discrepancy root cause: OPEN. Raw new-result byte audit: NOT TESTED.** This update is source inspection plus review of pasted result lines, not an independently executed model experiment or a full JSON/binary audit.

## 1. One tracking entry, no duplicate continuation

INIT-01 (PR #16) and P1-R1 (PR #17) were both prepared for substantially the same initializer question and have now both been run by the user. This duplicated task preparation was unnecessary; the user did not run the wrong command. Use **P1-R1 / PR #17 as the consolidated follow-up entry**, retaining INIT-01 as supplementary same-environment corroboration. These are six unique historical seed/model targets replayed twice, NOT twelve independent initial conditions or an independent AI cross-review. Stop both bounded native replay tasks; no third implementation or repeat run is requested.

This administrative consolidation does not merge, close or delete either PR, either branch, worktree or result directory. Both PRs remain Draft. The original protocols and runners are unchanged.

## 2. Purpose, source and history

Purpose: establish whether the original native GPT/Parcae initial-state recipe reconstructs the historical M2/M2-L identities before another from-scratch causal comparison. This is not a model-quality or efficiency experiment.

- Repository: leotree2020/OpenMythos.
- Consolidated branch: mini-mythos-p1r-init-origin-20261030; Draft PR #17; base 4d1ecadc062e190a9bfc8b66b8e2d2962abb266a.
- P1-R1 executed code: **a097562ca8085eecd49c53f59a8ad83bc66ce066**. Protocol frozen first at ce46fc2a7d053e609c94fed7ecf67ba3f6bc171d. Runner blob 6d4e65424d52145d44a275a0012b56798aec913c, SHA256 d6bf602f2f714b9d232da927ebc49a684d40fe1289005dc4531970681b759070.
- INIT-01 executed code: **c3ed3725beecb05f0bfb5f0819a7acd8d18098b5**; branch mini-mythos-init-replay-20261030; Draft PR #16. Initial protocol 366c80b7cf0b9d84b0720581f6e102a423b784bd.
- Native source pin: sandyresearch/parcae@69284c13746e849104f738d6d1a347b1f457df76.
- P1-R1 preparation checkpoint, eight helper tests and exact original preparation limits remain in Git history at a097562ca8085eecd49c53f59a8ad83bc66ce066:research/mini_mythos/init_replay/CHECKPOINT.md. They are not additional native run results.
- Copied user output and scope: [evidence/user_supplied_init_dual_run_20261030.txt](evidence/user_supplied_init_dual_run_20261030.txt), committed at **41e812cd5fffa190a9d082acec7084aafd53b6e9**. This is NOT a reconstructed result.json or independently captured stdout.

## 3. Inputs, environment and frozen expected result

Three seeds 42, 20261029, 20261030; official GPT FFN60 and original Parcae FFN64 configuration. Follow exact original factory order: make GPT, make Parcae, pair_io, original per-arm preflight, original synthetic count forward/backward, then historical full-state hash. Compare with both immutable M2 and M2-L records, including old pilot SHA256 c5be0f6da8eab77ab499ad97a3aaf318633d2d44f234083165ffcacc3b26d7bb.

Pinned source requirements: Linux Python3.12.3, torch2.11.0+cpu, NumPy1.26.4, einops0.8.0, FP32, single CPU thread. The reviewed source fails on incompatible builds, altered inputs or upstream. PASS output is evidence that the runner reported those preconditions met; the complete environment dump has not been independently received in this update.

Expected: all six historical full-state/shared-IO/preflight/count identities match exactly; permitted pairing scope only; probes preserve model state and caller CPU RNG; saved tensor values finite. No optimizer construction/step, training/validation/test/Alice batches, new dependencies, upstream edits or GPU use. Synthetic backward is present solely at the original measurement boundary; do not call this a zero-computation audit.

## 4. Actual user-reported outcomes

| Model, across all three seeds | Native constructor matches history | After pair_io | After preflight | After count | Pairing changed tensor bytes |
|---|---|---|---|---|---|
| GPT | true | true | true | true | none |
| Parcae | false | true | true | true | lm_head.weight; transformer.wte.weight |

INIT-01 independently printed the same phase pattern for the same six targets and exit0. P1-R1 printed history_match=true and probe_state_preserved=true for all six rows; final execution, historical_init_status, probe_preservation_status and comparison_status all PASS; exit0. The classifier also requires probe RNG preservation, finite states, bounded pairing scope and matching old shared-IO/preflight/count results. Those raw fields remain uninspected here; do not call the status-line review a complete replay audit.

| Acceptance item | Status | Evidence level |
|---|---|---|
| Original-producer recipe reconstructs six historical initial states | PASS as reported | Both terminal excerpts; historical hash bytes not yet independently read |
| Probe model-state preservation | PASS as reported | Six per-row booleans and classifier result |
| Probe caller RNG preservation | PASS as reported | Included in aggregate classifier; individual RNG hashes pending |
| Phase/tensor localization | Supported by terminal output and source | Three Parcae pairing differences restricted to input/output weights |
| Original JSON byte identity and complete field consistency | NOT TESTED | User-reported SHA256 only |
| INIT-01 six reconstructed initial binaries | NOT TESTED by this reviewer | No raw binary inspection in this update |
| Claude's original six initialization mismatches explained | OPEN | Original reviewer procedure/output absent; no controlled cross-build comparison |
| New independent Grok/Claude review | NOT TESTED / DEFERRED | These two tools are not separate AI reviewers |
| Full training/resume/metric reproduction or quality improvement | NOT TESTED here | Zero optimizer updates; old scientific FAIL results unchanged |

## 5. Interpretation: what changed and what did not

Source-confirmed pair_io copies GPT's input embedding into Parcae, transposes and copies the GPT output head, and copies final LayerNorm state. Changed tensor bytes reported here are only lm_head.weight and transformer.wte.weight. Copying an already equal normalization state need not produce a changed hash; do not infer that normalization copying was skipped.

The Parcae native-constructor false flag is **not a failed replay**: the frozen historical target is the paired/probed state, not the standalone native-constructor state. GPT's own values are unchanged by pair_io and already match history at construction. Original probe/count code therefore need not be blamed for initial-state mutation based on the supplied observations.

**Supported inference:** skipping or changing the prescribed pairing can produce a standalone Parcae-vs-historical mismatch. **Not established:** that Claude actually skipped it, that this explains Claude's GPT mismatch, or that the CPU versus CUDA-enabled wheel caused any mismatch. GPT already matches without pairing in this run, so missing Parcae pairing alone cannot explain all six reviewer failures.

Track A-M2L-02 as two subquestions, without erasing historical failures: producer-recipe reconstructability PASS as reported; cross-review mismatch cause OPEN. The latter must not trigger an open-ended repeat-replay campaign. No claim of cross-build bitwise equivalence or universal native-model reproducibility.

## 6. Existing result identities and single next handoff

USER-REPORTED ONLY, not independently calculated in this review:

- Primary P1-R1: /workspaces/OpenMythos/mythos_evidence/p1r_init_v1/result.json
  SHA256 **bf2b75fbcc49179cbdb059916a744ae8fa4cc682675bd802b662b32e791126ea**.
- Supplementary INIT-01: /workspaces/OpenMythos/mythos_evidence/init_replay_v1/result.json
  SHA256 **f5c3b716e0c337f0da3c7b77da16f1efc169006c123deff2f9aded14ac0a26ee**.

**Next only:** hand off the existing P1-R1 result.json for byte identity and six complete phase records; retain INIT-01 output without re-executing either tool. If reviewer files later become available, inspect their existing procedure against this recipe; do not speculate or launch a build matrix by default. No need to resend the already-audited M2-T JSON. No third initialization diagnostic or automatic new training is authorized by this checkpoint.

## 7. Unchanged boundaries

M2-L quality FAIL, M2-D depth benefit FAIL and M2-T intervention/extra-depth FAIL remain separate negative results. A-M2L-01 inactive paths remain unchanged. Prior binary/reviewer handoffs and resume-equivalence limits remain explicitly scoped.

This outcome update changes documentation/evidence/PR descriptions only. The reviewer performed repository reads and status interpretation, not native model construction, backward, raw-result hashing, binary loading, training, source repair, GPU rental or merge. Parcae, Bench, J1, R3, models and frozen protocols/runners are untouched. Formal Oracle stays BLOCKED/NOT_READY, FORMAL_ACCEPTANCE_READY=False; no G2 REAL.
