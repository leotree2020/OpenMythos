# P1-C Training FLOPs Note for Recurrent Core

The plain `6 × N × T` formula is insufficient for Parcae.

Observed from upstream / HF config (VERIFIED):
- mean_recurrence = 8
- mean_backprop_depth = 4
- sampling_scheme = poisson-truncated-full
- Recurrent block is shared and executed repeatedly

Implications (ESTIMATED):
- Forward FLOPs scale roughly with the number of core iterations (mean_recurrence).
- Backward FLOPs scale with mean_backprop_depth (gradient is not necessarily flowed through every iteration).
- Non-recurrent parts (prelude, coda, embeddings) scale once.

Until a precise FLOP counter is implemented or a profiler is run, report ranges rather than a single number.
This document exists to prevent misuse of the simple Transformer proxy.
