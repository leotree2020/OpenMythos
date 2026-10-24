# S2-2 Checkpoint Call Chain

Pinned Parcae: 69284c13746e849104f738d6d1a347b1f457df76

## Order (source)

1. `train_step` increments `microbatch_step`, sets `model.step`.
2. `is_accumulating = microbatch_step % accum != 0`.
3. On a non-accumulating boundary, if `optimizer_step > 0`, `optimizer.step()` runs. First boundary skips `step()`.
4. Then `optimizer_step += 1`.
5. `maybe_save_checkpoint` runs if not accumulating and `microbatch_step % save_step_interval == 0`.
6. Then `exit_step = exit_at_step or max_steps`; exit if `optimizer_step >= exit_step - 1`.

Save happens before the exit check in the same loop iteration.

## B1

`exit_at_step=4` → exit when `optimizer_step >= 3`.
With accum=4 this is expected after microbatch 12. RUNTIME VERIFY. Not a measured fact.

## Resume

`load_checkpoint` restores model, optimizer, scheduler (if present), torch/numpy/python/cuda RNG, and dataloader state when the checkpoint contains them.

After `iter(train_dataloader)`, if `microbatch_step > 0`, native code calls `next(train_iterator)`.
That is the extra skip. The rngds-only patch omits it only for `RandomTokensDataset`.

## B2 vs C

Same B1 checkpoint. Same seed, model, optimizer, data config.
Only difference: B2 omits the extra skip for rngds; C keeps it.
Non-rngds keeps the native skip.

## Not claimed

Full `scripts/train.py` on CPU is BLOCKED (CUDA/fabric).
This audit plus the CPU logic test does not equal a GPU resume PASS.
