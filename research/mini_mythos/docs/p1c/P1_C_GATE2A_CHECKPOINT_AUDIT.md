# P1-C Gate 2A — Checkpoint / Resume Integrity Audit

**Static analysis. No checkpoint created or loaded. All runtime behavior NOT TESTED.**

## Known upstream behaviors (from prior train.py inspection and task notes)

1. **LR Scheduler on resume**: Upstream restore logic may keep the newly created scheduler rather than fully restoring the checkpointed scheduler state. Impact: LR trajectory after resume may diverge from continuous training. **Risk: Medium. Must be measured.**
2. **Extra batch skip on resume**: Code contains logic that advances the dataloader by one batch on resume. Correctness depends on whether the saved cursor already points past the last consumed batch. **Risk: Medium. Requires exact next-batch comparison.**
3. **Save interval vs microbatch**: `save_step_interval` is tied to microbatch / fabric step counting, not pure optimizer steps. A setting of 1024 does **not** guarantee a save every 1024 optimizer steps. **Risk: High for smoke planning.**

## Future test definition (not executed)

### Continuous baseline
- Train N optimizer steps from seed S, save final state.

### Resume baseline
- Train N/2 steps, checkpoint, resume, continue to N.

### Comparisons (PASS if all hold)
- Model parameters: relative tolerance 1e-5 (or exact for bf16).
- MuonAdamW optimizer state: momentum buffers match within 1e-5.
- Scheduler state: current step and LR match (or document intentional divergence).
- RNG: torch, cuda, numpy, python match so next sample is identical.
- Sampled recurrence depths: next batch depths match.
- Next training batch: exact token match.
- Loss / grad norm continue without jump beyond tolerance.

**Any mismatch → FAIL.**

## Required state to capture for resume verification

- model.state_dict()
- optimizer.state_dict() (Muon + AdamW groups)
- scheduler.state_dict() if available
- torch.random.get_rng_state(), torch.cuda.get_rng_state(), numpy, random
- dataloader state (StatefulDataLoader)
- current microbatch / optimizer step counters
- last sampled depth pair

**Do not modify upstream checkpoint code to hide issues.**
