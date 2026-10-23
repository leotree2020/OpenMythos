# P1-C GPU & Cost Analysis

## Measured Gate 1 Smoke Data (2026-10-23, A100-SXM4-80GB)

These numbers are **measured** for the specific smoke configuration only (micro-batch=2, seq_len=128, 4 steps, synthetic labels, AdamW). They must **not** be extrapolated to official full training (effective batch 256, seq 2048, MuonAdamW, etc.).

- Peak VRAM Allocated: 3.256 GiB
- Peak VRAM Reserved: 3.502 GiB
- Average Step Time: 0.2173 s
- Throughput: 1178.2 tokens/sec
- Historical RunPod price observed during the run period: approximately **$1.80/hr** (not a permanent quote; re-check before any future launch)

## Future Estimates (NOT MEASURED — for planning only)

Any projection for official Stage 1 / Gate 2 training (40 optimizer steps, full effective batch, real or properly shifted data) is **unmeasured**.

- Do **not** use the Gate 1 1178.2 tokens/sec figure to estimate official 40-step runtime.
- Do **not** use any unmeasured assumption such as 10,000 tokens/s.
- Before Gate 2 execution, the target configuration must be re-measured for throughput and cost on the actual instance.
- Hard cumulative budget cap remains 5,000 JPY. Exceeding it is a stop condition.

## Cost Control

- Billing alerts are **not** hard stops.
- After any run: manually Terminate the Pod in the dashboard.
- Delete unused Network Volumes and Volume Disks (storage continues to bill).
- Confirm the billing page shows no active compute charges.

All future runtime and cost numbers remain ESTIMATED until measured under the target configuration.
