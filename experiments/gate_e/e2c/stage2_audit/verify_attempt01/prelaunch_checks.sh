#!/bin/bash
# E2-c stage-2 formal verify: the ten pre-launch checks (read-only; nothing in the repository is written)
export GIT_OPTIONAL_LOCKS=0 PYTHONDONTWRITEBYTECODE=1
SHA=1f6524441c2a08a583be9acc38d14b09848d11d1
REPO=/home/user/OpenMythos
E=$REPO/experiments/gate_e/e2c
RUN=$(cd "$(dirname "$0")" && pwd)
fail=0
ok() { echo "PASS $1"; }
no() { echo "FAIL $1"; fail=1; }
echo "# pre-launch checks $(date -u +%FT%T.%3NZ)"
# 1-2 HEAD local and remote
l=$(git -C $REPO rev-parse HEAD); r=$(git -C $REPO ls-remote origin refs/heads/claude/openmythos-research | cut -f1)
[ "$l" = $SHA ] && ok "1 local HEAD $l" || no "1 local HEAD $l"
[ "$r" = $SHA ] && ok "2 remote claude/openmythos-research $r" || no "2 remote $r"
# 3 clean tree, no operation in progress
st=$(git -C $REPO status --porcelain --untracked-files=all | wc -l)
ops=$(ls -d $REPO/.git/MERGE_HEAD $REPO/.git/rebase-merge $REPO/.git/rebase-apply $REPO/.git/CHERRY_PICK_HEAD 2>/dev/null | wc -l)
[ "$st" = 0 ] && [ "$ops" = 0 ] && ok "3 working tree clean (status lines $st, operations in progress $ops)" || no "3 working tree: status lines $st, operations $ops"
# 4-5 frozen code tree and frozen inputs: the driver's own start checks, read-only (no ledger), plus fixed sha256
cd "$RUN" && python3 -B readonly_prestart.py $E > "$RUN/prelaunch_prestart_replica.txt" 2>&1; rc=$?
grep -q "^prestart: PASS" "$RUN/prelaunch_prestart_replica.txt" && grep -q "frozen code files differing from the HEAD blobs: \[\]" "$RUN/prelaunch_prestart_replica.txt" \
  && grep -q "code_tree_sha256 4888bbe314e48c01fff0ee23ff647788b8367f6b70e865d062ee00185b940c7f" "$RUN/prelaunch_prestart_replica.txt" && [ $rc = 0 ] \
  && ok "4 frozen code tree 4888bbe3...; only the four I2 changes since f7a0ffe; every file equal to its HEAD blob (driver prestart: would not refuse)" \
  || no "4 frozen code tree / driver prestart (see prelaunch_prestart_replica.txt, rc $rc)"
want="434f586996e49b5a493b5a346839756da7c653fc451bcba2b14438bfb00d6681  $E/E2C_PREREG_DRAFT.md
96f0df4883276b105a3026ed06f7ee09e1e9d3348895faf659fc689e4ed8d7d4  $E/DESIGN_REVIEW.md
5ff426c6b600506550eb91f72dad4fbde14c253c0629fec0968a0fb1600e3daa  $E/stage1/STAGE1_FINAL_AUDIT.md
c248e1ec1563e411894da1f1394af393bb19a6fd1e1d0b12c30834fd9076fe38  $E/stage1/STAGE1_FINAL_AUDIT.json
3f3ff565fc3fe681f789290d8df07d28f6defbd303890bafcc27542d2f98da7e  $E/stage1/STAGE1_FINAL_AUDIT_SHA256.txt
6c23606ebec922dcfe9a577260b9830ffac002da778e27ea39865cce30fff43f  $E/stage1/gate4/lambda_selected.json
a2301dc764393872ac82f4a083456a54fa0c4a826ebf92c08483e7f70dee87c2  $E/stage1/gate4/calibration.json
71068ae57e25da99b22910e40f36f9fb390c35c6b244ebe316b1ea9f247cc643  $E/stage1/environment.json
d22fcdab84c0ae85b49f0c7fd8c578a3f753b9b824a50654e8427f88ca4c259e  $REPO/experiments/gate_e/sets/manifest.json"
echo "$want" | sha256sum -c --quiet && t1=$(git -C $REPO rev-parse HEAD:experiments/gate_e/e2c/stage1) && t2=$(git -C $REPO rev-parse f7a0ffe:experiments/gate_e/e2c/stage1) \
  && [ "$t1" = "$t2" ] && grep -q "^E1 sets: PASS" "$RUN/prelaunch_prestart_replica.txt" \
  && ok "5 stage-1 final audit, preregistration, design review, lambda/lambda2, calibration, environment record, E1 manifest equal to the approved sha256; stage1/ tree $t1 = f7a0ffe; E1 sets PASS" \
  || no "5 frozen evidence sha256"
# 6 no stage-2 output, no history
n6=$(ls -d $E/stage2 $E/e2c_workload_freeze.json 2>/dev/null | wc -l); h6=$(git -C $REPO log --all --format=%h -- experiments/gate_e/e2c/stage2 experiments/gate_e/e2c/e2c_workload_freeze.json | wc -l)
[ "$n6" = 0 ] && [ "$h6" = 0 ] && ok "6 stage2/ and the freeze absent; never in the history" || no "6 stage2/ or freeze present ($n6) / in history ($h6)"
# 7 no E2-c process
pr=$(pgrep -af '[e]2c_stage2|[_]v2-worker|[e]2c_stage4|[t]rain_e2c|[r]un_e2c|[k]eyspace.py' | grep -v prelaunch_checks || true)
[ -z "$pr" ] && ok "7 no E2-c driver, V2 worker, job, trainer or launcher running" || no "7 running: $pr"
# 8 environment
env8=$(cd "$RUN" && python3 -B -c "
import sys, json, hashlib, subprocess, platform, os, numpy, torch
rec = json.load(open('$E/stage1/environment.json'))
now = {'python': sys.version, 'torch': torch.__version__, 'numpy': numpy.__version__}
pf = hashlib.sha256(subprocess.run([sys.executable, '-m', 'pip', 'freeze'], capture_output=True, text=True).stdout.encode()).hexdigest()
same = {k: rec.get(k) for k in now} == now and pf == rec['pip_freeze_sha256'] and platform.platform() == rec['platform'] and os.cpu_count() == rec['cpu_count']
print(('SAME' if same else 'DIFF'), now, 'pip', pf[:16], platform.platform(), 'cpus', os.cpu_count(), 'cuda', torch.cuda.is_available())")
case "$env8" in SAME*) ok "8 environment equal to the stage-1 record: ${env8#SAME }";; *) no "8 environment: $env8";; esac
# 9 disk and log location
av=$(df -B1M --output=avail $REPO | tail -1 | tr -d ' ')
[ "$av" -gt 2000 ] && [ -w "$RUN" ] && ok "9 disk ${av} MiB available; logs outside the repository in $RUN (survived the earlier container restart)" || no "9 disk $av MiB / log dir"
# 10 no test or stage variables
bad=$(env | cut -d= -f1 | grep -E '^(E2C_|STUB_)' || true)
[ -z "$bad" ] && ok "10 no E2C_* / STUB_* variable set (E2C_STAGE2_AUTHORIZED and PYTHONHASHSEED are set by the launcher for the driver only)" || no "10 set: $bad"
echo "pre-launch result: $([ $fail = 0 ] && echo GO || echo NO-GO)"
exit $fail
