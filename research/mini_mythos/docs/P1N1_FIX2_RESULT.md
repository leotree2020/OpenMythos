# P1-N1-FIX2

## Verdict

FIX2 fixture: **PASS**
Native fabric save/load: **NOT TESTED**
Overall P1-N1-FIX2: **PASS** for the persistence gap only.

## Mechanism

When `MINI_MYTHOS_EVIDENCE=1`, the patch calls `stamp_update_count(state)` before `fabric.save`.
The value comes from `_MM_LOG.update_count` and is written into the save object as `mini_mythos_update_count`.
After load, `restore_update_count` reads that field. Missing field returns `MISSING` and does not assume zero.

Disabled instrumentation leaves the original path unchanged.

## Test

```bash
PYTHONPATH=research/mini_mythos/gate2_2 python research/mini_mythos/gate2_2/test_native_lifecycle_observer.py
```
Exit 0.

Saved count 1. New observer restored 1, then next step made 2. Missing field returned MISSING.

Patch SHA-256: `b691be6741cb3f8017afb460bec1912da4bf172dbb7f252e8eed1a69fb5c432b`
Kind: TEST FIXTURE — NOT NATIVE TRAINING.

## Still blocked

Frozen `scripts/train.py` remains BLOCKED on this CPU host. Real fabric save/load and GPU_RUNTIME are NOT TESTED.
