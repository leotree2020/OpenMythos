#!/usr/bin/env bash
# Round 6, task 2: the exception guard (run_guarded) must not change the normal path of a check script.
# Runs each guarded script twice with identical arguments: the version under OLD (reports/ as of f4d8e988,
# extracted with git archive) and the version in this working tree. Compares exit codes and the combined
# stdout+stderr byte for byte, then prints the new output in full.
# Not covered here: l6_check.py (its logic changed in round 6; compared with round 5 in t2_l6_check.txt), and
# blind_handback_check.py and records_check.py (their inputs, round-4 event pages and round-5 subagent transcripts,
# are not in this container).
#   bash guard_ab.sh OLD_REPORTS_DIR OUT_DIR PY QWEN_TOK_DIR FACTS.json PARQUET_CACHE_DIR      (run from the repo root)
# Round 6, after the data-auditor's BLOCK (reviews/599230f9.../data-auditor.md, item E3): this harness is a check
# script as well. Its last line is RESULT: PASS or RESULT: FAIL; on any other exit (wrong number of arguments, an
# error before the end) the EXIT trap prints RESULT: FAIL and the exit code is non-zero.
RESULT_DONE=0
on_exit() { rc=$?; if [ "$RESULT_DONE" = 0 ]; then echo "RESULT: FAIL"; [ "$rc" = 0 ] && rc=1; fi; exit "$rc"; }
trap on_exit EXIT
set -u
if [ $# -ne 6 ]; then echo "usage: bash guard_ab.sh OLD_REPORTS_DIR OUT_DIR PY QWEN_TOK_DIR FACTS.json PARQUET_CACHE_DIR" >&2; exit 2; fi
OLD="$1"; OUT="$2"; PY="$3"; TOK="$4"; FACTS="$5"; CACHE="$6"
NEW=metrix/e1-pilot/reports
M=metrix/e1-pilot
mkdir -p "$OUT"
cases=(
  "template_overlap|round1/template_overlap.py|--split-manifest $M/SPLIT_MANIFEST.json"
  "y_ratio|round2/y_ratio.py|--manifest $M/DATA_MANIFEST.json --split-manifest $M/SPLIT_MANIFEST.json --tokenizer-dir $TOK"
  "anchor_check|round2/anchor_check.py|--manifest $M/DATA_MANIFEST.json --tokenizer-dir $TOK --facts $FACTS --cache-dir $CACHE --anchor-out $OUT/anchor_ab.json"
  "candidate_feasibility_r3|round3/candidate_feasibility_r3.py|--facts $FACTS --split-manifest $M/SPLIT_MANIFEST.json --tokenizer-dir $TOK"
  "outside_metrix_check|round3/outside_metrix_check.py|--rev f4d8e988a31f99527cc0bc6be5ceacc709bda2f1"
  "verify_scoring|round3/verify_scoring.py|--facts $FACTS --split-manifest $M/SPLIT_MANIFEST.json --tokenizer-dir $TOK"
  "st_prefix_check|round4/st_prefix_check.py|--facts $FACTS --split-manifest $M/SPLIT_MANIFEST.json --tokenizer-dir $TOK"
  "recover_blind|round5/recover_blind.py|rebuild --source $M/reports/round4/blind/source_events.jsonl --timeline $M/reports/round4/t6_blind_timeline.txt --out-dir $OUT/blind_rebuilt"
)
same_all=0
for c in "${cases[@]}"; do
  IFS='|' read -r name rel args <<< "$c"
  mkdir -p "$OUT/blind_rebuilt"
  # shellcheck disable=SC2086
  "$PY" "$OLD/$rel" $args > "$OUT/$name.old" 2>&1; rc_old=$?
  # shellcheck disable=SC2086
  "$PY" "$NEW/$rel" $args > "$OUT/$name.new" 2>&1; rc_new=$?
  if cmp -s "$OUT/$name.old" "$OUT/$name.new" && [ "$rc_old" = "$rc_new" ]; then same=True; same_all=$((same_all + 1)); else same=False; fi
  echo "== $name: $PY {OLD,NEW}/$rel $args"
  echo "   exit old $rc_old new $rc_new | output bytes old $(wc -c < "$OUT/$name.old") new $(wc -c < "$OUT/$name.new") | sha256 old $(sha256sum < "$OUT/$name.old" | cut -c1-16) new $(sha256sum < "$OUT/$name.new" | cut -c1-16) | identical: $same"
done
echo "identical (output and exit code): $same_all of ${#cases[@]}"
for c in "${cases[@]}"; do
  IFS='|' read -r name rel args <<< "$c"
  echo "---------- new output: $name"
  cat "$OUT/$name.new"
done
RESULT_DONE=1
if [ "$same_all" = "${#cases[@]}" ]; then echo "RESULT: PASS"; exit 0; fi
echo "RESULT: FAIL"
exit 1
