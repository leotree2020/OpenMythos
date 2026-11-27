#!/usr/bin/env bash
# Implementation stage C (C1 second submission, fix commit, round 1) audit: run one command and write its complete stdout+stderr
# (merged) to one file, command line first, exit code last.  usage: ic6_run_logged.sh <out_file> <command> [args...]
# PYTHONDONTWRITEBYTECODE=1 (and -B on every python call of these scripts): no .pyc file is written.
# GIT_OPTIONAL_LOCKS=0: git status in the pilot repository does not refresh (rewrite) the index file.
out="$1"; shift
export PYTHONDONTWRITEBYTECODE=1
export GIT_OPTIONAL_LOCKS=0
{
  echo "# Data Auditor run (implementation stage C, C1 second submission, fix commit (staged tree ae5fcb2f, parent ae60e0f), round 1). host $(hostname), Anthropic cloud container, CPU only (no GPU device node: $(ls /dev | grep -c '^nvidia') nvidia entries), no model weights loaded (tokenizer files only; tiny models are random-initialised in memory); $(date -u '+%Y-%m-%d %H:%M:%S UTC'); cwd $(pwd)"
  echo "# stdout and stderr merged, complete, unedited"
  printf '$'; printf ' %q' "$@"; echo
  "$@"
  echo "exit=$?"
} > "$out" 2>&1
tail -n 3 "$out"
