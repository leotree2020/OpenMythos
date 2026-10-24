# Evidence Format

Tensors are stored as sidecar `.bin` files named by SHA-256.
JSON holds index entries: name, shape, dtype, numel, sha256, blob.

## source

| Value | Meaning |
|-------|---------|
| SYNTHETIC | self-test only; rejected for acceptance |
| CPU_PARCAE | real Parcae objects on CPU; model/optimizer consistency only |
| GPU_RUNTIME | actual GPU training run |

## GPU NUMERICAL PASS

Returned only when all structural checks pass AND:
- every run has `source=GPU_RUNTIME`
- `optimizer_class=MuonAdamW`
- CUDA RNG status is `COLLECTED` at before_save and after_load for B2/C

Otherwise the best structural result is `STRUCTURAL PASS`.
CPU consistency is not training-path numerical equivalence.
