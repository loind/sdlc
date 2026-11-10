#!/usr/bin/env bash
# Kiểm tài liệu sống không còn nhắc tên hay cách làm đã bỏ.
# Khi bỏ một tên hay một cách làm: THÊM mẫu vào RETIRED (kèm lý do ngắn), rồi sửa mọi chỗ còn sót.
# Hồ sơ lịch sử có ngày (ADR, design, board, learning-notes, test chứng minh cách cũ) không kiểm.
# Lưu ý: git grep KHÔNG thấy file chưa commit (file đã `git add` thì thấy). Thử trên bản đã commit.
#
# Dùng:  scripts/check-docs.sh              kiểm repo hiện tại
#        scripts/check-docs.sh --self-test  chứng minh cổng không rỗng (chạy trong repo tạm)
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

# Mẫu mồi: --self-test cắm chuỗi này vào một tài liệu sống và cổng PHẢI đỏ. Không nhắc nó ở file khác.
CANARY='CANARY-DA-BO-DOC-KIEM'
RETIRED=(
  "$CANARY"                          # mồi cho --self-test
  'await rlm\('                      # kernel báo "rlm is not callable", dùng rlm.spawn (ADR-0001)
  'rlm\.run\('                       # đã đổi tên thành rlm.spawn (ADR-0001)
  'rlm\.delete_subagent\('           # child giữ tới cuối run, không xoá sau phase (ADR-0001)
  'FMT_OK|LINT_OK|TEST_OK'           # marker gate cũ; nay run-gate.sh in GATE_OK / GATE_RED
)
EXCLUDE=(
  ':!docs/adr'                       # quyết định kèm lý do lịch sử
  ':!docs/design'                    # gói thiết kế và verdict có ngày
  ':!docs/learning-notes'            # ghi chú học theo ngày, nhắc cách cũ để giải thích
  ':!.prime'                         # board orchestrator
  ':!tests'                          # test chứng minh cách cũ đã bỏ
  ':!scripts/check-docs.sh'
  ':!mau/check-docs-mau.sh'          # bản mẫu của chính script này, chứa mẫu mồi
)

run_check() {
  if [ "${#RETIRED[@]}" -eq 0 ]; then
    echo "check-docs: RETIRED rỗng, cổng vô nghĩa" >&2
    return 2
  fi
  local pat hits rc
  pat="$(IFS='|'; echo "${RETIRED[*]}")"
  hits="$(git grep -nE "$pat" -- . "${EXCLUDE[@]}")"
  rc=$?
  # git grep: 0 = có khớp, 1 = không khớp, từ 2 trở lên = lỗi (regex hỏng, ngoài repo). Lỗi không được tính là sạch.
  if [ "$rc" -gt 1 ]; then
    echo "check-docs: git grep lỗi (exit $rc)" >&2
    return 2
  fi
  if [ -n "$hits" ]; then
    echo "check-docs: còn thuật ngữ đã bỏ trong tài liệu sống:" >&2
    echo "$hits" >&2
    return 1
  fi
  echo "check-docs: OK"
}

self_test_body() {
  local out rc
  mkdir -p "$tmp/scripts" "$tmp/docs/adr"
  cp "${BASH_SOURCE[0]}" "$tmp/scripts/check-docs.sh"
  printf 'dòng sạch\n' > "$tmp/README.md"
  printf '# ADR\n%s\n' "$CANARY" > "$tmp/docs/adr/0001-x.md"   # miễn quét: mồi ở đây không được làm đỏ
  git -C "$tmp" init -q && git -C "$tmp" add -A || return 2

  out="$(bash "$tmp/scripts/check-docs.sh" 2>&1)"; rc=$?
  [ "$rc" -eq 0 ] || { echo "self-test: bản sạch phải xanh, nhận exit $rc: $out" >&2; return 1; }

  printf 'dòng sạch\n%s\n' "$CANARY" > "$tmp/README.md"
  git -C "$tmp" add -A
  out="$(bash "$tmp/scripts/check-docs.sh" 2>&1)"; rc=$?
  [ "$rc" -eq 1 ] || { echo "self-test: mồi trong tài liệu sống phải làm cổng đỏ (exit 1), nhận exit $rc: $out" >&2; return 1; }
  grep -q '^README.md:2:' <<<"$out" || { echo "self-test: cổng đỏ nhưng thiếu file:dòng 'README.md:2:': $out" >&2; return 1; }

  printf 'dòng sạch\n' > "$tmp/README.md"
  git -C "$tmp" add -A
  out="$(bash "$tmp/scripts/check-docs.sh" 2>&1)"; rc=$?
  [ "$rc" -eq 0 ] || { echo "self-test: bỏ mồi rồi cổng phải xanh lại, nhận exit $rc: $out" >&2; return 1; }

  out="$(GIT_DIR="$tmp/khong-co-repo" bash "$tmp/scripts/check-docs.sh" 2>&1)"; rc=$?
  [ "$rc" -eq 2 ] || { echo "self-test: git grep lỗi phải cho exit 2 (không phải OK giả), nhận exit $rc: $out" >&2; return 1; }
  echo "check-docs --self-test: OK"
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
  "") run_check; exit $? ;;
  *) echo "dùng: $0 [--self-test]" >&2; exit 2 ;;
esac
