#!/usr/bin/env bash
# Round 5 helper: run one command and append its record to a raw-output file.
#   bash logrun.sh OUTFILE CMD [ARG...]
# Appends "$ <CMD shell-quoted>", the combined stdout+stderr of CMD (unaltered), and "exit=<code>".
# Returns the command's exit code. Header lines are written by the caller.
set -u
out="$1"; shift
printf '$' >> "$out"; printf ' %q' "$@" >> "$out"; printf '\n' >> "$out"
"$@" >> "$out" 2>&1
rc=$?
printf 'exit=%d\n' "$rc" >> "$out"
exit "$rc"
