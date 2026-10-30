# P1-R1: original-initializer provenance, not another depth experiment

Date: 2026-10-30. Native execution at this freeze: **NOT TESTED**.
Base: `4d1ecadc062e190a9bfc8b66b8e2d2962abb266a`, Draft PR #15.

## Development decision

M2-L/M2-D/M2-T negative outcomes remain immutable. End the existing tiny-model depth/continuation series; no longer runs, new depth schedules, GPU scale-up or architecture patch is authorized by this stage. The next useful prerequisite is A-M2L-02: why a reviewer could not reconstruct six original initial model hashes. This is a bounded provenance experiment, not another archive audit or a replacement for the missing reviewer scripts.

## One question

Can the original six initial state_dict hashes be reconstructed in the original CPU environment using the **exact original constructor, pairing and preflight ordering**? Record the first stage at which identities change. Do not infer the cause of Claude's mismatch without its actual reconstruction script/output or a controlled environment comparison.

## Fixed inputs

- Untouched native Parcae/GPT: `sandyresearch/parcae@69284c13746e849104f738d6d1a347b1f457df76`.
- Original model factory and hash algorithm: `research/mini_mythos/m2_matched/experiment.py`, SHA256 `74f00c64448ddbc224a48ef83dc031a90c33448ccb92647666707f6b8f988967`.
- Original config: `research/mini_mythos/m2_matched/frozen_config.json`, SHA256 `a49b38521a45e716b1cb5f2c2b55d317d06ca7542d02623349c5331e9fe26447`.
- Existing M2-L pilot bytes SHA256 `c5be0f6da8eab77ab499ad97a3aaf318633d2d44f234083165ffcacc3b26d7bb`; code_head `09d0d508fa0eef459c8b767b109b236f9490c014`.
- Original matched pilot is already in the repository at `m2_matched/evidence/linux_e533fbe/pilot.json`; require its bytes to match the M2-L pilot's recorded `reference_pilot_sha256`. Require both historical sources to agree on all six initial hashes and common IO hashes BEFORE reconstruction.
- Seeds: 42, 20261029, 20261030. Original GPT FFN60, Parcae FFN64, other model settings entirely from the original factory.
- Producer-equivalent required dependencies: Linux, Python3.12.3, torch2.11.0+cpu, NumPy1.26.4, einops0.8.0. FP32 CPU, one thread, deterministic algorithms, math SDPA through original helpers. Record full environment/build metadata; matching versions does NOT assert identical OS/CPU hardware.

## Bounded procedure

For each seed construct GPT then Parcae exactly as the original runner does. Snapshot state_dict identities after (a) each native constructor, (b) original `pair_io`, (c) original per-arm `preflight`, and (d) original per-arm `count` in GPT-then-Parcae order. Use the original whole-state hash, and record each tensor's dtype/shape/byte hash, changed-name sets, and CPU RNG digests at these boundaries. Compare the final stage to each arm's historical initial hash and compare shared IO to the historical record.

The historical `count` helper performs a fixed synthetic forward/backward to count operations; the original `preflight` performs synthetic CE/causality forwards. They are replayed ONLY to preserve the original initialization measurement point. **No optimizer is created, no optimizer.step, no training batches, no validation/test/Alice evaluation, no saved trained weights loaded, no new gradient-coverage sweep.** Six original preflights and six original counts, no retries or parameter searches. Counted values must equal original saved counts. Require model state and caller RNG to be unchanged across each preflight/count, rather than assuming it.

This stage does not run two different builds or blame CPU/CUDA build differences. A later reviewer can run this same fixed script in the SAME prescribed producer environment. An incompatible environment is BLOCKED, never silently waived.

## Acceptance / stopping rules

- `execution_status=PASS`: all six bounded native sequences complete with required inputs/environment and clean unchanged upstream/research sources.
- `historical_init_status=PASS`: all six final initial hashes equal BOTH historical reports; common IO and saved parameter/FLOP counts also match exactly. Hash disagreement after valid execution is **FAIL**, not BLOCKED.
- `probe_preservation_status=PASS`: full state and caller RNG unchanged by both original probes, no optimizer used, six sequences only. Unexpected mutation is **FAIL** and disallows promoting the initializer result.
- `comparison_status=PASS` requires all three above. Exit0=bounded reproduction PASS; exit1=executed comparison FAIL; exit2=missing/invalid environment or evidence / operational blocker.
- Regardless of PASS, A-M2L-02's **reviewer-discrepancy root cause remains OPEN** until the missing Claude reconstruction procedure is compared. A successful producer-environment replay narrows the issue; it is not permission to erase the earlier six failures or assert cross-build reproducibility.
- Per-tensor differences between constructor/pairing/probe stages are diagnostics, NOT a target for patching initial tensors until expected hashes are forced to match.
- Preserve outputs in a new persistent `mythos_evidence/p1r_init_v1` directory. A second launch only reads the existing result; never deletes, overwrites or reruns automatically. No package install or upstream clone.

## What this can change

PASS establishes a reproducible starting recipe for a later independently authorized causal comparison. FAIL means that starting-condition provenance remains a blocker to new from-scratch mechanism claims. Neither outcome changes old NLL results, active-parameter observations, P2 advantage, ACT or reasoning status. No new model architecture or training experiment follows automatically.

## Review and formal gates

Grok/Claude review of P1-R1: NOT TESTED/DEFERRED until an actual report exists. Prior user-supplied reviewer statements are not new connected runs. Formal Oracle stays BLOCKED/NOT_READY, FORMAL_ACCEPTANCE_READY=False; J1, Bench, R3, upstream Parcae and G2 REAL remain untouched.
