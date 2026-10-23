# P1-C Gate 1 GPU Acceptance Report

**Formal Conclusion: P1-C Gate 1: GPU MECHANISM SMOKE PASS**

Date of experiment: 2026-10-23  
Evidence source: User-provided experimental results summary (original tarball verified by ChatGPT).  
This report does **not** claim independent re-execution of the GPU run by the archiving agent.

## Experiment Goal

Verify that the official Parcae model (pinned commit) can be constructed from random weights, execute forward/backward, produce finite loss and gradients that reach the shared Recurrent Core and DiagonalInjection/adapter, and update parameters without NaN/Inf, on a real A100 GPU using synthetic tokens.

This is a **mechanism smoke**, not a language-learning or full-training reproduction.

## Environment and Git Commits

- GPU: NVIDIA A100-SXM4-80GB
- Python: 3.12.3
- PyTorch: 2.8.0+cu128
- CUDA Runtime: 12.8
- NVIDIA Driver: 595.91.07
- OpenMythos commit used: `f46e3144d60ddfd6dddf698293e14090f879d729`
- Parcae commit: `69284c13746e849104f738d6d1a347b1f457df76`
- Model: `parcae-small-140m` (random init)
- Model parameters: 144,323,136
- Config: mean_recurrence=8, mean_backprop_depth=4

## Execution Parameters

- Steps: 4
- Micro-batch: 2
- Sequence length: 128
- Seed: 42
- Optimizer: AdamW (official MuonAdamW **NOT TESTED**)
- Labels: `labels = input_ids.clone()` (synthetic; not official next-token shift)

## Results

- Exit code: 0
- Status: PASS
- gpu_tested: true
- gpu_operators_executed: true
- checks_completed: true
- core_grad_observed: true
- injection_grad_observed: true
- params_updated: true
- params_finite_after_update: true

### Loss (per step)

| Step | Loss |
|------|------|
| 0 | 10.559690475463867 |
| 1 | 5.614777565002441 |
| 2 | 1.8080718517303467 |
| 3 | 0.37588196992874146 |

### Step Time (s)

| Step | Time |
|------|------|
| 0 | 0.5098 |
| 1 | 0.2032 |
| 2 | 0.0784 |
| 3 | 0.0778 |

### Performance (smoke config only)

- Peak VRAM Allocated: 3.256 GiB
- Peak VRAM Reserved: 3.502 GiB
- Average Step Time: 0.2173 s
- Reported Throughput: 1178.2 tokens/sec

**These numbers apply only to the smoke configuration (seq=128, micro-batch=2, 4 steps). Do not extrapolate to official full training.**

## Evidence Source

- User-provided archive: `p1c_gate1_evidence.tar.gz`
- SHA-256: `1ac6dc5603bdb039b9f22e3a816e12e028b73eab7ae8fb27cdce4ab6006da047`
- Contents (per ChatGPT verification of 11 consistency checks): smoke JSON/log, stdout, pip_freeze, nvidia_smi, commit files.
- Archiving agent did **not** independently re-read the raw tarball; results above are from the user/ChatGPT summary.

## Limitations

- Official MuonAdamW not used or validated.
- Labels are not official next-token shifted targets; no language learning is demonstrated.
- Actual sampled recurrence depth not measured.
- Timing includes diagnostic overhead (synchronization + gradient inspection).
- Throughput and VRAM are smoke-scale only.
- No checkpoint save/resume tested.
- No multi-seed stability tested.

## Acceptance Conclusion

**P1-C Gate 1: GPU MECHANISM SMOKE PASS**

The native Parcae model can be instantiated from random weights and execute a short synthetic forward/backward/update cycle on A100 with finite loss, reachable gradients on core and injection paths, and finite parameter updates.

## Next-Stage Entry Conditions (Gate 2)

See `P1_C_GATE2_READINESS_CHECKLIST.md`. Gate 2 remains unauthorized until that checklist is satisfied and separately approved.
