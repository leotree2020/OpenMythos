# P1-C Gate 1 GPU Acceptance Report

**Formal Conclusion: P1-C Gate 1: GPU MECHANISM SMOKE PASS**

Date of experiment: 2026-10-23  
Evidence source: Original user-provided tarball `p1c_gate1_evidence.tar.gz`.  
SHA-256: `1ac6dc5603bdb039b9f22e3a816e12e028b73eab7ae8fb27cdce4ab6006da047` (verified against the file provided in this session).

## Experiment Goal

Verify that the official Parcae model (pinned commit) can be constructed from random weights, execute forward/backward, produce finite loss and gradients that reach the shared Recurrent Core and DiagonalInjection/adapter, and update parameters without NaN/Inf, on a real A100 GPU using synthetic tokens.

This is a **mechanism smoke**, not a language-learning or full-training reproduction.

## Environment and Git Commits

- GPU: NVIDIA A100-SXM4-80GB (confirmed in nvidia_smi.txt)
- Python: 3.12.3
- PyTorch: 2.8.0+cu128 (confirmed in smoke JSON and pip_freeze)
- CUDA Runtime: 12.8
- NVIDIA Driver: 595.91.07
- OpenMythos commit used: `f46e3144d60ddfd6dddf698293e14090f879d729` (confirmed in openmythos_commit.txt)
- Parcae commit: `69284c13746e849104f738d6d1a347b1f457df76` (confirmed in parcae_commit.txt and smoke log)
- Model: `parcae-small-140m` (random init)
- Model parameters: 144,323,136
- Config: mean_recurrence=8, mean_backprop_depth=4, use_fused_head=pytorch

## Execution Parameters

- Steps: 4
- Micro-batch: 2
- Sequence length: 128
- Seed: 42
- Optimizer: AdamW (official MuonAdamW **NOT TESTED**)
- Labels: `labels = input_ids.clone()` (synthetic; not official next-token shift)

## Results (directly from p1c_gate1_smoke.json and accompanying files)

- Exit Code 0: reported by the user from the terminal output of the run (not embedded as a field inside the experiment log itself).
- Status: PASS
- gpu_tested: true
- gpu_operators_executed: true
- checks_completed: true
- core_grad_observed: true
- injection_grad_observed: true
- params_updated: true
- params_finite_after_update: true
- official_muonadamw: NOT_TESTED
- actual_sampled_recurrence: NOT_MEASURED

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

**These numbers apply only to the smoke configuration. Do not extrapolate to official full training.**

## Evidence Source and Verification

- Archive: `p1c_gate1_evidence.tar.gz`
- SHA-256: `1ac6dc5603bdb039b9f22e3a816e12e028b73eab7ae8fb27cdce4ab6006da047`
- Original data consistency was verified by ChatGPT (11 structural/consistency checks).
- The archiving agent (Grok) was provided the tarball in this session, extracted it, and confirmed that the JSON, log, commit files, and nvidia_smi match the reported numbers and SHA-256.
- No new GPU experiment was launched during archival.

## Limitations

- Official MuonAdamW not used or validated.
- Labels are not official next-token shifted targets; no language learning is demonstrated.
- Actual sampled recurrence depth not measured.
- Timing includes diagnostic overhead.
- Throughput and VRAM are smoke-scale only.
- No checkpoint save/resume tested.
- No multi-seed stability tested.

## Acceptance Conclusion

**P1-C Gate 1: GPU MECHANISM SMOKE PASS**

## Next-Stage Entry Conditions (Gate 2)

See `P1_C_GATE2_READINESS_CHECKLIST.md`. Gate 2 remains unauthorized.
