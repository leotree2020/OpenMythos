#!/usr/bin/env bash
# Stage C, C4 documentation commit, round 3: simulation of RUNBOOK commands with HOME, the partition and the tmux socket
# directory in a scratch directory. Covered: the 3.0 variable file (heredoc text taken from the RUNBOOK, placeholder
# replaced), the 3.1 REPO line, the 3.2a if/else block taken from the RUNBOOK (both branches; the uv branch forced by
# renaming python3.13 in the version test), a fresh shell after source, the long-command send-keys line of section 1
# taken from the RUNBOOK (<名称> replaced) with a script that contains single quotes, and the GPU-seconds command of 3.7
# item 5 taken from the RUNBOOK on two synthetic gpu_clock.json files. Not covered: the pip install of the lock, the
# downloads, run_pilot.py. Usage: c4_runbook_sim_r3.sh SCRATCH RUNBOOK(absolute) REPO PYTHON_WITH_TORCH
set -u
mkdir -p "$1/home" "$1/part" "$1/tmux"
export HOME="$1/home" TMUX_TMPDIR="$1/tmux"; P="$1/part"; RB="$2"; REPO_DIR="$3"; TORCH_PY="$4"
cd "$1"
echo "--- 3.0 variable file (heredoc from the RUNBOOK, placeholder replaced):"
heredoc=$(awk '/^cat > ~\/metrix-vars.sh <<.EOF.$/{f=1} f{print} /^EOF$/{if(f) exit}' "$RB")
echo "$heredoc"
eval "${heredoc//<该分区上的目录>/$P}"
source ~/metrix-vars.sh; mkdir -p "$WORK/command_output"; echo "E=$E"
echo "--- 3.1 REPO line (from the RUNBOOK):"
line31=$(grep -m1 '^echo "export REPO=$(pwd)" >> ~/metrix-vars.sh$' "$RB"); echo "$line31"
(cd "$REPO_DIR" && eval "$line31")
block=$(awk '/^if \[ "\$\(python3.13 --version/{f=1} f{print} /^fi$/{if(f) exit}' "$RB")
echo "--- 3.2a block from the RUNBOOK:"; echo "$block"
for branch in host uv; do
  cp ~/metrix-vars.sh ~/vars.base
  if [ $branch = uv ]; then b=${block//python3.13 --version/python3.13-absent --version}; else b=$block; fi
  echo "=== branch $branch"; eval "$b"
  source ~/metrix-vars.sh
  { echo "PY313=$PY313"; "$PY313" -c 'import platform, sys; print(platform.python_implementation(), platform.python_version()); print(sys.version)'; } 2>&1 | tee -a "$E"
  "$PY313" -m venv ~/metrix-venv-$branch && echo "venv ok"
  [ $branch = host ] && cp ~/metrix-vars.sh ~/vars.host
  cp ~/vars.base ~/metrix-vars.sh
done
cp ~/vars.host ~/metrix-vars.sh
echo "export PY=$TORCH_PY" >> ~/metrix-vars.sh      # stands for ~/metrix-venv/bin/python (torch needed below)
echo "--- ~/metrix-vars.sh:"; cat ~/metrix-vars.sh
echo "--- a fresh shell after source:"
env -i HOME="$HOME" PATH="/usr/bin:/bin:/usr/local/bin" bash -c 'source ~/metrix-vars.sh && cd "$REPO" && echo "WORK=$WORK INPUTS=$INPUTS E=$E REPO=$REPO PY313=$PY313 PY=$PY" && pwd && "$PY313" --version'
echo "--- long command (section 1) with a script containing single quotes:"
cat > "$WORK/command_output/s_test.sh" <<'EOF'
set -o pipefail; source ~/metrix-vars.sh && cd "$REPO" || exit 1
"$PY313" -c 'import sys; print("quoted ok", sys.version_info[:3], sys.argv[1:])' 'a b' 2>&1 | tee -a "$WORK/command_output/s_test.txt"
python3 -c 'import sys; sys.exit(3)' | tee -a "$WORK/command_output/s_test.txt"
EOF
send=$(grep -m1 -o 'source ~/metrix-vars.sh && tmux new-window[^`]*' "$RB"); send=${send//<名称>/s_test}
echo "$send"
tmux new-session -d -s metrix -c "$REPO_DIR"
env -i HOME="$HOME" TMUX_TMPDIR="$TMUX_TMPDIR" PATH="/usr/bin:/bin:/usr/local/bin" bash -c "$send"
for i in $(seq 1 60); do [ -f "$WORK/command_output/s_test.end" ] && break; sleep 1; done
echo "s_test.txt:"; cat "$WORK/command_output/s_test.txt"; echo "s_test.end:"; cat "$WORK/command_output/s_test.end"
echo "capture-pane (last lines):"; tmux capture-pane -p -t metrix:s_test | grep -v '^$' | tail -4
tmux kill-server
echo "--- GPU seconds command (3.7 item 5) from the RUNBOOK:"
gpu=$(grep -m1 -o 'source ~/metrix-vars.sh && cd "$REPO" && PYTHONPATH=metrix/e1-pilot/src "$PY" -c "import sys; from metrix_e1.compute import GpuClock[^`]*' "$RB"); echo "$gpu"
echo '{"segments": [[1000.0, 1010.5], [2000.0, 2004.5]], "open": null}' > "$WORK/gpu_clock.json"; echo "closed only (expected 15.0 None):"
env -i HOME="$HOME" PATH="/usr/bin:/bin:/usr/local/bin" bash -c "$gpu"
python3 -c 'import json, time; json.dump({"segments": [[1000.0, 1010.5]], "open": time.time() - 100}, open("'"$WORK"'/gpu_clock.json", "w"))'; echo "with an open segment started 100 s ago (expected about 110.5 and a timestamp):"
env -i HOME="$HOME" PATH="/usr/bin:/bin:/usr/local/bin" bash -c "$gpu"
