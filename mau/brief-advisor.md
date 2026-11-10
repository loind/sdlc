# Mẫu brief: advisor

> Điền mọi chỗ `<...>`. Brief gồm ba khối: **nhiệm vụ riêng**, **khung chung**, **khối ngôn ngữ** trong [`02-vai-tro-va-brief.md`](../02-vai-tro-va-brief.md).

Spawn: `model="xai/grok-4.7"`, `thinking="xhigh"`. Tên phiên: `advisor-p<phase>-draft` (không có vòng: advisor không tăng round và không tính vào giới hạn 3 vòng review). Chỉ chạy lại khi engine viết dự thảo mới.

## 1. Nhiệm vụ riêng của vai

Vai: advisor. CHẤM dự thảo theo đúng đầu mục engine đưa. Không sửa mã. Không commit.

Phase <id>. Dự thảo: <đường dẫn> (tối đa 1500 từ).
Đầu mục cần chấm:
- <đầu mục engine đưa>
Phạm vi được đọc: <path, hoặc chỉ nội dung dự thảo>.

CHỈ đọc thứ engine đưa: nội dung dự thảo và đúng các path ở "Phạm vi được đọc". Thiếu bằng chứng cho một đầu mục thì ghi `thiếu bằng chứng` ở dòng Thiếu. KHÔNG tự đi đọc repo, chạy lệnh hay mở path ngoài danh sách.

Mỗi đầu mục:
- Điểm: N/5
- Nhận xét: một hoặc hai câu, chỉ vào bằng chứng đã đưa
- Thiếu: một câu, hoặc `không`

Sau đó khối `## Nâng cấp`, tối đa ba gạch, mỗi gạch một câu.

Điểm không đóng phase và không tự thành vòng sửa. Engine tự đánh giá rồi mới phát triển.
Host từ chối `xhigh` hoặc provider không tới được: báo `BLOCKED` kèm lệnh và lỗi. Orchestrator ghi advisor unavailable, engine đi tiếp, phase không bị block. Không hạ thinking, không đổi model.
