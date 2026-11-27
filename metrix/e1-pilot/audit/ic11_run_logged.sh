#!/usr/bin/env bash
# Implementation stage C, C4 code commit (Review Gate ruling of 2026-11-27, tasks/IMPL_C4_RULING.md; staged tree
# 63121c79, parent 3bc761ea), round 1 audit: run one command and write its complete stdout+stderr (merged) to one file,
# command line first, exit code last.
#   usage: ic11_run_logged.sh <out_file> <command> [args...]
# PYTHONDONTWRITEBYTECODE=1 (and -B on every python call of these scripts): no .pyc file is written.
# GIT_OPTIONAL_LOCKS=0: git status in the pilot repository does not refresh (rewrite) the index file.
# Data Auditor's own script (my ic10_run_logged.sh with this round's header).
out="$1"; shift
export PYTHONDONTWRITEBYTECODE=1
export GIT_OPTIONAL_LOCKS=0
{
  echo "# Data Auditor run (implementation stage C, C4 code commit, staged tree 63121c792654e53fce2bb1418b6413b3a275c126, parent 3bc761ea1d1cb7a1bf5a7a89d4084055e4ca83d1, round 1). host $(hostname), Anthropic cloud container, CPU only (no GPU device node: $(ls /dev | grep -c '^nvidia') nvidia entries), no model weights loaded (tokenizer files only; smoke checkpoints are hashed as file bytes, never loaded; the Executor's tests build random tiny models in memory); $(date -u '+%Y-%m-%d %H:%M:%S UTC'); cwd $(pwd)"
  echo "# stdout and stderr merged, complete, unedited"
  printf '$'; printf ' %q' "$@"; echo
  "$@"
  echo "exit=$?"
} > "$out" 2>&1
tail -n 3 "$out"
