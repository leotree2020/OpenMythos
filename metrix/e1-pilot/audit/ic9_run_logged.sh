#!/usr/bin/env bash
# Implementation stage C, C2 second fix commit (staged tree a6ce8a0e, parent 0cbee197), round 1 audit: run one command and write
# its complete stdout+stderr (merged) to one file, command line first, exit code last.
#   usage: ic9_run_logged.sh <out_file> <command> [args...]
# PYTHONDONTWRITEBYTECODE=1 (and -B on every python call of these scripts): no .pyc file is written.
# GIT_OPTIONAL_LOCKS=0: git status in the pilot repository does not refresh (rewrite) the index file.
# Data Auditor's own script.
out="$1"; shift
export PYTHONDONTWRITEBYTECODE=1
export GIT_OPTIONAL_LOCKS=0
{
  echo "# Data Auditor run (implementation stage C, C2 second fix commit, staged tree a6ce8a0ea0aeff1e86443a2a22a2a4eb349bcc50, parent 0cbee197, round 1). host $(hostname), Anthropic cloud container, CPU only (no GPU device node: $(ls /dev | grep -c '^nvidia') nvidia entries), no model weights loaded (tokenizer files only; smoke checkpoints are hashed as file bytes, never loaded; the Executor's e2e test builds random tiny models in memory); $(date -u '+%Y-%m-%d %H:%M:%S UTC'); cwd $(pwd)"
  echo "# stdout and stderr merged, complete, unedited"
  printf '$'; printf ' %q' "$@"; echo
  "$@"
  echo "exit=$?"
} > "$out" 2>&1
tail -n 3 "$out"
