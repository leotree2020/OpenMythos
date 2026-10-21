#!/bin/bash
# read-only status of the running stage-2 verify (no write in the repository)
E=/home/user/OpenMythos/experiments/gate_e/e2c
RUN=$(cd "$(dirname "$0")" && pwd)
echo "== $(date -u +%FT%TZ)"
cd "$RUN" && PYTHONDONTWRITEBYTECODE=1 python3 -B ledger_status.py $E/stage2/budget_ledger_s2.json
L=$E/stage2/attempts/01/driver_log.txt
[ -f $L ] && tail -n 6 $L | cut -c1-240
n=$(cat $E/stage2/attempts/01/v2_worker_*.txt 2>/dev/null | grep -c '^V2 seed'); echo "V2 seeds done: $n / 33"
ls $E/stage2/attempts/01/v2 2>/dev/null | wc -l | sed 's/^/seed files: /'
ps -eo pid,ppid,etimes,pcpu,args | grep -E '[e]2c_stage2.py|[e]2c_stage4.py|[k]eyspace.py' | cut -c1-150
grep -E "exit_code|end_utc" $RUN/launch_record.txt
ls $E/stage2 2>/dev/null | tr '\n' ' '; echo
