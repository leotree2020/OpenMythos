# S2-3A Native Checkpoint Fields

Source: pinned Parcae scripts/train.py `maybe_save_checkpoint`.

`fabric.save(path, state)` writes the training `state` dict.

Present in state at save time (source):
- model
- optimizer
- lr_scheduler
- tokenizer
- train_dataloader / val_dataloader
- microbatch_step
- optimizer_step
- is_accumulating
- rng_state_torch / rng_state_cuda / rng_state_numpy / rng_state_python
- metrics, wandb_run_id, model_config

Post-hoc extractable: anything in that dict.
Must be collected during the run: per-microbatch input SHA-256, per-boundary loss,
actual optimizer.step() count. These are not stored as a sequence in the checkpoint.

This list is from source. A self-built test checkpoint is not this format.
