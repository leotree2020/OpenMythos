# Config Verification (static)

| Check | Status |
|-------|--------|
| A/B1/B2/C unique run_name and out_dir | PASS (static) |
| A has no exit_at_step | PASS (static) |
| B1 exit_at_step=4 | PASS (static) |
| B2/C resume=true | PASS (static) |
| A/B1 same seed and model | PASS (static) |
| B2 uses patched train.py, C uses unpatched | DOCUMENTED, runtime NOT TESTED |
| resume_checkpoint_path injection | NOT TESTED (must be filled before launch) |
| tokenizer_path absolute | NOT TESTED (fill on launch host) |
| native CLI parse | NOT TESTED |
| auto-exit / cost stop | DOCUMENTED in COST_GUARD.md, runtime NOT TESTED |

YAML uniqueness is not a CLI PASS.
