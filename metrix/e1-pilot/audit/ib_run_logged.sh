#!/usr/bin/env bash
# Implementation stage B audit: run one command and write its complete stdout+stderr (merged) to one file,
# command line first, exit code last.  usage: ib_run_logged.sh <out_file> <command> [args...]
# The given venv has torch installed; whether a script imported it is printed by the script itself (ia_common.run).
# PYTHONDONTWRITEBYTECODE=1: no .pyc file is written anywhere (in particular not under metrix/e1-pilot/src/).
out="$1"; shift
export PYTHONDONTWRITEBYTECODE=1
{
  echo "# Data Auditor run (implementation stage B). host $(hostname), CPU only (no GPU device), no model weights loaded (tokenizer files only); $(date -u '+%Y-%m-%d %H:%M:%S UTC'); cwd $(pwd); PYTHONDONTWRITEBYTECODE=$PYTHONDONTWRITEBYTECODE"
  echo "# stdout and stderr merged, complete, unedited"
  printf '$'; printf ' %q' "$@"; echo
  "$@"
  echo "exit=$?"
} > "$out" 2>&1
cat "$out"
