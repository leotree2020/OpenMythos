# MYTHOS-CPU-LOAD-INTEGRITY-V1

Frozen before runtime; initial status NOT TESTED. Owner authorization: implement, review, freeze and execute this CPU complete-loading check from checkpoint `a20ec439`; stop on BLOCKED/FAIL, preserve evidence, commit a checkpoint. No Claude handoff or further permission request is required.

## Purpose and scope

Test whether the pinned official evaluation loader faithfully restores every actual parameter and buffer tensor from the existing released checkpoint. This is a separate loading-integrity question, not a repeat of B1's constructor-versus-artifact A5 or the completed RoPE numerical-path diagnostic.

Only one official model construction/loading invocation. One independent harness read of the original weight file supplies the reference; the official loader performs its own read. No second model, model forward, generation, training, backward, optimizer, cache creation, GPU, download, package installation, configuration override, manual buffer assignment, buffer recomputation by the harness, model save, upstream change, B1 invocation, B2/D2-A or PR #24 operation.

The constructor's normal initialization (including an initial RoPE buffer) is part of the official loader and must not be skipped or modified. Initialization seed is fixed to 0; it is not an experiment seed sweep and all accepted state must match the artifact afterward.

## Fixed inputs and environment

- Base commit: `a20ec43914f8e7bb5a7c17dedd27f1acf2a95ec3`.
- Branch: `mythos-base-v01-cpu-load-v1`, reusing the clean isolated checkout `/workspaces/mythos-base-v01-rope-diag-v11`. The old diagnostic branch stays at its prior remote head.
- New source only: `research/mini_mythos/base_v01/load_integrity_v1/`.
- Codespace: `bookish-pancake-vwqx7rr9x5w3wxjr`.
- Interpreter: `/workspaces/mythos-base-v01-cpu312/bin/python`, Python 3.12.3, torch 2.11.0+cpu. Compare the entire installed distribution inventory to the original B1 environment record. Lock SHA-256: `84440f8945041ed314c29b205c5244e074116ede023d5aae0b11b633b4d6a51e`.
- Upstream: `/workspaces/mythos-parcae-pinned` at `69284c13746e849104f738d6d1a347b1f457df76`, clean including ignored/untracked files.
- B1 worktree: `/workspaces/mythos-base-v01-b1` at `d88be474ebb2529c5b095e3732b1f25509f9b824`, unchanged and clean.
- Original input directory: `/workspaces/mythos-evidence/base_v01/b1/b1-20261101T021657Z/downloads/model`.
- Weight file: `pytorch_model.bin`, 578361537 bytes, SHA-256 `ed6eb306464dd0d694e9eacd58f7e06ac3e44b43cb7c5c79dbcb1543059c6621`.
- Config: `config.json`, 1741 bytes, SHA-256 `5c8fc785c2f6dba67d0370ad715034860e3b22bfce850da825c06baa03923c13`.
- Evidence root: `/workspaces/mythos-evidence/base_v01/load_integrity`; exclusive creation claims the only formal attempt. Existing root means stop and recover it, never delete or choose an alternate path to retry.
- Resource guard: at least 1 GiB free disk and 3 GiB available memory before importing the model. No new weight copy is written.

Before Torch import set OMP/MKL/OPENBLAS/RAYON threads to 1; TOKENIZERS_PARALLELISM=false; CUDA_VISIBLE_DEVICES empty; PYTHONDONTWRITEBYTECODE=1; HF_HUB_OFFLINE=TRANSFORMERS_OFFLINE=1. Use Python -B and private pycache redirection. Actual intra/inter-op thread counts must both be 1, deterministic algorithms enabled, defaults FP32/CPU, no enabled autocast, CUDA uninitialized. Verify actual CPU Torch package origin/version and runtime state before/after upstream imports and after model loading. Keep warnings and all logs.

The unknown historical training/export hardware and software remain UNKNOWN. They do not block a check of current faithful restoration from a byte-identified artifact. Missing current input, code or environment identity does block it.

## Official path

Import the exact pinned `receval/models/parcae.py` file with the standard Python file-module mechanism. Its source bytes are unchanged; this avoids importing unrelated evaluation registry packages. Record the code filename of `ModelingParcae.from_pretrained`. Add only the pinned upstream directory for its normal imports.

Call exactly once:

`ModelingParcae.from_pretrained(existing_absolute_local_directory, device="cpu", dtype=None)`

No configuration kwargs; no convenience `parcae_lm.from_pretrained`; no interception or replacement of `load_state_dict`. The official loader itself removes `_class_name`/`init`, converts `rope_settings`, and uses `strict=False`. The harness must not silently filter additional config fields or “repair” a failure. Configuration/import/construction exceptions are BLOCKED, with their evidence saved.

## Acceptance gates

