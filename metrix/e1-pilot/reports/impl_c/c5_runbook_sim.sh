#!/bin/bash
# C5 (tasks/IMPL_C5_RULING.md item 2): run the RUNBOOK_A100.md commands changed by the C5 documentation commit, taken
# verbatim from the RUNBOOK file, in a scratch HOME and a scratch "partition" on the CPU container (no GPU, no model
# weights; nothing under <work> is committed). Covered: the 3.0 variable file (placeholder replaced by the scratch
# partition) and the 3.0 env.txt line; the 3.1 REPO line and identity line; the long commands s3_2a, s3_2 (real
# dependency install from requirements.lock into $VENV), s3_4_data and s3_4_config, each written to <窗口名>.sh with the
# section-1 first line and sent with the section-1 send-keys line in a fresh `env -i` shell; the checks after s3_2a and
# s3_2; the 3.7 GPU-seconds command on two hand-made gpu_clock.json files; git check-ignore on the section-5 file names.
# Not covered: 3.3 (needs CUDA), s3_4_model (weights only on the A100 host), formal / test-generate / test-evaluate,
# the uv branch of 3.2a (the host here has CPython 3.13.18 with ensurepip; the uv branch ran in c4_08).
# usage: bash c5_runbook_sim.sh <scratch dir (new)> <absolute path to RUNBOOK_A100.md> <repo root>
set -u
S="$1"; RB="$2"; ROOT="$3"
unset TMUX                                    # isolation: never touch a real tmux server (DEFERRED_MINORS 1.42 CP6)
export TMUX_TMPDIR="$S/tmux"
mkdir -p "$S/tmux" "$S/home" "$S/part"
export HOME="$S/home"
CLEAN=(env -i "HOME=$HOME" "PATH=$PATH" "TMUX_TMPDIR=$TMUX_TMPDIR")
echo "# C5 RUNBOOK simulation, start $(date -u)"
echo "scratch $S; RUNBOOK sha256 $(sha256sum "$RB" | cut -d' ' -f1); repo HEAD $(git -C "$ROOT" rev-parse HEAD)"
echo "host $(hostname); python3.13 $(python3.13 --version 2>&1) at $(command -v python3.13)"

line_after() { awk -v m="$1" 'f{print; exit} $0==m{f=1}' "$RB"; }                 # the line after an exact line
range() { awk -v a="$1" -v b="$2" 'index($0,a)==1{f=1} f{print} f&&index($0,b)==1{exit}' "$RB"; }

echo; echo "== 3.0 (variable file, env.txt), placeholder <该分区上的目录> -> $S/part"
P30=$(range "cat > ~/metrix-vars.sh <<'EOF'" "{ date -u; nvidia-smi;" | sed "s#<该分区上的目录>#$S/part#g")
printf '%s\n' "$P30" | sed 's/^/  | /'
"${CLEAN[@]}" bash -c "$P30" > "$S/p30.out" 2>&1; echo "  exit=$?"; sed 's/^/  > /' "$S/p30.out"
# The tmux server is started from this shell (not env -i) so that its windows get this container's HTTPS proxy and CA
# settings for pip and Hugging Face (the A100 host has none); the send lines themselves run in env -i shells.
tmux new -d -s metrix; echo "  tmux session (detached; the RUNBOOK's 'tmux new -s metrix' is interactive): $(tmux ls 2>&1)"

echo; echo "== 3.1 (REPO line and identity line, run in the repo root $ROOT; no clone here)"
P31=$(grep -F 'echo "export REPO=$(pwd)" >> ~/metrix-vars.sh' "$RB"; echo 'source ~/metrix-vars.sh'; grep -F '{ date -u; git rev-parse HEAD;' "$RB")
printf '%s\n' "$P31" | sed 's/^/  | /'
(cd "$ROOT" && "${CLEAN[@]}" bash -c "$P31" > "$S/p31.out" 2>&1); echo "  exit=$?"; sed 's/^/  > /' "$S/p31.out"
echo "  ~/metrix-vars.sh now:"; sed 's/^/  : /' "$HOME/metrix-vars.sh"

FIRST=$(grep -o 'set -o pipefail; source ~/metrix-vars.sh && cd "$REPO" || exit 1' "$RB" | head -1)
SEND=$(grep -o 'source ~/metrix-vars.sh && tmux new-window[^`]*Enter' "$RB" | head -1)
echo; echo "== section 1: script first line and send line (from the RUNBOOK)"; echo "  | $FIRST"; echo "  | $SEND"
W="$S/part/metrix-work/command_output"

