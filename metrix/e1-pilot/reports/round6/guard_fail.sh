#!/usr/bin/env bash
# Round 6, task 2: every guarded check script, on an exception or an early exit, prints RESULT: FAIL and exits
# non-zero. Runs each script under OLD (reports/ as of f4d8e988) and in this working tree with the same failing
# arguments (a missing input file, a git error, an argparse error, a pin mismatch), and prints for each: exit
# codes, the number of "RESULT: FAIL" lines in each output, then both outputs in full.
#   bash guard_fail.sh OLD_REPORTS_DIR OUT_DIR PY QWEN_TOK_DIR      (run from the repository root)
set -u
OLD="$1"; OUT="$2"; PY="$3"; TOK="$4"
NEW=metrix/e1-pilot/reports
M=metrix/e1-pilot
X=$OUT/does_not_exist.json
EVAL=research/mini_mythos/stage1/results/r1/eval_sets.jsonl
mkdir -p "$OUT"
cases=(
  "template_overlap|round1/template_overlap.py|--split-manifest $X"
  "y_ratio|round2/y_ratio.py|--manifest $X --split-manifest $M/SPLIT_MANIFEST.json --tokenizer-dir $TOK"
  "anchor_check|round2/anchor_check.py|--manifest $X --tokenizer-dir $TOK --cache-dir $OUT --anchor-out $OUT/anchor_fail.json"
  "candidate_feasibility_r3|round3/candidate_feasibility_r3.py|--facts $X --split-manifest $M/SPLIT_MANIFEST.json --tokenizer-dir $TOK"
  "outside_metrix_check|round3/outside_metrix_check.py|--rev 0000000000000000000000000000000000000000"
  "verify_scoring|round3/verify_scoring.py|--facts $X --split-manifest $M/SPLIT_MANIFEST.json --tokenizer-dir $TOK"
  "st_prefix_check|round4/st_prefix_check.py|--facts $X --split-manifest $M/SPLIT_MANIFEST.json --tokenizer-dir $TOK"
  "l6_check_no_args|round5/l6_check.py|"
  "blind_handback_check|round5/blind_handback_check.py|$X --source $X --blind-dir $OUT --handbacks-out $OUT/handbacks_fail.jsonl"
  "recover_blind|round5/recover_blind.py|rebuild --source $X --timeline $X --out-dir $OUT"
  "records_check_no_args|round5/records_check.py|"
)
ok_all=0
for c in "${cases[@]}"; do
  IFS='|' read -r name rel args <<< "$c"
  # shellcheck disable=SC2086
  "$PY" "$OLD/$rel" $args > "$OUT/$name.old" 2>&1; rc_old=$?
  # shellcheck disable=SC2086
  "$PY" "$NEW/$rel" $args > "$OUT/$name.new" 2>&1; rc_new=$?
  n_old=$(grep -c '^RESULT: FAIL$' "$OUT/$name.old"); n_new=$(grep -c '^RESULT: FAIL$' "$OUT/$name.new")
  if [ "$rc_new" != 0 ] && [ "$n_new" = 1 ]; then ok=True; ok_all=$((ok_all + 1)); else ok=False; fi
  echo "== $name: $PY {OLD,NEW}/$rel $args"
  echo "   exit old $rc_old new $rc_new | 'RESULT: FAIL' lines old $n_old new $n_new | new: non-zero exit and RESULT: FAIL: $ok"
done
# the sys.exit("message") path of the new l6_check.py: eval_sets.jsonl replaced by another file -> pin mismatch
"$PY" "$NEW/round5/l6_check.py" --eval-sets research/mini_mythos/stage1/results/r1/data_lock.json \
    --parcae-tokenizer "$X" --manifest "$M/DATA_MANIFEST.json" --tokenizer-dir "$TOK" --anchor "$X" \
    --general-out "$OUT/general_fail.json" > "$OUT/l6_check_pin.new" 2>&1; rc=$?
n=$(grep -c '^RESULT: FAIL$' "$OUT/l6_check_pin.new")
if [ "$rc" != 0 ] && [ "$n" = 1 ]; then ok=True; ok_all=$((ok_all + 1)); else ok=False; fi
echo "== l6_check_pin (new only): --eval-sets data_lock.json instead of $EVAL"
echo "   exit new $rc | 'RESULT: FAIL' lines new $n | new: non-zero exit and RESULT: FAIL: $ok"
echo "new scripts with non-zero exit and exactly one RESULT: FAIL line: $ok_all of $(( ${#cases[@]} + 1 ))"
for c in "${cases[@]}"; do
  IFS='|' read -r name rel args <<< "$c"
  echo "---------- old output: $name"
  cat "$OUT/$name.old"
  echo "---------- new output: $name"
  cat "$OUT/$name.new"
done
echo "---------- new output: l6_check_pin"
cat "$OUT/l6_check_pin.new"
[ "$ok_all" = $(( ${#cases[@]} + 1 )) ]
