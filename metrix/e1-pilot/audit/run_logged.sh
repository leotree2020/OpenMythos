#!/usr/bin/env bash
# Run one audit command and write its complete stdout+stderr (merged) to one file, command line first.
# usage: run_logged.sh <out_file> <command> [args...]
out="$1"; shift
{
  echo "# Data Auditor run. host $(hostname), CPU only (no GPU, no torch, tokenizer files only); $(date -u '+%Y-%m-%d %H:%M:%S UTC'); cwd $(pwd)"
  echo "# stdout and stderr merged, complete, unedited"
  printf '$'; printf ' %q' "$@"; echo
  "$@"
  echo "exit=$?"
} > "$out" 2>&1
cat "$out"