run_long() {   # name, body: write <name>.sh, send it as the RUNBOOK says, wait for <name>.end
  local name="$1" body="$2" i
  printf '%s\n%s\n' "$FIRST" "$body" > "$W/$name.sh"
  echo; echo "== long command $name: $W/$name.sh"; sed 's/^/  | /' "$W/$name.sh"
  "${CLEAN[@]}" bash -c "${SEND//<窗口名>/$name}"; echo "  send exit=$?  $(date -u +%T)"
  for i in $(seq 1 720); do [ -f "$W/$name.end" ] && break; sleep 5; done
  echo "  $name.end ($(date -u +%T)): $(cat "$W/$name.end" 2>&1)"
}

run_long s3_2a "$(range 'if [ "$(python3.13 --version 2>&1)" = "Python 3.13.18" ]' '{ date -u; echo "PY313=$PY313";')"
echo "  check after s3_2a: the line after the last PY313= line of env.txt:"
awk '/^PY313=/{n=NR} {a[NR]=$0} END{print "  > " a[n]; print "  > " a[n+1]}' "$W/env.txt"

VENV="$S/part/metrix-venv"
( while [ ! -f "$W/s3_2.end" ]; do du -sk "$VENV.tmp" 2>/dev/null; sleep 2; done ) > "$S/venv_tmp_du.txt" &
run_long s3_2 "$(range '"$PY313" -m venv "$VENV"' 'mkdir -p "$VENV.tmp" && {')"
wait
echo "  check after s3_2: last line of env.txt: $(tail -n 1 "$W/env.txt")"
echo "  \$VENV.tmp during the install (du -sk samples every 2 s): $(wc -l < "$S/venv_tmp_du.txt") samples, max $(sort -n "$S/venv_tmp_du.txt" | tail -n 1 | cut -f1) KiB; now: $(du -sk "$VENV.tmp" | cut -f1) KiB"
echo "  pip cache under HOME: $(ls -a "$HOME/.cache" 2>&1 | tr '\n' ' ')"
echo "  venv size: $(du -sh "$VENV" | cut -f1); PY line in ~/metrix-vars.sh: $(grep '^export PY=' "$HOME/metrix-vars.sh")"

run_long s3_4_data "$(line_after '# 长命令 s3_4_data')"
run_long s3_4_config "$(line_after '# 长命令 s3_4_config')"

echo; echo "== 3.7 GPU-seconds command (from the RUNBOOK), on two hand-made $S/part/metrix-work/gpu_clock.json"
GPU=$(grep -o 'source ~/metrix-vars.sh && cd "$REPO" && PYTHONPATH=metrix/e1-pilot/src "$PY" -c "import json[^`]*gpu_clock.json"' "$RB")
echo "  | $GPU"
G="$S/part/metrix-work/gpu_clock.json"
printf '{"segments": [[1000.0, 1010.0], [2000.0, 2005.5]], "open": null}\n' > "$G"
echo "  (a) closed segments only (10 + 5.5 s), file: $(cat "$G")"
"${CLEAN[@]}" bash -c "$GPU" 2>&1 | sed 's/^/  > /'
OPEN=$(python3 -c 'import time; print(round(time.time() - 100.0, 3))')
printf '{"segments": [[1000.0, 1010.0]], "open": %s}\n' "$OPEN" > "$G"
echo "  (b) one closed segment (10 s) and one open since now-100 s, file: $(cat "$G")"
"${CLEAN[@]}" bash -c "$GPU" 2>&1 | sed 's/^/  > /'
echo "  expected for (b): 10 + (t - open), with t the third value printed"

echo; echo "== section 5: git check-ignore -v on the copied file names (no output and exit 1 = none ignored)"
git -C "$ROOT" check-ignore -v metrix/e1-pilot/results/command_output/env.txt metrix/e1-pilot/results/command_output/formal_20261128T000000Z.txt metrix/e1-pilot/results/command_output/formal.sh.txt metrix/e1-pilot/results/command_output/formal.end.txt
echo "  check-ignore exit=$?"

echo; echo "== files under $W"; ls -l "$W" | sed 's/^/  /'
for f in env.txt fetch.txt; do echo; echo "== $W/$f"; sed 's/^/  | /' "$W/$f"; done
for f in "$W"/*.end; do echo "== $(basename "$f"): $(cat "$f")"; done
tmux kill-server                               # the scratch server only (TMUX unset, TMUX_TMPDIR in the scratch dir)
echo; echo "# end $(date -u)"
