# Step / Exit Matrix (from pinned Parcae source)

Source: `scripts/train.py` line 846-849:
```
exit_step = cfg.exit_at_step if cfg.exit_at_step is not None else cfg.max_steps
if state["optimizer_step"] >= exit_step - 1:
    break
```

Also: `optimizer.step()` is skipped when `optimizer_step == 0` (line 708).
`optimizer_step` increments only on non-accumulating boundaries (`microbatch_step % accum == 0`).
accum = 4.

## A (max_steps=6, no exit_at_step)

- exit when optimizer_step >= 5
- boundaries: microbatch 4, 8, 12, 16, 20
- optimizer_step after those: 1, 2, 3, 4, 5
- actual step() calls: 4 (first boundary skipped)
- RUNTIME VERIFY: exact microbatch at exit

## B1 (exit_at_step=4)

- exit when optimizer_step >= 3
- expected exit after microbatch 12 (optimizer_step becomes 3)
- actual step() before exit: 2 (boundaries at 8 and 12; 4 was skipped)
- RUNTIME VERIFY

## B2 / C

- resume from B1, continue with max_steps=6
- expected to reach same optimizer_step=5 endpoint as A
- C uses unpatched train.py (extra skip) so data position differs
- RUNTIME VERIFY alignment of update counts

## First-step skip

Not a restore bug. Record optimizer_step and actual step() count separately.
