# F2-C B2-R1

Status: **PENDING CHATGPT REVIEW**. Not a final F2-C PASS.

## Guards

- Actual `--manifest` file blob is checked with `git hash-object`.
- A copied manifest with a non-selection field changed is rejected.
- Status rank is FAIL > BLOCKED > INCONCLUSIVE > PASS. Unstable no longer hides FAIL.
- Import path, 247936 params, core ownership, storage alias, and restore checks are enforced.
- Research repo is found from `__file__`, not a hardcoded `/tmp/om`.

## Replay

Same three frozen scalars, seed 42, h grid, and input. Local status PASS. Exit 0. Original B1 manifest unchanged.
