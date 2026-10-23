# P1-C GPU Smoke Implementation Audit Notes

**Scope**: Analysis only. No rewrite of `p1c_gpu_smoke.py` in this task.

## Findings

1. **Model creation**: Uses `parcae_lm.create_model("parcae-small-140m")` → official path. OK.
2. **Random init**: `torch.manual_seed` before construct; Parcae `reset_parameters` is called in `__init__`. Adequate for smoke.
3. **Core gradient check**: Relies on parameter-name substring match (`"core"`, `"recurrent"`, `"core_block"`). Works for current naming but is brittle if names change. Suggest future explicit module traversal.
4. **Injection gradient check**: Matches `"injection"`, `"diagonal"`, `"adapter"`. Adapter is the injection path in current code. Sufficient for smoke; could be tightened to known adapter parameter names.
5. **Parameter update check**: Compares `torch.allclose` before/after. Reliable for detecting any change.
6. **Labels**: `labels = input_ids.clone()` differs from official next-token shift. Documented as synthetic / not language validation. Acceptable for mechanism smoke.
7. **VRAM / timing scope**: Correctly limited to smoke config. Timing includes diagnostics (explicitly flagged).
8. **Diagnostic overhead**: CUDA synchronize + full named-parameter gradient scan every step. Real training throughput will differ.
9. **Misinterpretation risk**: JSON status `PASS` + `gpu_tested: true` could be over-read. Acceptance report and README explicitly forbid claiming full training / MuonAdamW / language learning.

## Blockers for Gate 2

- Official MuonAdamW not exercised.
- Next-token label alignment not verified in official loop.
- Checkpoint resume not tested.
- Actual sampled recurrence not recorded.

No code changes made in this audit.
