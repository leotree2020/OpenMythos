#!/usr/bin/env bash
# B1-E0: build the isolated CPU environment and a hash lock. Run on the TARGET machine.
# It never reuses or removes an existing environment and never touches the historical D1/M2 environment.
#   resolve (no install) -> make_lock.py (hash lock + 14-day release-age review) -> install by hash
#   -> pip check -> pip freeze -> freeze/lock comparison
set -euo pipefail
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REFERENCE_PY=${B1_REFERENCE_PYTHON:-/workspaces/mythos-m2-cpu312/bin/python}
VENV=${B1_VENV:-/workspaces/mythos-base-v01-cpu312}
WORK=${B1_ENV_WORK:-/workspaces/mythos-evidence/base_v01/env/$(date -u +%Y%m%dT%H%M%SZ)}
LOCK_DATE=${B1_LOCK_DATE:-$(date -u +%F)}
blocked() { printf 'BLOCKED: %s\n' "$1" >&2; exit 2; }

[[ -x "$REFERENCE_PY" ]] || blocked "reference interpreter not found: $REFERENCE_PY (no replacement is substituted)"
BASE_PY=$("$REFERENCE_PY" -c 'import os,sys;print(os.path.realpath(sys.executable))')
VERSION=$("$BASE_PY" -c 'import platform;print(platform.python_version())')
[[ "$VERSION" == "3.12.3" ]] || blocked "base interpreter is Python $VERSION, not 3.12.3"
[[ ! -e "$VENV" ]] || blocked "environment directory already exists, not reusing or removing: $VENV"
mkdir -p "$(dirname "$WORK")"
mkdir "$WORK"   # fails if it already exists

"$BASE_PY" -m venv "$VENV"
PY="$VENV/bin/python"
"$PY" -m pip --version | tee "$WORK/pip_version.txt"
{ echo "base_python=$BASE_PY"; echo "venv=$VENV"; echo "lock_date=$LOCK_DATE"; uname -a; } > "$WORK/build_context.txt"

# 1. Resolve the full closure without installing anything.
"$PY" -m pip install --dry-run --ignore-installed --only-binary=:all: \
  --report "$WORK/pip_report.json" \
  --index-url https://pypi.org/simple --extra-index-url https://download.pytorch.org/whl/cpu \
  -c "$HERE/constraints.txt" -r "$HERE/requirements.direct.txt" 2>&1 | tee "$WORK/resolve.log"

# 2. Hash lock and release-age review (exit status 2 = violations; nothing is relaxed).
"$PY" "$HERE/make_lock.py" lock --report "$WORK/pip_report.json" --out "$WORK/requirements.lock" \
  --review "$WORK/lock_review.json" --lock-date "$LOCK_DATE" \
  || blocked "lock review reported violations: see $WORK/lock_review.json (add exact pins to constraints.txt and rerun in a NEW environment directory)"

# 3. Install strictly by hash. --no-deps is correct here only because the lock lists the whole closure.
"$PY" -m pip install --require-hashes --no-deps --only-binary=:all: -r "$WORK/requirements.lock" 2>&1 | tee "$WORK/install.log"
"$PY" -m pip check | tee "$WORK/pip_check.txt"
"$PY" -m pip freeze > "$WORK/pip_freeze.txt"
"$PY" "$HERE/make_lock.py" verify --lock "$WORK/requirements.lock" --freeze "$WORK/pip_freeze.txt" | tee "$WORK/lock_vs_freeze.json"
"$PY" -c 'import torch,numpy,einops,tokenizers;print(torch.__version__,numpy.__version__,einops.__version__,tokenizers.__version__)' | tee "$WORK/import_smoke.txt"

cat <<MSG
Environment ready: $VENV
Evidence: $WORK
Next: review $WORK/requirements.lock, copy it to research/mini_mythos/base_v01/requirements.lock,
commit it, then run the stages from that commit (env-check requires a clean tree).
MSG
