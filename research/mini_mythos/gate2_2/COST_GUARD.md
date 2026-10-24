# Cost Guard (NOT AUTHORIZATION)

Prior caps (¥700 / run, ¥5,000 cumulative) are **not** a new launch authorization.
Reconfirm quote and balance immediately before any pod start.

## Stages (estimated, not measured)

| Stage | Cap |
|-------|-----|
| A continuous | part of 60 min window |
| B1 exit | part of same window |
| B2 resume | part of same window |
| C negative | part of same window |
| Total | ≤ 60 minutes |

## Cost formula

`cost ≈ gpu_hourly_rate * hours + disk_gb * disk_rate * hours + storage_after_stop`

Stop if projected cost ≥ ¥700 or elapsed ≥ 50 min (leave margin to terminate).

## Failure stop

1. Save logs, configs, checkpoint paths, nvidia-smi.
2. Terminate the Pod (not only the process).
3. Delete unneeded persistent volumes.
4. Confirm billing console shows no running resources.
5. Hash saved evidence.

## Status

READY FOR GPU AUTHORIZATION — free prerequisites on this branch are done.
This is **not** launch authorization. Do not start a pod in this round.
