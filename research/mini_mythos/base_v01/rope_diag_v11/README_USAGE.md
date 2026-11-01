# RoPE diagnostic — usage and scope

This is a single-run CPU diagnostic, not a B1 rerun. The protected B1 implementation and upstream are read-only. No model forward, training, generation or GPU is used.

## Before running

Read CHECKPOINT.md, PROTOCOL.md, STATIC_REVIEW.md and AUTHORIZATION_AND_SCOPE.md. The implementation must be committed and the diagnostic worktree clean. Verify the frozen implementation SHA recorded by the freeze checkpoint. No dynamic preflight, fixture or numerical helper tests are permitted before the formal attempt under this protocol.

The entry point imports only Python standard-library modules at import time. Do not use importing it as a substitute for static review. AST parsing reads source text without executing it.

## The one formal command

Run only inside Codespace bookish-pancake-vwqx7rr9x5w3wxjr, after the implementation commit has been frozen:

```bash
/workspaces/mythos-base-v01-cpu312/bin/python -B /workspaces/mythos-base-v01-rope-diag-v11/research/mini_mythos/base_v01/rope_diag_v11/run_rope_diag.py --execute --implementation-commit FULL_FROZEN_IMPLEMENTATION_SHA --run-id rope-v11-YYYYMMDDTHHMMSSZ
```

The placeholders must be replaced with the recorded implementation SHA and actual UTC launch timestamp. This command is documentation, not evidence that it ran. No --help/dry-run/fixture execution is needed. The --native-child entry is internal to N3; never invoke it manually.

The runner exclusively creates /workspaces/mythos-evidence/base_v01/rope_diag, then its one run directory and CLAIM.json before importing Torch. If the root already exists, do not delete it or use another directory. Recover the existing evidence and stop.

## Results and stop rules

A return code is not a scientific verdict. Read public/summary.json, the per-check records and manifests. A guard BLOCKED/FAIL stops the numerical path and only seals completed evidence. G2 failure leaves all T/P/R/Q and their metrics NOT TESTED. Do not fix code and rerun after observing the formal result.

private/ contains S, all native/control/candidate tensors and repeats, secondary FP64 data, detailed metrics, logs and runtime snapshots. FULL_MANIFEST.json covers both classes. Only public/ may be copied into Git after checking its contents. Keep the private evidence on the target; do not publish weights, S, detailed constraints or raw tensor values. Manifest exclusions are stated explicitly to avoid self-reference.

On an emergency sealing failure, preserve CLAIM.json and every partial file, plus the terminal output. Perform only evidence recovery/hash/Git/checkpoint operations, not further numeric computations.

Write a result checkpoint, commit explicitly selected public evidence/documentation, normal push and stop. Do not change A5's 1e-6 threshold or B1's BLOCKED status; do not enter B2/D2-A or operate PR #24.
