# GPU Prelaunch Blockers (not resolved)

- gpu_confirmed boolean is not proof of a GPU run.
- Per-batch SHA, loss, and optimizer update_count are not yet wired into native train.py.
- before_save / after_load RNG timing is not captured inside the real train loop.
- Optimizer sidecars are not fully checked against a native MuonAdamW checkpoint.
- Checkpoint, config, and run-event linkage is incomplete until a real run exists.
- Official 65k tokenizer remains BLOCKED.
- MuonAdamW CPU step is BLOCKED on this host (torch.compile / missing Python.h).
- CUDA RNG and GPU step are NOT TESTED.

None of these are marked resolved.
