#!/usr/bin/env bash
# Cổng ghim phụ thuộc theo nhánh (03-gitflow-va-release.md, mục "Ghim phụ thuộc theo nhánh").
#   develop, release/*, hotfix/*, master : CHỈ MASTER-<n>, cấm TEST-<n>.
#   test, feature/*                      : TEST-<n> hoặc MASTER-<n>.
#   nhánh không xác định được            : áp luật chặt nhất, không pass ngầm.
# Pipeline của MR: truyền nhánh ĐÍCH (feature/* vào develop thì truyền develop), vì TEST-<n> không được lọt vào đó.
# Chạy ở stage đầu của CI, trước mọi bước nặng. git grep chỉ thấy file đã commit hoặc đã `git add`.
#
# Dùng:  scripts/check-pins.sh [--branch <tên>]   mặc định: $BRANCH_NAME, rồi nhánh hiện tại
#        scripts/check-pins.sh --self-test        chứng minh cổng không rỗng (chạy trong repo tạm)
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

# File ghim phụ thuộc cần quét (git pathspec, `*` khớp cả dấu `/`). Chỉnh theo repo của bạn.
PIN_FILES=('*Cargo.toml' '*Cargo.lock' '*package.json' '*package-lock.json' '*yarn.lock' '*pnpm-lock.yaml'
           '*pyproject.toml' '*poetry.lock' '*uv.lock' '*Pipfile' '*Pipfile.lock' '*requirements*.txt' '*go.mod'
           '*Dockerfile*')

run_check() {
  local branch="${1#origin/}" hits rc
  case "$branch" in
    test|feature/*) echo "check-pins: OK ('$branch' được ghim TEST-<n> hoặc MASTER-<n>)"; return 0 ;;
    develop|master|release/*|hotfix/*) ;;
    *) echo "check-pins: nhánh '${branch:-<không xác định>}' không thuộc mẫu gitflow, áp luật chặt nhất" >&2 ;;
  esac
  hits="$(git grep -nE '(^|[^A-Za-z0-9])TEST-[0-9]+' -- "${PIN_FILES[@]}")"
  rc=$?
  # git grep: 0 = có khớp, 1 = không khớp, từ 2 trở lên = lỗi. Lỗi không được tính là sạch.
  if [ "$rc" -gt 1 ]; then
    echo "check-pins: git grep lỗi (exit $rc)" >&2
    return 2
  fi
  if [ -n "$hits" ]; then
    echo "check-pins: TEST-<n> không được vào '${branch:-<không xác định>}'. Đổi sang MASTER-<n> tương ứng rồi ghi bằng chứng:" >&2
    echo "$hits" >&2
    return 1
  fi
  echo "check-pins: OK"
}

expect() {  # expect <exit mong đợi> <mô tả> <lệnh...>
  local want="$1" what="$2" out rc
  shift 2
  out="$("$@" 2>&1)"; rc=$?
  [ "$rc" -eq "$want" ] || { echo "self-test: $what: cần exit $want, nhận exit $rc: $out" >&2; return 1; }
}

self_test_body() {
  local b chk="$tmp/scripts/check-pins.sh"
  mkdir -p "$tmp/scripts" "$tmp/sub"
  cp "${BASH_SOURCE[0]}" "$chk"
  printf 'foo = { git = "x", tag = "TEST-12" }\n' > "$tmp/Cargo.toml"
  printf 'source = "git+x?tag=TEST-3"\nbar = "LATEST-9"\n' > "$tmp/sub/Cargo.lock"
  for f in uv.lock poetry.lock yarn.lock pnpm-lock.yaml Pipfile Dockerfile; do printf 'pin = "TEST-4"\n' > "$tmp/sub/$f"; done
  git -C "$tmp" init -q && git -C "$tmp" add -A || return 2

  for b in develop master release/2026.11.10 hotfix/12 revert/abc "" origin/develop; do
    expect 1 "TEST-<n> trên '$b' phải đỏ" bash "$chk" --branch "$b" || return 1
  done
  for b in test feature/12-x; do
    expect 0 "TEST-<n> trên '$b' được phép" bash "$chk" --branch "$b" || return 1
  done
  out="$(bash "$chk" --branch develop 2>&1)"
  grep -q '^Cargo.toml:1:' <<<"$out" && grep -q '^sub/Cargo.lock:1:' <<<"$out" \
    || { echo "self-test: thiếu file:dòng của cả hai file ghim: $out" >&2; return 1; }
  grep -q 'LATEST-9' <<<"$out" && { echo "self-test: LATEST-9 không phải TEST-<n>: $out" >&2; return 1; }
  for f in uv.lock poetry.lock yarn.lock pnpm-lock.yaml Pipfile Dockerfile; do
    grep -q "^sub/$f:1:" <<<"$out" || { echo "self-test: không quét $f: $out" >&2; return 1; }
  done

  printf 'foo = { git = "x", tag = "MASTER-7" }\n' > "$tmp/Cargo.toml"
  printf 'source = "git+x?tag=MASTER-7"\n' > "$tmp/sub/Cargo.lock"
  for f in uv.lock poetry.lock yarn.lock pnpm-lock.yaml Pipfile Dockerfile; do printf 'pin = "MASTER-7"\n' > "$tmp/sub/$f"; done
  git -C "$tmp" add -A
  expect 0 "chỉ MASTER-<n> trên develop phải xanh" bash "$chk" --branch develop || return 1
  expect 2 "git grep lỗi phải exit 2 (không phải OK giả)" env GIT_DIR="$tmp/khong-co-repo" bash "$chk" --branch develop || return 1
  echo "check-pins --self-test: OK"
}

self_test() {
  tmp="$(mktemp -d)" || return 2
  self_test_body
  local rc=$?
  rm -rf "$tmp"
  return "$rc"
}

case "${1:-}" in
  --self-test) self_test; exit $? ;;
  --branch) run_check "${2:-}"; exit $? ;;
  "") run_check "${BRANCH_NAME:-$(git branch --show-current 2>/dev/null)}"; exit $? ;;
  *) echo "dùng: $0 [--branch <tên>] | --self-test" >&2; exit 2 ;;
esac
