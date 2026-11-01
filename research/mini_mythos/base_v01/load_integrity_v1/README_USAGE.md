# CPU complete checkpoint loading check

Read PROTOCOL.md and CHECKPOINT.md. Use only the designated Codespace and its frozen CPU environment. This stage tests the official loading path, not B1's historical A5 criterion. Do not invoke B1 or the completed RoPE diagnostic.

After source and static reviews are committed as A and the freeze checkpoint as B, invoke once:

```bash
/workspaces/mythos-base-v01-cpu312/bin/python -B /workspaces/mythos-base-v01-rope-diag-v11/research/mini_mythos/base_v01/load_integrity_v1/run_load_check.py --execute --implementation-commit FULL_IMPLEMENTATION_SHA --run-id load-v1-YYYYMMDDTHHMMSSZ
```

Use the recorded full A commit and actual UTC launch time. The implementation asserts the new branch `mythos-base-v01-cpu-load-v1`; the reused worktree path retains its old directory name.

The root `/workspaces/mythos-evidence/base_v01/load_integrity` must not already exist. Existing evidence or a failed attempt is not permission to delete it or change the run-id. Do not use an import, `--help`, fixture or another machine as a rehearsal. No package install, weight download, config override or manual tensor assignment.

Read public/summary.json, check records, every tensor row, state_comparison.json, loading_acceptance.json and invariance.json. A partial run may not have all files; check its first stop and any EMERGENCY record. Never infer PASS from exit 0. An original-metadata/reference read and the official loader's internal read are two reads in one experiment, not two model-loading runs.

After any outcome, preserve the run and operator output, verify all manifest entries with file hashes only, review the evidence, explicitly stage public records/documentation, commit the result checkpoint and push normally. No repair/retry after results. Keep private logs/baselines on the target. The old A5, forward, generation and training statuses remain unchanged. Stop after sealing this stage.
