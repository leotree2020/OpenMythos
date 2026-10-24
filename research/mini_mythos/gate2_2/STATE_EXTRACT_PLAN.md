# State Extraction Plan (for the GPU run; not executed)

After each of A, B1, B2, C, write an evidence JSON with:

- batch_hashes: SHA-256 of each microbatch input
- losses: float per optimizer boundary
- model_state: per-key shape, dtype, sha256 or values
- optimizer_state: full MuonAdamW state_dict (param_groups + state)
- scheduler: state_dict and lr_trace
- microbatch_step, optimizer_step, update_count
- rng: cpu, cuda, python, numpy
- checkpoint_sha256
- resume_from_sha256 (B2 and C)

Then:
```
python compare_equivalence.py A.json B1.json B2.json C.json
```
Exit 0 only if every required check passes.
