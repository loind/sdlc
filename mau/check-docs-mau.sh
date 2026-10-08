#!/usr/bin/env bash
# Kiểm tài liệu sống không còn nhắc tên hay cách làm đã bỏ.
# Khi bỏ một tên hay một cách làm: THÊM mẫu vào RETIRED (kèm lý do ngắn), rồi sửa mọi chỗ còn sót.
# Hồ sơ lịch sử có ngày (ADR, design, board, test chứng minh cách cũ) không kiểm.
# Lưu ý: git grep KHÔNG thấy file chưa commit. Thử trên bản đã commit.
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

RETIRED=(
  'ten-cu-vi-du-1'                   # thư mục cũ, nay là ten-moi/
  'cach-lam-cu-vi-du'                # đã bỏ ở ticket #NN
)
EXCLUDE=(
  ':!docs/adr'                       # quyết định kèm lý do lịch sử
  ':!docs/design'                    # gói thiết kế và verdict có ngày
  ':!.prime'                         # board orchestrator
  ':!tests'                          # test chứng minh cách cũ đã bỏ
  ':!scripts/check-docs.sh'
)
pat="$(IFS='|'; echo "${RETIRED[*]}")"
hits="$(git grep -nE "$pat" -- . "${EXCLUDE[@]}")"
if [ -n "$hits" ]; then
  echo "check-docs: còn thuật ngữ đã bỏ trong tài liệu sống:" >&2
  echo "$hits" >&2
  exit 1
fi
echo "check-docs: OK"
