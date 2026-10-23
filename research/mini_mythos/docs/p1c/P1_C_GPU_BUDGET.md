# P1-C GPU & Cost Analysis (Arithmetic Corrected)

**All numbers ESTIMATED / NOT TESTED until Gate 1 JSON is produced.**

## Consistent example (do not treat as measured)

Assumption for illustration only: 10,000 tokens/s on A100 80GB.
- Tokens/step (official effective) = 256 × 2048 = 524,288
- Stage 1 (40 steps) = 20,971,520 tokens → ~35 min → ~0.58 GPU-hours
- At 200 JPY/hr → ~116 JPY for the compute portion of Stage 1

Real throughput, peak VRAM, and cost must be taken from `p1c_gate1_smoke.json` after an authorized run.

## Cost control

- Set alerts, but **alerts are not hard stops**.
- After any run: Stop/Terminate Pod in dashboard.
- Delete unused Network Volumes and Volume Disks (they continue billing).
- Verify billing page shows zero active compute.

Hard cumulative cap remains 5,000 JPY. Exceeding it is a stop condition.
