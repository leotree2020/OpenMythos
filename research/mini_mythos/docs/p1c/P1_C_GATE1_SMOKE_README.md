# P1-C Gate 1 GPU Smoke — Execution Guide

**Pinned Parcae**: `69284c13746e849104f738d6d1a347b1f457df76`

## Install (on GPU instance)

```bash
git clone https://github.com/sandyresearch/parcae.git
cd parcae
git checkout 69284c13746e849104f738d6d1a347b1f457df76
pip install -e .
# Record: pip freeze | grep -E 'torch|lightning|parcae'
```

## Run smoke

```bash
# From OpenMythos clone or copy the script
python research/mini_mythos/scripts/p1c_gpu_smoke.py \
  --steps 4 --micro-batch 2 --seq-len 128 \
  --out p1c_gate1_smoke.json --log p1c_gate1_smoke.log
```

- On CPU (no CUDA): exits with `CPU_CONFIG_OK_GPU_NOT_TESTED` after config check.
- On GPU: performs limited synthetic steps; writes JSON with peak VRAM, step time, tokens/sec, gradient flags.
- Failure: full traceback in `.log`.

## Pre-run checklist

- [ ] Parcae checked out at exact commit
- [ ] `import parcae_lm` succeeds
- [ ] Billing alert set; hard cumulative cap 5,000 JPY monitored manually
- [ ] Plan to terminate Pod and delete unused Network Volume / Volume Disk immediately after
- [ ] No large data download

## Cost control reminder

Billing alerts are **not** hard stops. You must:
1. Manually Stop or Terminate the Pod in the RunPod dashboard.
2. Delete any Network Volume or persistent storage that is no longer needed (storage continues to bill while attached or idle).
3. Confirm in the billing page that the instance is no longer accruing charges.

## Budget arithmetic correction

Previous ranges mixed assumptions. Revised consistent example (ESTIMATED, unmeasured):
- If measured throughput = 10,000 tokens/s on the target GPU,
- Stage 1 40 steps × 524,288 tokens ≈ 21e6 tokens → ~35 minutes → ~0.6 GPU-hours.
Actual numbers must come from the smoke script JSON. No fixed claim until measured.

Upstream MuonAdamW is used in official training; this smoke uses AdamW for minimal dependency. If official optimizer is required and unavailable, mark BLOCKED.
