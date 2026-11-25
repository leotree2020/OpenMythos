#!/usr/bin/env bash
# Implementation stage C (C1, round 3) audit: run one command and write its complete stdout+stderr (merged) to one file,
# command line first, exit code last.  usage: ic4_run_logged.sh <out_file> <command> [args...]
# PYTHONDONTWRITEBYTECODE=1 (and -B on every python call of these scripts): no .pyc file is written.
out="$1"; shift
export PYTHONDONTWRITEBYTECODE=1
{
  echo "# Data Auditor run (implementation stage C, C1 work commit, round 3). host $(hostname), Anthropic cloud container, CPU only (no GPU device node: $(ls /dev | grep -c '^nvidia') nvidia entries), no model weights loaded (tokenizer files only; the probe's tiny models are random); $(date -u '+%Y-%m-%d %H:%M:%S UTC'); cwd $(pwd)"
  echo "# stdout and stderr merged, complete, unedited"
  printf '$'; printf ' %q' "$@"; echo
  "$@"
  echo "exit=$?"
} > "$out" 2>&1
tail -n 3 "$out"
