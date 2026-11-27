#!/usr/bin/env bash
# Runs the RUNBOOK 3.0-3.2 variable-file lines and the 3.2a block (both branches) with HOME and the partition in a scratch
# directory; the else branch is forced by replacing python3.13 with a name that does not exist. No pip install of the lock.
set -u
export HOME="$1/home"; P="$1/part"; RB="$2"
cd "$1"
# 3.0 (placeholder replaced by the scratch partition)
cat > ~/metrix-vars.sh <<EOF
export WORK=$P/metrix-work INPUTS=$P/metrix-inputs
export E="\$WORK/command_output/env.txt"
EOF
source ~/metrix-vars.sh; mkdir -p "$WORK/command_output"; echo "E=$E"
# 3.1 (the repository root stands for the clone)
cd "$3" && echo "export REPO=$(pwd)" >> ~/metrix-vars.sh; cd "$1"
# 3.2a exactly as in the RUNBOOK, branch 1 (host has 3.13.18), then branch 2 forced
block=$(awk '/^if \[ "\$\(python3.13 --version/{f=1} f{print} /^fi$/{if(f) exit}' "$RB")
echo "--- 3.2a block from the RUNBOOK:"; echo "$block"
for branch in host uv; do
  cp ~/metrix-vars.sh ~/vars.base
  if [ $branch = uv ]; then b=${block//python3.13 --version/python3.13-absent --version}; else b=$block; fi
  echo "=== branch $branch"; eval "$b"
  source ~/metrix-vars.sh
  { echo "PY313=$PY313"; "$PY313" -c 'import platform, sys; print(platform.python_implementation(), platform.python_version()); print(sys.version)'; } 2>&1 | tee -a "$E"
  "$PY313" -m venv ~/metrix-venv-$branch && echo "venv ok"
  cp ~/vars.base ~/metrix-vars.sh
done
echo 'export PY=~/metrix-venv-host/bin/python' >> ~/metrix-vars.sh
echo "--- a fresh shell (as a new tmux window or a new Claude Code call) after source:"
env -i HOME="$HOME" PATH="/usr/bin:/bin:/usr/local/bin" bash -c 'source ~/metrix-vars.sh && cd "$REPO" && echo "WORK=$WORK INPUTS=$INPUTS E=$E REPO=$REPO PY=$PY" && pwd && "$PY" --version'
echo "--- ~/metrix-vars.sh:"; cat ~/metrix-vars.sh
