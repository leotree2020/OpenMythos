# MYTHOS-ROUTING-FEASIBILITY-CPU-V2 checkpoint

**Engineering status: FAIL. Scientific early-exit result: NOT TESTED.**

Purpose: test whether the frozen0.01 adaptive policy exits at16 on16 new-to-routing source articles, each128tokens, under two paired seeds. Required coverage32 calls.

Input/source freeze: `1ff8c902cb003ba1010be76f067de2708e0206bd`.
Initial sealed result commit: `126174ca907af5d43514cbd780756bf00265bab1`.
Branch: `mythos-routing-feasibility-cpu-v2`. This documentation revision is the subsequent branch HEAD.

Environment: designated bookish-pancake-vwqx7rr9x5w3wxjr Codespace; model interpreter Python3.12.3, existing Torch2.11.0+cpu environment. The worker stopped before importing Torch/loading a model; the intended FP32/thread runtime was NOT TESTED. Data preparation used the existing Python3.12.3/pyarrow19.0.1/numpy1.26.4/tokenizers0.23.2 environment. Three dependency inventories were preserved unchanged; no packages installed.

Actual results:

- Full target dependency/source preflight:36/36 PASS.
- Target development helpers:10 data tests +11 routing tests =21/21 PASS. These are not model evidence.
- Data preparation:26 checks PASS. Reviewed60 sources; exclude33 historical sources;27 remain; deterministically select16 distinct sources with128-token prefixes. No historical/new prefix duplicates.
- Sealed private inputs:58091bytes, SHA256 `ae5f8ad5fd53d25afaf29487a650dc0300528b0926c9883652475c4ca7db127f`.
- Worker startup:2 PASS /1 FAIL, at designated routing worktree/branch guard.
- Model loads:0. Forward calls:0/32. Final independent model-output audit:NOT TESTED.
- Operator custody:PASS; five protected checkout baselines, original artifacts, completed data and three environments unchanged. Worker model preservation:NOT TESTED because no model existed.
- No early-exit, quality, efficiency or later mechanism finding is available.

Cause: the input path error was corrected, but root continuation review missed that the reused V1 worker hard-codes its original worktree and branch. Its guard correctly rejected the V2 identity. This is an implementation integration error, not a negative mechanism result. No guard was disabled, no identity was spoofed, no post-stop repair/retry occurred.

Evidence: `evidence/summary.json`, `evidence/worker/public/completion.json`, `evidence/data/public/completion.json`, `evidence/custody.json` and `STAGE_REVIEW.json`.
External complete run: `/workspaces/mythos-evidence/base_v01/routing_feasibility/attempt-v2`. Original private tokens/raw artifacts stay external and are bound by EXTERNAL_EVIDENCE_MANIFEST.json. V1 stopped run/checkpoint are retained.

The user-approved four-mechanism order and controlled combination rules are recorded in MECHANISM_SEQUENCE.md. Individual nonsignificant results do not establish equivalence or rule out interaction. LoRA, iteration encoding and MoDA/MoE remain NOT TESTED. The sequence is paused at the engineering failure, not cancelled.

Next unique instruction: resolve only operator/worker startup identity consistency in a new frozen continuation. Preserve stopped V1/V2 and the sealed16-source inputs. Isolate required worker identity changes and test the actual startup contract before loading a model; never edit the frozen V1 worker or spoof its identity. Then complete mechanism1 before progressing in the recorded order.

Upstream69284c13746e849104f738d6d1a347b1f457df76 and threshold0.01 unchanged. No A5 relaxation, B1 rerun, training/GPU, B2/D2-A or PR24 merge. Formal Oracle BLOCKED/NOT_READY; FORMAL_ACCEPTANCE_READY=False.
