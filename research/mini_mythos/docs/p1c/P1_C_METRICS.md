# P1-C Metrics Specification

Required for controlled comparison (accuracy/loss, FLOPs, stability, cost):

- Train loss / Validation loss
- Gradient norm (and skip-nonfinite behavior)
- Recurrent state norm and residual
- DiagonalInjection decay coefficient
- Actual iteration / recurrence depth per step
- Tokens/sec, samples/sec
- Peak GPU memory
- Training FLOPs (or proxy)
- Inference FLOPs / cost at eval depths
- Checkpoint integrity and resume fidelity
- Training throughput and wall time

All must be logged consistently. Distinguish VERIFIED / MEASURED / ESTIMATED.
