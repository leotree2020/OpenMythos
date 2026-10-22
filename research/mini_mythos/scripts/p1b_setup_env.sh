#!/usr/bin/env bash
# Build the isolated P1-B environment: a Python 3.12 venv with the pinned
# requirements and an unmodified Parcae checkout at the pinned commit.
# Re-running is safe: an existing venv/checkout is reused and re-verified.
#
#   bash p1b_setup_env.sh [VENV_DIR] [PARCAE_DIR]
set -euo pipefail

PARCAE_SHA=69284c13746e849104f738d6d1a347b1f457df76
PARCAE_URL=https://github.com/sandyresearch/parcae
PYTHON=${PYTHON:-python3.12}
VENV_DIR=${1:-./venv_p1b}
PARCAE_DIR=${2:-./parcae}
HERE=$(cd "$(dirname "$0")" && pwd)

[ -x "$VENV_DIR/bin/python" ] || "$PYTHON" -m venv "$VENV_DIR"
"$VENV_DIR/bin/python" -m pip install --no-cache-dir -r "$HERE/requirements-p1b-parcae.txt"

if [ ! -d "$PARCAE_DIR/.git" ]; then
    git init -q "$PARCAE_DIR"
    git -C "$PARCAE_DIR" remote add origin "$PARCAE_URL"
fi
if [ "$(git -C "$PARCAE_DIR" rev-parse HEAD 2>/dev/null)" != "$PARCAE_SHA" ]; then
    git -C "$PARCAE_DIR" fetch -q --depth 1 origin "$PARCAE_SHA"
    git -C "$PARCAE_DIR" checkout -q --detach "$PARCAE_SHA"
fi

test "$(git -C "$PARCAE_DIR" rev-parse HEAD)" = "$PARCAE_SHA"
test -z "$(git -C "$PARCAE_DIR" status --porcelain --untracked-files=no)"
"$VENV_DIR/bin/python" -I -c 'import torch, numpy, einops; print("torch", torch.__version__, "numpy", numpy.__version__, "einops", einops.__version__)'
echo "venv:   $VENV_DIR"
echo "parcae: $PARCAE_DIR @ $PARCAE_SHA"
