# P1-C Gate 2A — Dependency Matrix

**All entries are static / NOT TESTED unless marked VERIFIED from prior Gate 1.**

| Dependency | Pin / Constraint | Status | Risk / Notes |
|------------|------------------|--------|--------------|
| torch | Gate 1 used 2.8.0+cu128; pyproject has torch221 / torchgte240 extras | VERIFIED (Gate 1) | Compatible enough for model construct + smoke |
| lightning | ==2.3.0.dev20240328 | NOT TESTED | Dev pin; may conflict with newer torch |
| torchdata | unpinned | NOT TESTED | StatefulDataLoader used for resume |
| axonn | git pin c5ef65d | BLOCKED | Not needed for single-GPU DDP/single; only for axonn_tp |
| wandb | unpinned | NOT TESTED | Offline mode recommended |
| numpy | <2.0 | NOT TESTED | Potential clash with newer stacks |
| datasets / transformers | >=2.18 / >=4.38 | NOT TESTED | For data/tokenizer |
| tokenizers | >=0.15.2 | NOT TESTED | |
| MuonAdamW | in-tree recpre/optim | NOT TESTED | Source present; not exercised on GPU yet |
| Parcae model | pinned 69284c1 | VERIFIED (Gate 1) | Construct + synthetic fwd/bwd PASS |

**CPU static checks performed**: file inspection only. No full environment install attempted in this task.
