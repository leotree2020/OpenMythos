# Native Evidence Adapter

## Verdict

CPU adapter: **PASS**
Native train.py path: **NOT TESTED**
GPU_RUNTIME: **NOT TESTED**
Overall integration: **BLOCKED** until a real train.py run exists

## What was added

External adapter only. Frozen Parcae was not modified.

- `native_evidence_adapter.py`
- `test_native_adapter_cpu.py`
- `native_adapter_cpu.txt`

## Fields

| Field | Source | Status |
|-------|--------|--------|
| batch SHA-256 | real tensor bytes | CPU PASS |
| loss | real forward `output["loss"]` | CPU PASS |
| optimizer_step vs update_count | first step skipped, then real `step()` | CPU PASS |
| before_save RNG | captured at the save point | CPU PASS |
| after_load RNG | captured at the resume point | CPU PASS |
| model / MuonAdamW / checkpoint | live objects and a real file | CPU PASS |
| commit / config / command link | hashed into `native_entry_artifact` | CPU PASS |
| GPU_RUNTIME | refused without `gpu_confirmed` | refused, as required |

## Not claimed

This is not a frozen `scripts/train.py` run. The adapter is ready to be called at the known save and resume points. Wiring it into a real run is the next authorized step.

Training math was not changed. No GPU. License remains UNKNOWN / UNVERIFIED and is not a blocker for this engineering work.
