# Evidence Schema 2.2-c

Required: schema_version, model_index, optimizer_index, optimizer_param_groups,
batch_hashes, losses, scheduler, microbatch_step, optimizer_step, update_count,
checkpoint_sha256, source, optimizer_class, integrity, resume_from_sha256.

integrity is SHA-256 of canonical metadata. Changing source without recomputing it fails.

## GPU NUMERICAL PASS (exit 0)

All of: hash match, loss within 1e-4, model numeric compare, optimizer index + param_groups,
scheduler, counts, checkpoint identity, RNG save/restore, C offset,
source=GPU_RUNTIME, optimizer_class=MuonAdamW, CUDA RNG COLLECTED, integrity match.

`--logic-test` exercises this path and labels the result LOGIC TEST.
That is not a real GPU run.

STRUCTURAL PASS and FAIL exit 1. MISSING exits 2.
