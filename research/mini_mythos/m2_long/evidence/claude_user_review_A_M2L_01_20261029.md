# A-M2L-01 — user-supplied Claude independent review (2026-10-29)

## Provenance and evidence boundary

The project owner pasted the following Claude report into the conversation. This file preserves that report as a **user-supplied reviewer statement**, not a connected Claude execution or a new ChatGPT experiment. The six underlying reviewer files have **not yet been received or opened in this review**. In particular, `352379ab…` is an abbreviated claimed preregistration digest, not enough to verify its byte identity or timing.

The previous GitHub state read before recording was `76c4075d63da40f23ac019bbadcc71c427267179`, PR #13 Draft/unmerged. The existing archive audit and original training evidence are preserved. Training source remains `09d0d508fa0eef459c8b767b109b236f9490c014`, and upstream remains `69284c13746e849104f738d6d1a347b1f457df76`.

## Disposition of the supplied report

- **A-M2L-01:** corroborated by Claude's reported static source inspection, archive inspection and one fixed-batch backward. The latter reports exactly two `grad is None` tensors in this tiny configuration. This review does not claim to have independently rerun it or to possess saved per-parameter gradients for all 1920 original training steps.
- **Quality:** FAIL unchanged, final mean delta +0.03428607532021418 > +0.02. Per-seed bounds passing do not override the mean failure.
- **Archive checks:** Claude reports 199 checks, 193 pass and six failures. Do not summarize this as 199/199 PASS. The six failures are the full-model initial-hash reconstructions, not the saved trained-weight hash checks.
- **A-M2L-02 (new open reproducibility item):** full-model initialization NOT REPRODUCED in 6/6 reconstructions. Reviewer used torch `2.11.0+cu130`; producer used `2.11.0+cpu`. Build difference is a recorded difference and a possible hypothesis, **not an established cause**. Reviewer also reports a GPT input-embedding hash difference. Do not ignore, retroactively excuse, or silently reclassify these six failures.
- **No causal overclaim:** corroborated inactive paths do not prove that they caused the validation loss gap, that effective capacity equals gradient-bearing parameter count, or that patching them improves quality. The original total-parameter budget PASS remains scoped to its frozen definition; 65344/51904 is a post-hoc diagnostic, not a replacement gate.
- **Seal decision:** preserve M2-L as a limited negative research record **with A-M2L-01 and unresolved A-M2L-02**. Do not repeat the same gradient diagnostic merely to seal it. Sealing is not full reproduction PASS, joint Grok acceptance, permission to merge, or permission to modify upstream/retrain.
- **Attribution:** this is Claude's report. Prior Grok M1/M2 review remains historical; new Grok A-M2L-01 review remains DEFERRED. Native independent NLL reevaluation and interrupted-resume parity remain NOT TESTED.
- **Next single action:** obtain the six existing reviewer files, a complete preregistration digest and their file manifest; archive without rerunning. Resolve or explicitly carry A-M2L-02 before stronger reproduction claims or a new mechanism-comparison stage. Any further controlled reproduction or training requires a separately specified stage. No upstream edits, GPU use, training, Alice reevaluation or PR merge occurred in recording this report.

## Reviewer report as supplied by the user

Blobs match the audit's cited blobs. Now the exact source lines.

Pre-registered the expectations (sha 352379ab…); next I run the offline archive analysis and the single no-`optimizer.step` forward/backward.

Archive analysis ran: the stateless mapping and byte-identity checks pass. Only my reconstructed init hash disagrees with the report, so I'm checking how training computed it.

**A-M2L-01 is confirmed for this config.** `value_embeds.0.weight` (8,192) and `transformer.core_block.0.attn.ve_gate.weight` (128) never get a gradient. The M2-L record can be sealed, and no further gradient-coverage diagnostic is needed for sealing. This is my answer to the Grok-spec; it is not a Grok review, and the Grok review stays deferred.

## What I ran

- **Archive analysis:** offline, `weights_only`, CPU, with `python -I -B`.
- **Gradient-coverage diagnostic:** the single permitted run: fixed synthetic batch, forward and backward, no `optimizer.step`.
- **Pre-registration:** the expectations were written and hashed (sha 352379ab…) before that run.
- **Environment:** `venv_p1b` (Python 3.12.3, torch 2.11.0+cu130, numpy 1.26.4, einops 0.8.0). Upstream stayed clean at 69284c13.
- **Checks:** 199 archive checks ran; 193 pass. The 6 failures are all one item, the whole-model init-hash reconstruction (see the table).
- **Not run:** no training, no resume replay, no Alice, no GPU.
- **Repo:** nothing changed or pushed.

## Results

