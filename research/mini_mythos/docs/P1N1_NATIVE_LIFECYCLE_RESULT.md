# P1-N1 Native Lifecycle

## Verdict

Overall P1-N1: **BLOCKED**

The isolated patch exists. The frozen entry did not run.

## What ran

Patched worktree import:
```text
ValueError: Node failure! Device manager init failed
```
Exit 1. This happens at `scripts/train.py` line 27, before any batch, loss, save, or resume.

No consecutive `collect_rng()` calls were used to fake save/restore.

## Patch

`research/mini_mythos/gate2_2/native_lifecycle.patch`
SHA-256 `9340f6de4e98f5f0ecec5e7245a2b2db7901726ad557505d4cfaf481cadcc943`
Upstream Parcae `69284c13746e849104f738d6d1a347b1f457df76` was not modified.

Hooks, not executed:
- after real `optimizer.step()` only, record batch hash, loss, counters
- after RNG is written and before `fabric.save`
- after checkpoint file write, hash the file or directory
- after resume applies RNG and before the next forward

The observer does not decide whether `optimizer.step()` runs.

## Matrix

| Item | Result |
|------|--------|
| Real batch hash | NOT TESTED |
| Real loss | NOT TESTED |
| optimizer_step | NOT TESTED |
| actual update_count | NOT TESTED |
| before_save RNG | NOT TESTED |
| Real checkpoint save | NOT TESTED |
| Real checkpoint restore | NOT TESTED |
| after_load RNG | NOT TESTED |
| MuonAdamW evidence | NOT TESTED on this path |
| scheduler | NOT TESTED |
| Schema 2.2-c | NOT TESTED on this path |
| Provenance | NOT TESTED |
| Native train.py CPU | BLOCKED |
| GPU_RUNTIME | NOT TESTED |
| Overall | BLOCKED |

## Next block

A host with a working CUDA device manager is required before these hooks can be verified. This CPU host cannot import `scripts/train.py`.
