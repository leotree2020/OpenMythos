#!/usr/bin/env bash
# Fault-injection tests of run_budget.sh, verify_runs.py and analyze_budget.py
# (revision 2). Non-formal seeds 97-99, short runs, test mode only: nothing
# is written to budget_a/runs and test2 is never evaluated. Results go to
# smoke/faults/ (RESULTS.txt plus each case's launcher log).
set -uo pipefail
cd "$(dirname "$0")/../.."
export PYTHONPATH=.
D=experiments/budget_a GA=experiments/gen_gate_a
F=$D/smoke/faults
rm -rf "$F"; mkdir -p "$F/refs"
R=$F/RESULTS.txt
pass=0 failn=0
check() {  # name expected actual detail
  if [ "$2" = "$3" ]; then r=PASS pass=$((pass + 1)); else r=FAIL failn=$((failn + 1)); fi
  echo "$r | $1 | expected $2, got $3 | $4" | tee -a "$R"
}
trainers() { ps -eo args | grep -c '[t]rain_level.py.*smoke/faults' || true; }
started() { grep -c 'started A_' "$1/logs/launcher_status.txt" || true; }
killed() { grep -c 'killed A_' "$1/logs/launcher_status.txt" || true; }

# references: weights after 40 steps of the extended schedule, per run
for s in 97 98 99; do for a in openmythos transformer; do
  python $GA/train_level.py --level A --arm $a --seed $s --steps 40 --schedule extended \
    --out $F/refs/A_${a}_s$s.json > $F/refs/A_${a}_s$s.log 2>&1 &
done; done; wait
cp -r $F/refs $F/refs_bad
python - "$F/refs_bad/A_transformer_s97.pt" <<'EOF'
import sys, torch
ck = torch.load(sys.argv[1], weights_only=False)
k = next(iter(ck["model"])); ck["model"][k] = ck["model"][k] + 1e-3
torch.save(ck, sys.argv[1])
EOF
cp -r $F/refs $F/refs_missing; rm $F/refs_missing/A_transformer_s97.pt

run() {  # dir refdir steps [extra env...]
  local dir=$1 ref=$2 steps=$3; shift 3
  env BUDGET_TEST_DIR=$dir REF_DIR=$ref STEPS=$steps "$@" bash $D/run_budget.sh > $dir.out 2>&1
}

# T1 normal launch: all six finish, results verified, dev eval and verdict
mkdir -p $F/t1; run $F/t1 $F/refs 250; rc=$?
check "T1 normal launch" 0 $rc "verdict.md: $(test -s $F/t1/verdict.md && echo written || echo missing)"

# T2 relaunch on top of existing outputs
run $F/t1 $F/refs 250; rc=$?
check "T2 stale outputs present -> refuse" 5 $rc "$(tail -1 $F/t1.out)"

# T3 comparability failure (transformer s97 reference perturbed by 1e-3)
mkdir -p $F/t3; run $F/t3 $F/refs_bad 2000; rc=$?
check "T3 comparability failure -> exit 3" 3 $rc "$(grep -h 'COMPARABILITY' $F/t3/logs/launcher_status.txt)"
check "T3 seed-99 runs never started" 4 "$(started $F/t3)" "started=$(started $F/t3) of 6"
check "T3 running trainings killed" 3 "$(killed $F/t3)" "killed=$(killed $F/t3)"
check "T3 nothing evaluated" no "$(ls $F/t3/runs/eval_* $F/t3/verdict.md >/dev/null 2>&1 && echo yes || echo no)" ""
check "T3 no trainer left running" 0 "$(trainers)" ""

# T4 a training killed from outside (SIGKILL, no result, no ABORTED record)
mkdir -p $F/t4; run $F/t4 $F/refs 2000 & lp=$!
for _ in $(seq 100); do pid=$(pgrep -f 'train_level.py.*--arm openmythos --seed 98.*faults/t4' | head -1); [ -n "$pid" ] && break; sleep 0.2; done
sleep 3; kill -9 "$pid"; wait $lp; rc=$?
check "T4 trainer SIGKILL -> exit 4" 4 $rc "$(grep -h 'RUN ERROR' $F/t4/logs/launcher_status.txt)"
check "T4 seed-99 runs never started" 4 "$(started $F/t4)" "started=$(started $F/t4)"
check "T4 running trainings killed" 3 "$(killed $F/t4)" "killed=$(killed $F/t4)"
check "T4 no trainer left running" 0 "$(trainers)" ""

