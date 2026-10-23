# P1-C Gate 1 GPU Smoke — Reproducible Execution Guide

**Pinned Parcae**: `69284c13746e849104f738d6d1a347b1f457df76`  
**Pinned OpenMythos HEAD**: (current P1-C branch)

## Full commands from a clean instance

```bash
# 1. Clone OpenMythos and switch to P1-C branch / known HEAD
git clone https://github.com/leotree2020/OpenMythos.git
cd OpenMythos
git checkout mini-mythos-p1c-parcae-training-plan
# or: git checkout <exact-sha-from-PR>

# 2. Clone Parcae and pin commit
git clone https://github.com/sandyresearch/parcae.git
cd parcae
git checkout 69284c13746e849104f738d6d1a347b1f457df76

# 3. Install compatible dependencies (record exact versions)
pip install -e .
# Typical additional: torch (CUDA build matching instance), lightning, etc.
# pip install torch --index-url https://download.pytorch.org/whl/cu124
pip freeze > /tmp/env_freeze.txt

# 4. Return to OpenMythos and run smoke (import path assumes parcae installed)
cd /path/to/OpenMythos
python research/mini_mythos/scripts/p1c_gpu_smoke.py \
  --steps 4 --micro-batch 2 --seq-len 128 \
  --out p1c_gate1_smoke.json --log p1c_gate1_smoke.log

# 5. Save results
cat p1c_gate1_smoke.json
cat p1c_gate1_smoke.log
```

## CPU contract check (no GPU, no torch required for basic)

```bash
python research/mini_mythos/scripts/p1c_cpu_contract_check.py
```

## Fail-closed behavior

Script returns non-zero exit code on:
- forward exception or wrong return shape
- nonfinite loss or gradients
- Recurrent Core gradient not observed
- DiagonalInjection / adapter gradient not observed
- no parameters updated
- invalid args
- unhandled exceptions

`status: PASS` only when all checks succeed. Official MuonAdamW is explicitly `NOT_TESTED`.

## Cost control

Billing alerts ≠ hard stop. After run: manually Terminate Pod and delete unused storage volumes, then confirm billing page.
