# Gate 2.2-B Readiness

Pinned Parcae: `69284c13746e849104f738d6d1a347b1f457df76`
HEAD: `ef2cc503c07bdf353114fbba9fb4f7c3300c0eb8`

## State completeness

| Item | Status | Notes |
|------|--------|-------|
| Model weights | source supported | `fabric.save` / `load_state_dict` |
| MuonAdamW state | source supported, runtime NOT TESTED | optimizer in fabric state |
| LR scheduler | risk | rebuilt in `startup()` from config; uses `optimizer_step` for `get_lr`. Not an independent loaded object beyond fabric state. |
| microbatch_step / optimizer_step | source supported | in fabric state; `model.step` is reassigned from microbatch_step before forward |
| Gradient accumulation boundary | source supported | `is_accumulating = microbatch_step % accum != 0`; save requires not accumulating |
| First optimizer.step skip | source supported | `if optimizer_step > 0` before step (compile/autotune guard) |
| torch CPU RNG | source supported | saved/restored in checkpoint |
| CUDA RNG | source supported, GPU NOT TESTED | saved/restored |
| NumPy / Python RNG | source supported | saved/restored |
| Recurrence sampling | source supported | seeded from `model.step` which is set from microbatch_step |
| StatefulDataLoader position | source supported, rngds verified | extra `next()` is the known skip; patch omits it for RandomTokensDataset only |
| ParquetStreamPure | BLOCKED on CPU | CUDA + distributed in state_dict |

## CPU probe (strengthened B)

B must match A on: input hashes, loss within 1e-5, weights, optimizer state, scheduler, update count.  
Re-run exit 0. All groups PASS under the stronger rule.

## GPU experiment

Designed only. Not executed. See `GATE2_2_B_GPU_PLAN.yaml` and acceptance matrix.

## Verdict

**NOT READY** for official GPU numerical equivalence.

Reasons:
- Official `scripts/train.py` path has not been run with the research patch.
- MuonAdamW runtime restore is NOT TESTED.
- Scheduler rebuild vs loaded state is a residual risk that must be checked on the first GPU run.
- ParquetStreamPure path is BLOCKED; experiment must use rngds.
- Cost/quote/balance cannot be confirmed from this environment.

A complete test plan exists. Key states have a source-supported path. Runtime confirmation is still required, so the verdict is NOT READY, not READY.
