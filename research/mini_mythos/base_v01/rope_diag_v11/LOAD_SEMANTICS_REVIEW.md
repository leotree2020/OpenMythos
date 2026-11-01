# Official checkpoint loading — read-only source finding

Date: 2026-11-01. This follows completed diagnostic result commit `02603d03aab9c3d6dc5638a76b86189a2c7622d8`. No new model, tensor calculation or numerical run was performed in this source-audit phase.

Purpose: determine whether matching a newly constructed RoPE buffer is the official pretrained loading contract, and identify the smallest useful next validation toward a usable baseline.

Environment and input: read-only target checkout and independent GitHub source reading, both pinned to `sandyresearch/parcae@69284c13746e849104f738d6d1a347b1f457df76`. Target source hashes and numbered excerpts are recorded in `source_evidence/LOAD_SOURCE_AUDIT.json`. No upstream files were changed.

Expected: trace buffer registration, save/load, key handling and generation use; distinguish source semantics from observed runtime behavior and historical artifact provenance.

Actual and status: the following source facts are established (**PASS for the source trace**). Actual full-model loading under the proposed next protocol remains **NOT TESTED**. The historical buffer creation environment remains **UNKNOWN**.

| Source | Finding |
|---|---|
| [Parcae constructor, lines 107–133](https://github.com/sandyresearch/parcae/blob/69284c13746e849104f738d6d1a347b1f457df76/parcae_lm/models/parcae/parcae.py#L107-L133) | Registers `freqs_cis` as a persistent buffer after constructing an initial value. |
| [Official evaluation loader, lines 15–53](https://github.com/sandyresearch/parcae/blob/69284c13746e849104f738d6d1a347b1f457df76/receval/models/parcae.py#L15-L53) | Constructs the model, loads the file, strips specified key prefixes, then calls `load_state_dict(cleaned, strict=False)`. It does not filter this buffer, specify `assign`, or regenerate it after loading. It preserves `rope_settings` by converting it to `RoPESettings`. |
| [Save interface, lines 55–63](https://github.com/sandyresearch/parcae/blob/69284c13746e849104f738d6d1a347b1f457df76/receval/models/parcae.py#L55-L63) | Saves the complete `state_dict`, which includes persistent buffers. |
| [Generation, lines 91–104](https://github.com/sandyresearch/parcae/blob/69284c13746e849104f738d6d1a347b1f457df76/receval/models/parcae.py#L91-L104) | Uses the model's existing `freqs_cis` by slicing it; this path does not regenerate it. |
| [Evaluation entry, lines 63–73](https://github.com/sandyresearch/parcae/blob/69284c13746e849104f738d6d1a347b1f457df76/scripts/eval.py#L63-L73) | Calls the evaluation loader above. |
| [Convenience API, lines 22–69](https://github.com/sandyresearch/parcae/blob/69284c13746e849104f738d6d1a347b1f457df76/parcae_lm/__init__.py#L22-L69) | A different entry point removes `rope_settings` and does not apply the same prefix cleanup. The two entry points must not be assumed equivalent. |

The documented PyTorch loading contract copies parameters and persistent buffers; `assign=False` is the default. `strict=False` concerns key matching, not exclusion of buffers. See the [PyTorch 2.11 API](https://docs.pytorch.org/docs/2.11/generated/torch.nn.Module.html#torch.nn.Module.load_state_dict).

Inference from these sources: with a matching buffer key, compatible shape/type and successful loading, the official evaluation path should restore the checkpoint's RoPE values. A model constructor's initial value need not equal that stored artifact for this loading operation to be faithful. This inference requires a separate runtime validation; it is not a new result for B1 A5.

The official loader ignores the returned missing/unexpected-key report. Therefore command success alone is insufficient. The next validation must independently compare the complete normalized checkpoint key set, shapes and types against the loaded model, detect prefix collisions, and check all loaded tensor bytes, including the RoPE buffer. Merely checking one buffer would miss silent partial loading.

## What remains unknown

The helper's present formula, training configuration (`bf16-mixed`, compilation setting), and environment-logging code do not establish the released artifact's actual creation/export history. This phase did not obtain a publication-linked training log, export command, original device/kernel/version record or conversion trace. No historical hardware or kernel cause is established.

The completed diagnostic's five paths all fail their frozen compatibility screen. This does not contradict the loader's restore-from-checkpoint contract; the two checks ask different questions. The original A5 remains BLOCKED with its unchanged `1e-6` threshold. No backward change to B1 acceptance is justified.

## Next single implementation task

Prepare a separately frozen **CPU official checkpoint restoration check**, using the existing local files and the pinned `receval` loader. Its scope is loading integrity only: no forward, generation, training, optimizer, GPU, downloads, buffer assignment by the harness, model saves, upstream edits or B1 runner invocation.

Acceptance must require: original input/source/environment identities; unambiguous checkpoint-key normalization; exact key/shape/dtype agreement; bytewise agreement of every loaded state entry with the normalized checkpoint; explicit bytewise RoPE agreement; unchanged protected files; complete evidence and a checkpoint. An inability to verify fixed input identity, pinned code provenance or the current runtime is BLOCKED; a confirmed state mismatch is FAIL. The already-unknown historical training/export environment stays UNKNOWN and does not itself block this distinct loading-integrity check. Stop and preserve evidence on either BLOCKED or FAIL. A passing restoration check establishes faithful loading only; language quality, training/resume and the old A5 retain their existing statuses.

Separate read-only review approved the source interpretation and the separation from historical A5; the blocker-scope clarification above incorporates that review. No empirical restoration claim was added.

Implementation, execution and all acceptance items for that next check remain **NOT TESTED**. This document does not rerun or amend the completed RoPE diagnostic. The owner has authorized autonomous work; no Claude handoff is required, while protected-stage boundaries continue to apply.