# T5 a training crashing with a Python error (reference checkpoint missing)
mkdir -p $F/t5; run $F/t5 $F/refs_missing 2000; rc=$?
check "T5 trainer exception -> exit 4" 4 $rc "$(grep -h 'RUN ERROR' $F/t5/logs/launcher_status.txt)"
check "T5 no ABORTED record written" no "$(ls $F/t5/runs/*ABORTED* >/dev/null 2>&1 && echo yes || echo no)" ""
check "T5 no trainer left running" 0 "$(trainers)" ""

# T6 launcher itself terminated
mkdir -p $F/t6; run $F/t6 $F/refs 2000 & lp=$!
sleep 8; kill -TERM "$(pgrep -n -f 'bash experiments/budget_a/run_budget.sh')"; wait $lp; rc=$?
check "T6 launcher SIGTERM -> exit 130" 130 $rc "$(grep -h 'interrupted' $F/t6/logs/launcher_status.txt)"
check "T6 no trainer left running" 0 "$(trainers)" ""

# T7 formal mode refuses test overrides (stops before anything is created)
STEPS=60 bash $D/run_budget.sh > $F/t7.out 2>&1; rc=$?
check "T7 override without test mode -> refuse" 5 $rc "$(cat $F/t7.out)"

# T8 verify_runs.py on corrupted copies of the T1 results
V="python $D/verify_runs.py --seeds 97,98,99 --steps 250 --save-at 20,40 --compare-at 40 --ref-dir $F/refs"
mut() {  # name python-mutation
  local m=$F/t8_$1; rm -rf $m; cp -a $F/t1/runs $m; rm -f $m/eval_*
  (cd $m && eval "$2"); $V --dir $m --marker $m/.launch_marker > $m.out 2>&1; local rc=$?
  check "T8 verify: $1" 1 $rc "$(grep FAIL $m.out | tr "\n" " ")"
}
mutj() { echo "import json; p='$1'; r=json.load(open(p)); $2; json.dump(r, open(p, 'w'))"; }
cp -a $F/t1/runs $F/t8_clean; rm -f $F/t8_clean/eval_*
$V --dir $F/t8_clean --marker $F/t8_clean/.launch_marker > $F/t8_clean.out 2>&1
check "T8 verify: untouched T1 results" 0 $? "$(tail -1 $F/t8_clean.out)"
mut schedule "python -c \"$(mutj A_openmythos_s97.json "r['schedule']='cosine'")\""
mut steps "python -c \"$(mutj A_transformer_s98.json "r['steps']=50")\""
mut seed_in_json "python -c \"$(mutj A_transformer_s99.json "r['seed']=98")\""
mut comparability "python -c \"$(mutj A_openmythos_s99.json "r['comparability']['passed']=False")\""
mut no_comparability "python -c \"$(mutj A_openmythos_s98.json "r['comparability']=None")\""
mut ckpt_wrong_arm "python -c \"import torch; c=torch.load('A_openmythos_s97.pt',weights_only=False); c['arm']='transformer'; torch.save(c,'A_openmythos_s97.pt')\""
mut ckpt_wrong_step "python -c \"import torch; c=torch.load('A_transformer_s97_step40.pt',weights_only=False); c['step']=20; torch.save(c,'A_transformer_s97_step40.pt')\""
mut stale_file "touch -d '2000-01-01' A_transformer_s97.pt"
mut extra_file "cp A_transformer_s97.json A_transformer_s97_old.json"
mut aborted_record "echo '{}' > A_openmythos_s97_ABORTED.json"
mut missing_ckpt "rm A_openmythos_s98_step20.pt"

# T9 analyze_budget.py on altered decision records (from the T1 dev eval)
E=$F/t1/runs/eval_dev.jsonl
A="python $D/analyze_budget.py --split dev --seeds 97,98,99 --runs-dir $F/t1/runs"
$A $E > $F/t9_clean.out 2>&1; check "T9 analyze: untouched records" 0 $? ""
ana() {  # name python-filter-on-lines
  python -c "import json,sys; L=[json.loads(l) for l in open('$E')]; $2; sys.stdout.write(''.join(json.dumps(r)+'\n' for r in L))" > $F/t9_$1.jsonl
  $A $F/t9_$1.jsonl > $F/t9_$1.out 2>&1; local rc=$?
  check "T9 analyze: $1" 1 $rc "$(grep -m1 AssertionError $F/t9_$1.out)"
}
ana duplicate "L.append(L[1])"
ana missing "L.pop(1)"
ana foreign_seed "L[1]['seed']=5"
ana arm_swapped "c=[r for r in L if r['type']=='cell']; c[0]['arm']='transformer'"
ana wrong_ckpt "L[1]['ckpt']='elsewhere/A_x.pt'"
ana test2_split_claimed "L[0]['split']='test2'"

echo "TOTAL: $pass passed, $failn failed" | tee -a "$R"
[ $failn -eq 0 ]
