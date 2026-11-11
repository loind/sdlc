#!/usr/bin/env bash
# P0.1 gate runner duy nhất cho engine và orchestrator.
# Usage: scripts/run-gate.sh "<cmd1>" "<cmd2>" ...
# Env: GATE_LOG (file log), TIMEOUT_SEC (giới hạn mỗi lệnh, default 600)
set -uo pipefail

LOG="${GATE_LOG:-/tmp/gate-$(date +%Y%m%d-%H%M%S).log}"
TIMEOUT_SEC="${TIMEOUT_SEC:-600}"
: > "$LOG"

# Không có lệnh nào, hay TIMEOUT_SEC không phải số dương, đều là gate rỗng: không được báo xanh.
if [ "$#" -eq 0 ]; then
  echo "[gate] REJECT: không có lệnh gate nào" | tee -a "$LOG" >&2
  exit 2
fi
if ! [[ "$TIMEOUT_SEC" =~ ^[1-9][0-9]*$ ]]; then
  echo "[gate] REJECT: TIMEOUT_SEC phải là số giây dương, nhận '$TIMEOUT_SEC'" | tee -a "$LOG" >&2
  exit 2
fi

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
  if [[ -z "${cmd//[[:space:]]/}" ]]; then
    echo "[gate $i] REJECT: lệnh gate rỗng" | tee -a "$LOG" >&2
    exit 2
  fi
  # Xuống dòng nối hai lệnh y như ';': exit code của lệnh đầu bị che.
  if [[ "$cmd" == *"|"* || "$cmd" == *"&"* || "$cmd" == *";"* || "$cmd" == *$'\n'* ]]; then
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
