#!/usr/bin/env bash
# P0.1 gate runner duy nhất cho engine và orchestrator.
# Usage: scripts/run-gate.sh "<cmd1>" "<cmd2>" ...
# Env: GATE_LOG (file log), TIMEOUT_SEC (giới hạn mỗi lệnh, default 600)
set -uo pipefail

LOG="${GATE_LOG:-/tmp/gate-$(date +%Y%m%d-%H%M%S).log}"
TIMEOUT_SEC="${TIMEOUT_SEC:-600}"
: > "$LOG"

bounded() {
  local secs="$1"; shift
  if command -v timeout >/dev/null 2>&1; then
    timeout "$secs" bash -c "$*"
  else
    perl -e 'alarm shift; exec @ARGV' "$secs" bash -c "$*"
  fi
}

i=0
for cmd in "$@"; do
  i=$((i+1))
  if [[ "$cmd" == *"|"* || "$cmd" == *"&"* || "$cmd" == *";"* ]]; then
    echo "[gate $i] REJECT: gate phai la 1 lenh don, cam pipe/&&/;: $cmd" | tee -a "$LOG" >&2
    exit 2
  fi
  echo "[gate $i] RUN: $cmd" | tee -a "$LOG"
  bounded "$TIMEOUT_SEC" "$cmd" >>"$LOG" 2>&1
  code=$?
  echo "[gate $i] EXIT=$code: $cmd" | tee -a "$LOG"
  if [ "$code" -ne 0 ]; then
    echo "GATE_RED at [$i]: $cmd (log: $LOG)" >&2
    exit "$code"
  fi
  echo "GATE_OK [$i]"
done
echo "GATE_GREEN all $i (log: $LOG)"
