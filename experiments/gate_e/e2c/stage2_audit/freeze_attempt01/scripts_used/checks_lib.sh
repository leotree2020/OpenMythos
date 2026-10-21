# Shared helpers for the freeze preparation scripts (sourced, bash). A failed command is never read as "nothing found":
# every helper returns the command's own failure, and an expected "no match" is decided from the command's documented
# exit status, not from empty output.

# git_capture VAR git-args... : VAR := stdout of git; returns git's exit status; on failure the error goes to stderr.
git_capture() {
  local __var=$1 __err __out __rc
  shift
  __err=$(mktemp) || return 90
  __out=$(git "$@" 2>"$__err")
  __rc=$?
  if [ $__rc -ne 0 ]; then
    echo "    git $* failed (exit $__rc): $(head -c 300 "$__err" | tr '\n' ' ')" >&2
  fi
  rm -f "$__err"
  printf -v "$__var" '%s' "$__out"
  return $__rc
}

# count_lines TEXT : number of non-empty lines (0 for empty text; "echo '' | wc -l" would say 1).
count_lines() {
  if [ -z "$1" ]; then echo 0; else printf '%s\n' "$1" | grep -c .; fi
}

# sha_check_list LIST : LIST holds "sha256  path" lines; prints sha256sum -c output; returns sha256sum's exit status
# (non-zero on any mismatch or unreadable file). No pipe after sha256sum, so its status is not lost.
sha_check_list() {
  local out rc
  out=$(printf '%s\n' "$1" | sha256sum -c 2>&1)
  rc=$?
  printf '%s\n' "$out"
  return $rc
}

# sha_of VAR FILE : VAR := sha256 of FILE; returns sha256sum's exit status.
sha_of() {
  local __var=$1 __out __rc
  __out=$(sha256sum "$2" 2>&1)
  __rc=$?
  [ $__rc -eq 0 ] || echo "    sha256sum $2 failed (exit $__rc): $__out" >&2
  printf -v "$__var" '%s' "${__out%% *}"
  return $__rc
}

# none_matching VAR PATTERN TEXT : grep -E PATTERN over TEXT; VAR := the matches.
# returns 0 = no match (grep 1), 1 = matches found (grep 0), 2 = grep error (grep >1).
none_matching() {
  local __var=$1 __out __rc
  __out=$(printf '%s\n' "$3" | grep -E "$2")
  __rc=$?
  printf -v "$__var" '%s' "$__out"
  case $__rc in 1) return 0 ;; 0) return 1 ;; *) return 2 ;; esac
}

# no_process VAR PATTERN : pgrep -af PATTERN; VAR := matches. returns 0 = none (pgrep 1), 1 = found (pgrep 0), 2 = error.
no_process() {
  local __var=$1 __out __rc
  __out=$(pgrep -af "$2")
  __rc=$?
  printf -v "$__var" '%s' "$__out"
  case $__rc in 1) return 0 ;; 0) return 1 ;; *) return 2 ;; esac
}
