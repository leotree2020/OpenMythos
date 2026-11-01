# One authorized CPU inference check

Read PROTOCOL.md and CHECKPOINT.md first. Only the named Codespace, existing frozen
venv, upstream, artifacts and isolated checkout are allowed. No downloads/install.

1. Review/AST-check source without importing numerical libraries. Freeze commit A
   with source, protocol, static review. Commit B contains the execution checkpoint
   with full A hash. Verify clean checkout and unchanged pins before execution.
2. Once only, from the target's frozen interpreter:

```sh
/workspaces/mythos-base-v01-cpu312/bin/python -B \
  /workspaces/mythos-base-v01-rope-diag-v11/research/mini_mythos/base_v01/cpu_inference_v1/run_forward_check.py \
  --execute --implementation-commit FULL_A_SHA --run-id inference-v1-YYYYMMDDTHHMMSSZ
```

The coordinator launches two sequential fresh interpreters: first worker has
planned first/repeat passes; reload worker has one pass. It writes a terminal
summary and manifests. An operator should preserve launch/completion records and
redirect coordinator stdout/stderr outside the run directory so its manifest is
not invalidated by live logging. Do not run worker.py manually or retry a run.

3. Read-only audit every manifest entry and partial/complete gate record. If
   engineering PASS, perform the already frozen AI quality review on first-pass
   text; no further numerical evaluation. Commit all public evidence and exported
   full manifest, keeping raw logits on target. Write final checkpoint with exact
   commits, environment, results, limits and one next instruction. Normal push.
4. Stop. No B1 runner, B2, D2-A, upstream edits, A5 changes or PR #24 action.
