# P1-C Gate 1 GPU Smoke — Reproducible Execution Guide

**Pinned Parcae**: `69284c13746e849104f738d6d1a347b1f457df76`

## Full commands from a clean Linux instance

```bash
# Work in a known directory
mkdir -p $HOME/mini-mythos-gate1 && cd $HOME/mini-mythos-gate1

# 1. Clone OpenMythos and switch to P1-C branch
git clone https://github.com/leotree2020/OpenMythos.git
cd OpenMythos
git checkout mini-mythos-p1c-parcae-training-plan

# 2. Clone Parcae and pin commit (sibling directory)
cd $HOME/mini-mythos-gate1
git clone https://github.com/sandyresearch/parcae.git
cd parcae
git checkout 69284c13746e849104f738d6d1a347b1f457df76
# Verify: git rev-parse HEAD   # must equal 69284c13746e849104f738d6d1a347b1f457df76

# 3. Install
pip install -e .
# Install matching CUDA torch if needed, then:
pip freeze > $HOME/mini-mythos-gate1/env_freeze.txt

# 4. Run smoke from OpenMythos, pointing at Parcae clone for HEAD check
cd $HOME/mini-mythos-gate1/OpenMythos
python research/mini_mythos/scripts/p1c_gpu_smoke.py \
  --parcae-dir $HOME/mini-mythos-gate1/parcae \
  --steps 4 --micro-batch 2 --seq-len 128 \
  --out $HOME/mini-mythos-gate1/p1c_gate1_smoke.json \
  --log $HOME/mini-mythos-gate1/p1c_gate1_smoke.log

# 5. Inspect
cat $HOME/mini-mythos-gate1/p1c_gate1_smoke.json
```

## CPU contract check (no GPU)

```bash
cd $HOME/mini-mythos-gate1/OpenMythos
python research/mini_mythos/scripts/p1c_cpu_contract_check.py
```

## Failure path simulation (CPU)

```bash
python research/mini_mythos/scripts/p1c_gpu_smoke.py --simulate-fail nonfinite --out /tmp/sim.json
# expect exit 1 and status FAIL in JSON
```

## Notes

- Synthetic labels are used. This is a mechanism smoke, **not** a language-learning validation.
- Official training shifts labels for next-token prediction; smoke uses identical tensors for interface check only.
- Timing includes gradient diagnostic loops.
- `gpu_tested=true` only after GPU operators executed **and** all checks completed.
- Official MuonAdamW remains NOT TESTED.
- Actual sampled recurrence remains NOT MEASURED unless explicitly captured.

## Cost control

After any run: manually Terminate the Pod in the dashboard and delete unused Network Volumes / Volume Disks. Confirm the billing page shows no active charges. Alerts are not hard stops.
