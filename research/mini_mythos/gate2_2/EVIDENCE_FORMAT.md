# Evidence Schema

JSON fields used by the comparator:
- model_index: [{name, shape, dtype, numel, sha256, blob}]
- optimizer_index: same, plus discrete entries
- batch_hashes, losses, checkpoint_sha256, resume_from_sha256
- source: SYNTHETIC | CPU_PARCAE | GPU_RUNTIME
- optimizer_class
- rng_stages.before_save / after_load with cuda_status

Blobs are `.bin` files named by SHA-256. Comparator reads them and checks hash, shape, dtype, numel, key set, and raw bytes.

## Exit codes

| Status | Exit |
|--------|------|
| GPU NUMERICAL PASS | 0 |
| STRUCTURAL PASS | 1 |
| FAIL | 1 |
| MISSING | 2 |

GPU NUMERICAL PASS requires GPU_RUNTIME + MuonAdamW + collected CUDA RNG.
Relabeling source does not qualify. CPU_PARCAE cannot obtain it.
