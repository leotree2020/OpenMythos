# INIT-01 — completed user-reported replay / supplementary record (2026-10-30)

**User terminal output reports execution PASS and exact historical initialization replay PASS for all six seed/model targets, exit0.** This outcome review has not received, independently hashed or fully inspected the new result.json or six saved initial-state binaries. Therefore raw artifact audit remains NOT TESTED; this is not an independent training or metric replay.

## Consolidated tracking decision

INIT-01 / PR #16 and P1-R1 / PR #17 were overlapping tasks for the same original-initialization question. Both have now been run; there is no reason to request either again. **PR #17 / mini-mythos-p1r-init-origin-20261030 is the single follow-up entry**; this PR retains supplementary same-environment evidence. These are six unique historical initial conditions replayed twice, not twelve independent conditions, architectural progress, or a Claude/Grok cross-review.

The consolidated checkpoint is at `mini-mythos-p1r-init-origin-20261030:research/mini_mythos/init_replay/CHECKPOINT.md`, outcome commit **aaf09608c91793ab4569555ec172f3ef511191f0**. Its copied terminal evidence for both tools was committed at **41e812cd5fffa190a9d082acec7084aafd53b6e9**, path `research/mini_mythos/init_replay/evidence/user_supplied_init_dual_run_20261030.txt`.

This is documentation consolidation only. Neither PR is closed, merged or deleted; both remain Draft. Preserve both worktrees, result directories, original protocols and code unchanged.

## Source and expected behavior

- Repository leotree2020/OpenMythos; branch mini-mythos-init-replay-20261030; PR #16, base 4d1ecadc062e190a9bfc8b66b8e2d2962abb266a.
- Actual user-executed source: **c3ed3725beecb05f0bfb5f0819a7acd8d18098b5**.
- Original preregistration: 366c80b7cf0b9d84b0720581f6e102a423b784bd.
- Runner blob: 2dfdd689ad8c8a28cb24cd1609f80eed409be15c; SHA256 d3ede24ac178bcf76b9100e0032ffe8b8514caa01a6f1badb8108a9f5e99b76a.
- Upstream pin: sandyresearch/parcae@69284c13746e849104f738d6d1a347b1f457df76.
- Full preparation checkpoint, six helper tests, incompatible-runtime rejection and four launcher fixtures remain in Git history at c3ed3725beecb05f0bfb5f0819a7acd8d18098b5. Those tests are not additional native initialization results.

Purpose: reconstruct the historical initial state in the original CPU recipe and capture reusable initial artifacts. Original Linux Python3.12.3 / torch2.11.0+cpu / NumPy1.26.4 / einops0.8.0; GPT FFN60 and native Parcae FFN64; seeds42/20261029/20261030. Exact make(GPT), make(Parcae), pair_io, original preflight/count, then historical hash. Count includes a synthetic backward; no optimizer is constructed, no parameter updates, no text/Alice evaluation, no new training or GPU use.

## User-reported actual result

All three GPT rows list matching phases constructed, paired_io, after_preflight, after_count. All three Parcae rows list paired_io, after_preflight, after_count, but not constructed. All six initial_replay fields are PASS; final execution and initialization_replay PASS; exit0.

P1-R1's companion output reports the same phase behavior and localizes the Parcae pairing changes to lm_head.weight and transformer.wte.weight; probe-state preservation true for every model. Source inspection confirms the historical pair_io copies GPT input embedding, transposed output head and final LayerNorm into Parcae. Only changed bytes appear in the diff, so absence of LayerNorm from the changed list does not mean no copy occurred.

| Item | Status / evidence boundary |
|---|---|
| Historical original-producer recipe replay | PASS as reported in user output, six targets |
| Whole raw new result and reconstructed binaries | NOT TESTED by this review |
| Cause of Claude's six initial-hash mismatches | OPEN; original reviewer code/output not supplied |
| Fresh Grok/Claude cross-review | NOT TESTED / DEFERRED |
| Training/quality/efficiency or full resume equivalence | NOT TESTED by this initializer replay |

A standalone Parcae constructor is not the paired state recorded historically. This is a measured phase distinction, NOT evidence that Claude omitted pairing or that it explains its GPT mismatch. Do not blame Torch build differences without controlled evidence.

## Existing output; no repeat command

Result remains at `/workspaces/OpenMythos/mythos_evidence/init_replay_v1/result.json`.

USER-REPORTED SHA256 (not independently verified here):
`f5c3b716e0c337f0da3c7b77da16f1efc169006c123deff2f9aded14ac0a26ee`.

Do not rerun for sealing or create a third initializer experiment. The next primary handoff is the already-generated P1-R1 result.json, handled in PR #17; INIT-01's files stay preserved as supplementary evidence. No repeat request for the previously audited M2-T JSON.

M2-L/D/T scientific failures and A-M2L-01 are unchanged; A-M2L-02 is split into producer-path replay reported PASS and reviewer-cause OPEN. No model, upstream, old result, protocol or launcher edit, no new experiment, no merge. Formal Oracle BLOCKED/NOT_READY, FORMAL_ACCEPTANCE_READY=False; no G2 REAL, J1/Bench/R3 change or GPU allocation.
