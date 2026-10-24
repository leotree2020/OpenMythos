# State Restore Audit (source + CPU probe)

## Official train.py (source)

- First `optimizer_step == 0` skips `optimizer.step()` (compile/autotune guard).
- LR scheduler is created in `startup()`; on resume it is rebuilt from config, not loaded from an independent scheduler checkpoint object beyond what `load_state_dict` of the optimizer/fabric state provides.
- `fabric.load(..., strict=False)` can skip missing keys. Risk of silent omission.
- Recurrence depth is sampled inside the model forward from torch RNG. If that RNG is not in the checkpoint, resumed forwards diverge even with identical data.
- Checkpoint save is tied to microbatch boundaries (`not is_accumulating` and interval). Data iterator position is saved via StatefulDataLoader state, then the extra `next()` (native) advances one more batch.

## CPU probe evidence

- Data continuity with the patch rule: input hashes match.
- Weight continuity: NOT achieved in the probe because model RNG for recurrence was not restored.
- CUDA RNG: NOT APPLICABLE (no CUDA).

## Not claimed

Official train.py numerical equivalence is BLOCKED on CPU. Probe is not a substitute.