| Gate | Expected | Failure classification |
|---|---|---|
| L0 | Named target; exact interpreter/dependencies/source/input identities; isolated clean branch; full protected-file baseline; required runtime and resources | BLOCKED |
| L1 | Independent `torch.load(..., weights_only=True, map_location="cpu")`; nonempty tensor mapping; exact official prefix normalization without collisions | Invalid mapping, key or collision FAIL; unavailable input/read mechanism BLOCKED |
| L2 | Exactly one official loader returns the exact evaluation model on CPU; no config/dtype changes by harness | Unavailable/import/construction exception BLOCKED; confirmed returned-model contract violation FAIL |
| L3 | Exact state key set, metadata, complete actual registered parameter/buffer coverage, finite float/complex values, every logical tensor byte directly equal to its independent original | Confirmed key/shape/dtype/device/finiteness/value mismatch FAIL; unsupported representation/coverage premise BLOCKED |
| L4 | One complete comparison per checkpoint entry; both sides' byte counts complete; explicit RoPE equality; tied embedding/head object/storage relationship and both file paths verified; exact invocation count | FAIL; unexpected frozen architectural premise BLOCKED |
| L5 | All protected file hashes, prior evidence membership and Git states unchanged; evidence sealed without gaps | Confirmed changes FAIL; incomplete proof or save failure BLOCKED |

Each record includes Purpose, Environment, Input, Expected, Actual, Status. Any first BLOCKED/FAIL stops numerical/model work; unreached gates stay NOT TESTED. Continuing metadata inventory to preserve a structural failure and sealing files are not permission to compare additional tensor values. No third attempt, repairs or reruns after a formal result. Candidate counts or exit code alone are not PASS.

## Coverage and byte semantics

- Normalize keys with the official one-pass ordered loop: `module.`, `_orig_mod.`, `model.`, each at most once. No recursive stripping. Preserve the original-to-normalized mapping. Reject any collision, even if colliding values might match.
- Compare source and loaded `state_dict` key sets bidirectionally. Enumerate `named_parameters(remove_duplicate=False)` and `named_buffers(remove_duplicate=False)`, plus each module's registered buffer slots, including aliases and persistence flags. Do not count only deduplicated parameter names.
- A registered `None` slot is not an actual tensor: record its non-state reason without blocking. If an actual nonpersistent Tensor is present and has no original persistent-state value, mark the complete-coverage premise BLOCKED; do not label normal PyTorch nonpersistent semantics a defective load. Do not silently omit it and claim complete restoration.
- Verify model state exports directly expose their registered tensors. Unsupported custom/extra state is BLOCKED rather than silently ignored.
- Exact shape, dtype and CPU strided representation are required. Compare canonical logical C-order bytes; preserve/report original strides and never cast either side. Ordinary non-contiguous storage does not by itself fail.
- Use blocks at most 1 MiB per side. Check each side's block length and final total against the expected bytes before calling the hash complete. Direct bytes equality is the criterion; SHA-256 provides evidence, not a substitute. This distinguishes +0/-0. Nonfinite floating/complex values are FAIL even if bitwise identical.
- A failed partial row must label any prefix hash as partial, leave the full hash unset, save processed byte counts, and stop. Empty tensors can have zero-byte complete coverage. Metadata access exceptions (for example uninitialized tensors) become BLOCKED in the runner.
- All alias paths are compared independently against their file entries. For frozen `tie_embeddings=True`, embedding/head must remain the same Parameter object and storage with the same offset/shape/stride; both paths must directly match their file values. This establishes reference-value agreement by transitivity, without assuming the checkpoint's own storage topology equals the model's.
- No raw tensor elements, weight copies or restored model are exported. Report keys, classifications, shapes, dtypes, strides, byte counts, finite flags, hashes and alias metadata.

## Controls, audit limits and evidence

Source/AST review occurs before implementation freeze. No new module, Torch import, helper fixture or model run is executed as a rehearsal. Separate agents review comparison and orchestration code; this is static review, not empirical proof and not external Claude/Grok approval.

Implementation commit A precedes a documentation checkpoint B. The runner verifies source bytes against A, records execution HEAD B, and exclusively claims one run before importing Torch. The upstream helper is not called separately; no constructor RoPE value is compared with the artifact in this check.

Protect all tracked upstream files, frozen new implementation, B1 code/lock, original B1 run files and the completed RoPE run files. Before/after inventories detect additions/removals in old evidence directories. Logs close before evidence hashes are finalized. Catch ordinary exceptions and Python interruptions; attempt sealing even after a logging failure. An uncatchable process kill cannot guarantee a final summary; operator capture and the claim/partial files then establish BLOCKED without rerunning.

Private logs and protected-baseline records stay on the target. Public per-key/check records and summaries are copied byte-for-byte into Git with their original `public/` prefix preserved. Full and public manifests state self-exclusions; summary is written only after the manifests. The result checkpoint records A/B/result commits, environment, result, limitations, unresolved issues and one next instruction. Normal push only; no PR creation/merge.

PASS establishes faithful CPU checkpoint loading only. B1 A5 remains BLOCKED at its unchanged `1e-6` criterion. No B1 A3/A8–A11, forward, language quality, training, training-resume, efficiency, or performance claim is upgraded. Formal Oracle remains BLOCKED/NOT_READY and FORMAL_ACCEPTANCE_READY=False. Complete this stage and stop.
