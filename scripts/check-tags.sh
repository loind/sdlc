#!/usr/bin/env bash
# Cổng tag bất biến, không gắn tay (03-gitflow-va-release.md, mục "Tag").
# Tag chỉ có hai dạng: MASTER-<n> và TEST-<n>, do job CI gắn SAU khi gate xanh. Không dời tag, không gắn tay.
# Script bắt được từ git: (1) tag bắt đầu bằng master hoặc test (không phân biệt hoa thường) mà sai mẫu,
# (2) tag chỉ có ở local (gắn tay, chưa qua CI),
# (3) tag ở local trỏ khác remote (đã bị dời). KHÔNG phân biệt được tag trên remote do CI hay người đẩy lên:
# việc chỉ cho CI tạo MASTER-* và TEST-* phải do quyền trên remote (protected tags) đảm bảo.
# Trước khi chạy, lấy tag bằng `git fetch --tags` (KHÔNG --force): tag đã bị dời trên remote sẽ làm fetch báo lỗi.
#
# Dùng:  scripts/check-tags.sh [<remote>]   mặc định remote: origin
#        scripts/check-tags.sh --self-test  chứng minh cổng không rỗng (remote và clone tạm)
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

run_check() {
  local remote="${1:-origin}" listed names name sha rsha bad=0
  listed="$(git ls-remote --tags "$remote" 2>&1)" || {
    echo "check-tags: không đọc được remote '$remote': $listed" >&2
    return 2
  }
  names="$( { printf '%s\n' "$listed" | awk '{sub("refs/tags/", "", $2); sub(/\^\{\}$/, "", $2); print $2}'
              git for-each-ref --format='%(refname:strip=2)' refs/tags; } | sort -u )" || return 2

  # shortcut: vài lần fork mỗi tag (khoảng 25 ms/tag trên macOS, 2000 tag mất cỡ 50 giây); repo có nhiều nghìn tag thì gộp vào một lệnh awk
  while IFS= read -r name; do
    [ -n "$name" ] || continue
    case "$name" in
      MASTER-[0-9]*|TEST-[0-9]*) : ;;
      [Mm][Aa][Ss][Tt][Ee][Rr]*|[Tt][Ee][Ss][Tt]*)
        echo "TAG $name: sai mẫu (chỉ MASTER-<n> hoặc TEST-<n>), có thể gắn tay" >&2; bad=1; continue ;;
      *) continue ;;
    esac
    if ! printf '%s' "${name#*-}" | grep -qE '^[0-9]+$'; then
      echo "TAG $name: sai mẫu (<n> phải là số), có thể gắn tay" >&2; bad=1; continue
    fi
    sha="$(git rev-parse --verify --quiet "refs/tags/$name")" || continue   # chỉ có ở remote: local chưa fetch
    rsha="$(printf '%s\n' "$listed" | awk -v r="refs/tags/$name" '$2 == r {print $1}')"
    if [ -z "$rsha" ]; then
      echo "TAG $name: chỉ có ở local, chưa có trên '$remote' (gắn tay, chưa qua CI)" >&2; bad=1
    elif [ "$rsha" != "$sha" ]; then
      echo "TAG $name: local trỏ ${sha:0:12}, '$remote' trỏ ${rsha:0:12} (tag đã bị dời)" >&2; bad=1
    fi
  done <<<"$names"

  [ "$bad" -eq 0 ] || return 1
  echo "check-tags: OK"
}

# --- self-test: mỗi ca dựng remote bare và clone riêng ---
g() { git -C "$work" -c user.name=t -c user.email=t@t "$@"; }

fresh() {
  rm -rf "$tmp/remote.git" "$tmp/work"
  git init -q --bare "$tmp/remote.git" && git init -q "$tmp/work" || return 2
  work="$tmp/work"
  g remote add origin "$tmp/remote.git" && g commit -q --allow-empty -m one && g commit -q --allow-empty -m two || return 2
  mkdir -p "$work/scripts" && cp "${BASH_SOURCE[0]}" "$work/scripts/check-tags.sh"
}

expect() {  # expect <exit mong đợi> <mô tả> <chuỗi phải có trong output>
  local want="$1" what="$2" must="$3" out rc
  out="$(bash "$work/scripts/check-tags.sh" 2>&1)"; rc=$?
  [ "$rc" -eq "$want" ] && grep -qF -- "$must" <<<"$out" \
    || { echo "self-test: $what: cần exit $want chứa '$must', nhận exit $rc: $out" >&2; return 1; }
}

self_test_body() {
  fresh || return 2
  expect 0 "chưa có tag" "OK" || return 1
  g tag MASTER-7 HEAD~1 && g tag -a TEST-12 -m t && g tag v1.0 && g push -q origin --tags || return 2
  expect 0 "tag đúng mẫu đã có trên remote (nhẹ + annotated), v1.0 không liên quan" "OK" || return 1

  g tag TEST-9
  expect 1 "tag chỉ có ở local phải đỏ" "TAG TEST-9: chỉ có ở local" || return 1
  g tag -d TEST-9 >/dev/null

  g push -q --force origin HEAD:refs/tags/MASTER-7 || return 2
  expect 1 "tag bị dời trên remote phải đỏ" "TAG MASTER-7: local trỏ" || return 1

  fresh || return 2
  for bad in MASTER-7-hotfix master-7 TEST-x test-1 MASTER-; do
    g tag "$bad" && g push -q origin "refs/tags/$bad" || return 2
    expect 1 "tag sai mẫu '$bad' phải đỏ" "TAG $bad: sai mẫu" || return 1
    g push -q --delete origin "refs/tags/$bad" && g tag -d "$bad" >/dev/null || return 2
  done

  g remote set-url origin "$tmp/khong-co-remote.git"
  expect 2 "remote không đọc được phải exit 2 (không phải OK giả)" "không đọc được remote" || return 1
  echo "check-tags --self-test: OK"
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
  -*) echo "dùng: $0 [<remote>] | --self-test" >&2; exit 2 ;;
  *) run_check "${1:-origin}"; exit $? ;;
esac
