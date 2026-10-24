# S2-4 MuonAdamW Audit

Source: recpre/optim/muon_adamw.py at Parcae 69284c1.

## Construction

`MuonAdamW(param_groups)` expects groups with `kind` of `adamw` or `muon`.
`get_muon_param_groups` routes:
- ndim < 2, embed, norm, bias, A_log, dt_bias, adapter.B, adapter.adapter, transformer.C → AdamW
- other 2D weights → Muon, grouped by shape

## Compile / BF16

`adamw_step` and `muon_step` are `@torch.compile(dynamic=False, fullgraph=True)`.
Muon path casts the update to bfloat16 inside `muon_step`.

## CPU result

Environment: this host, torch CPU, no CUDA.
- instantiate groups: PASS
- A_log / dt_bias / adapter.B → AdamW: PASS
- real step(): BLOCKED. Inductor C++ compile failed: `Python.h: No such file or directory`.
- state_dict restore: not reached because step did not run.
- GPU step: NOT TESTED.
- RunPod is PyTorch 2.8.0+cu128. This host is a different CPU build. Compatibility on 2.8 is NOT TESTED.

AdamW was not used as a substitute.
