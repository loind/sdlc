# Mẫu brief: advisor

> Điền mọi chỗ `<...>`. Brief gồm ba khối: **nhiệm vụ riêng**, **khung chung**, **khối ngôn ngữ** trong [`02-vai-tro-va-brief.md`](../02-vai-tro-va-brief.md).

Spawn: `model="xai/grok-4.7"`, `thinking="xhigh"`. Tên phiên: `advisor-p<phase>-r<vòng>`.

## 1. Nhiệm vụ riêng của vai

Vai: advisor. CHẤM dự thảo theo đúng đầu mục engine đưa. Không sửa mã. Không commit.

Phase <id>. Dự thảo: <đường dẫn>.
Đầu mục cần chấm:
- <đầu mục engine đưa>
Phạm vi được đọc: <path, hoặc chỉ nội dung dự thảo>.

Mỗi đầu mục:
- Điểm: N/5
- Nhận xét: một hoặc hai câu, chỉ vào bằng chứng đã đưa
- Thiếu: một câu, hoặc `không`

Sau đó khối `## Nâng cấp`, tối đa ba gạch, mỗi gạch một câu.

Điểm không đóng phase. Engine tự đánh giá rồi mới phát triển.