| Item | Status | Evidence |
| --- | --- | --- |
| Archive, pilot hash, 26 files, 18 snapshots | PASS | `pilot.json` sha matches; 18/18 file shas match the reports |
| Weights | PASS 18/18 | Training's `weights_sha` on each loaded state_dict equals the reported hash |
| Optimizer | PASS | Param_groups ids map 1:1 to `model.parameters()` order; hyperparameters, moment shapes and `step` all match |
| Trajectories | PASS | 120 and 480 traces are exact prefixes of 1920; loss and gradient-norm shas match; GPT and Parcae use the same batch starts |
| RNG | PASS (loadable only) | 18/18 accepted by `Generator.set_state` |
| Interrupt-resume replay | NOT TESTED | Only reading and hashing were done |
| Quality | FAIL | Mean Δ = +0.03428607532021418 > +0.02. Seeds are +0.0280, +0.0332, +0.0416, each ≤ +0.05, which doesn't offset the failed mean. |
| Stateless mapping | PASS | In 9/9 Parcae snapshots exactly those two tensors, 8,320 parameters, lack state. 51,904 have state. GPT has 65,344 of 65,344. |
| Values unchanged | PASS | Byte-identical across 120/480/1920 for 3/3 seeds, and byte-equal to the init I rebuilt from the seed |
| Gradient coverage (1 batch) | PASS, as pre-registered | See below |
| Rebuilt whole-model `init_sha` vs report | NOT REPRODUCED (6/6) | Cause unknown. My environment is a different torch build, and the GPT wte hash differs too. Parcae's `value_embeds` and `ve_gate` init do reproduce. It doesn't affect the stateless finding. |

**Gradient-coverage run.** In Parcae, `.grad is None` for exactly those two tensors, and 51,904 of 60,224 parameters receive gradients. The config values were:

- `config.n_layer` is 2.
- `value_embeds` keys are {0, 2}.
- Layer ids are prelude 0, core 1, coda 3.
- Gates are prelude none, core present, coda present.

The GPT control has zero `None`-grad tensors out of 48.

## Why those two tensors

- `has_ve` is `layer_idx % 2 == (n_layer-1) % 2`, and `ve_gate` exists only if `has_ve(layer_id, config.n_layer)` (`mixer.py:18-20,44-46`). `config.n_layer` is 2 (`config.py:46`).
- `value_embeds` keys come from 1+1+1 = 3 effective layers (`parcae.py:68-73`), which gives keys {0, 2}.
- The prelude looks up key "0", but it has no gate, so the embedding is ignored (`parcae.py:165`).
- The core has a gate but looks up key "1", which doesn't exist, so `ve` is None and the gate is never evaluated (`parcae.py:374-378`).
- The coda looks up key "2" and has a gate, so it trains.
- AdamW only creates state for parameters that had a gradient, and `clip_grad_norm_` skips `None` gradients.

## The two ratios

- **1.0850** (65,344 / 60,224) is the frozen total-parameter budget. It stays PASS under its own definition and I did not change it.
- **1.2589** (65,344 / 51,904) counts parameters that ever receive a gradient. It is a post-hoc diagnostic, not a gate.
- **What it means:** GPT has about 25.9% more updated parameters. That limits blaming the NLL gap purely on recurrence.
- **FLOPs:** the dead tensors add no matmul FLOPs, so the frozen FLOP ratio is unaffected.

## Disagreements with ChatGPT

- **Agree:** the archive checks, the quality FAIL, A-M2L-01 rated HIGH, and the source mechanism.
- **Added by me:** I observed `.grad is None` directly, which ChatGPT had not. I also showed the two tensors equal the seed-rebuilt init, not just each other across snapshots. The GPT control has full coverage.
- **Caveat on ChatGPT's PASS labels:** its "RNG PASS" means the state loads. Nobody has done a resume replay.
- **Init hash:** ChatGPT did not try to reproduce it.
- **Scope:** this holds for this tiny config only (prelude 1, recurrent block 1, coda 1, recurrence 2, backprop depth 2). I claim nothing about other Parcae scales.

## Decisions

1. **Seal M2-L as a negative research record: yes.** The wording should be: evidence audit PASS, quality criterion FAIL, P2 advantage not established, plus A-M2L-01 as a recorded confounder.
2. **Another gradient-coverage diagnostic: no, not for sealing.** The one-batch diagnostic is done for this config. Removing or relayering those tensors, or rerunning with matched updated parameters, would be a new stage needing your authorization and a fresh pre-registered gate. I haven't done any of it.

Stopping here. Files are in `/tmp/claude-0/-home-user/2c7c9a9c-fc7c-5adb-90a5-e297bc6c2a17/scratchpad/tools/`:

- M2L_A-M2L-01_REPORT.md
- PREREG_expectations.md
- grad_diag.py
- archive_diag.py
- grad_diag.out.json
- archive_diag.out.json
