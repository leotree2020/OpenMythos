#!/usr/bin/env bash
# PILOT_REPORT_ORDER item 3: logged run of the Data Auditor's pilot_final_* scripts (Data Auditor's own wrapper).
# Writes the complete stdout + stderr, the command lines and the exit codes to
#   metrix/e1-pilot/audit/stdout/pilot_final_facts_order.txt   (fact order of facts.jsonl, B10)
#   metrix/e1-pilot/audit/stdout/pilot_final_recompute.txt     (recomputation and comparison)
# No git command, no Executor code, no TEST file, no model weights. The only network access is the download of the
# pinned tokenizer.json (no weights) into <scratch_dir>.
# usage: bash pilot_final_run_logged.sh <repo_root> <scratch_dir> <python with the tokenizers package>
set -u
REPO="$1"; SCRATCH="$2"; VPY="$3"
AUD="$REPO/metrix/e1-pilot/audit"
OUT="$AUD/stdout"
mkdir -p "$OUT"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
TOKDIR="$SCRATCH/pilot_final_tok_$STAMP"
URL="https://huggingface.co/Qwen/Qwen3-1.7B/resolve/70d244cc86ccca08cf5af4e1e306ecf908b1ad5e/tokenizer.json"

{
  echo "# Data Auditor run (PILOT_REPORT_ORDER item 3, part 1: fact order). host $(hostname), Claude Code cloud container, CPU only (no GPU, no torch, no transformers, no model weights); $(date -u '+%Y-%m-%d %H:%M:%S UTC'); cwd $(pwd)"
  echo "# wrapper: bash $0 $*"
  echo "# stdout and stderr merged, complete, unedited"
  echo "\$ mkdir -p $TOKDIR && curl -sS -L -o $TOKDIR/tokenizer.json $URL"
  mkdir -p "$TOKDIR" && curl -sS -L -o "$TOKDIR/tokenizer.json" "$URL" 2>&1
  echo "exit=$?"
  echo "\$ ls -la $TOKDIR"
  ls -la "$TOKDIR" 2>&1
  echo "\$ sha256sum $TOKDIR/tokenizer.json"
  sha256sum "$TOKDIR/tokenizer.json" 2>&1
  echo "\$ $VPY -I -c 'import sys, tokenizers; print(sys.version); print(tokenizers.__version__)'"
  "$VPY" -I -c 'import sys, tokenizers; print(sys.version); print(tokenizers.__version__)' 2>&1
  echo "\$ $VPY -I -c 'import importlib.util as u; print({m: u.find_spec(m) is not None for m in (\"torch\", \"transformers\")})'"
  "$VPY" -I -c 'import importlib.util as u; print({m: u.find_spec(m) is not None for m in ("torch", "transformers")})' 2>&1
  echo "\$ $VPY -I -B $AUD/pilot_final_facts_order.py $REPO $TOKDIR/tokenizer.json $AUD/pilot_final_fact_order.json"
  "$VPY" -I -B "$AUD/pilot_final_facts_order.py" "$REPO" "$TOKDIR/tokenizer.json" "$AUD/pilot_final_fact_order.json" 2>&1
  echo "exit=$?"
} > "$OUT/pilot_final_facts_order.txt" 2>&1

{
  echo "# Data Auditor run (PILOT_REPORT_ORDER item 3, part 2: recomputation). host $(hostname), Claude Code cloud container, CPU only (no GPU, no model, no tokenizer, no network); $(date -u '+%Y-%m-%d %H:%M:%S UTC'); cwd $(pwd)"
  echo "# wrapper: bash $0 $*"
  echo "# stdout and stderr merged, complete, unedited"
  echo "\$ command -v python3; python3 -I -c 'import sys, numpy; print(sys.version); print(numpy.__version__)'"
  command -v python3 2>&1
  python3 -I -c 'import sys, numpy; print(sys.version); print(numpy.__version__)' 2>&1
  echo "\$ python3 -I -B $AUD/pilot_final_recompute.py $REPO $AUD/pilot_final_fact_order.json $AUD/pilot_final_recompute.json"
  python3 -I -B "$AUD/pilot_final_recompute.py" "$REPO" "$AUD/pilot_final_fact_order.json" "$AUD/pilot_final_recompute.json" 2>&1
  echo "exit=$?"
} > "$OUT/pilot_final_recompute.txt" 2>&1

echo "facts order : $(tail -2 "$OUT/pilot_final_facts_order.txt" | tr '\n' ' ')"
echo "recompute   : $(tail -2 "$OUT/pilot_final_recompute.txt" | tr '\n' ' ')"
