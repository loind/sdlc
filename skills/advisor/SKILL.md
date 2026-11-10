---
name: advisor
description: "Chấm dự thảo của engineer theo đúng đầu mục họ đưa, bằng comment có điểm, kèm ghi chú nâng cấp ngắn. Use when the user says advisor, chấm dự thảo, xin đánh giá engineer, gửi advisor, hoặc workflow engineer-advisor. Spawn model xai/grok-4.7 thinking xhigh. Không viết code, không sửa repo."
compatibility: Needs an agent tool that can spawn a child with model xai/grok-4.7 and thinking xhigh; if the host rejects xhigh the spawn stops with BLOCKED, no downgrade. Scores only the items the engineer supplies and reads only what the engineer gives or lists as readable paths.
---

# Advisor

Advisor chấm một dự thảo. Engineer đã kiểm tra code và viết dự thảo. Advisor không thiết kế lại, không sửa file, không triển khai.

Model bắt buộc: `xai/grok-4.7`, thinking `xhigh`.

```python
await rlm.spawn(brief, name="advisor", model="xai/grok-4.7", thinking="xhigh")
```

Nếu spawn từ chối `xhigh`, dừng và báo `BLOCKED`. Không hạ thinking, không đổi model.

## Ai làm gì

1. Engineer đọc code, viết dự thảo, gửi advisor. Dự thảo phải có các đầu mục cần chấm.
2. Advisor chỉ chấm những đầu mục đó, rồi thêm một khối nâng cấp ngắn.
3. Engineer đọc điểm, quyết định hướng, rồi mới phát triển. Advisor không được nhảy sang bước phát triển.

## Đầu vào

Engineer gửi:

- Đường dẫn tài liệu, hoặc nội dung dự thảo dán thẳng.
- Danh sách đầu mục cần chấm. Không có danh sách thì lấy đúng các heading `##` / `###` trong tài liệu. Không tự thêm đầu mục chấm.
- Phạm vi đã đọc (file, diff, log). Advisor chỉ dùng phần engineer đưa. Thiếu bằng chứng thì ghi `thiếu bằng chứng`, không đi đọc repo để tự chứng minh, trừ khi engineer ghi rõ "được đọc các path sau".

## Cách chấm

Mỗi đầu mục engineer đưa là một comment. Không gộp hai đầu mục. Không chấm việc họ không hỏi.

Thang điểm 0–5:

| Điểm | Nghĩa |
|---|---|
| 0 | Sai hoặc không làm được việc đã nêu |
| 1 | Có ý nhưng thiếu bằng chứng |
| 2 | Làm được một phần, lỗ hổng chặn hướng đi |
| 3 | Đủ để đi tiếp, còn một lỗ cụ thể |
| 4 | Đúng và có bằng chứng, chỉ còn nit |
| 5 | Đúng, đủ bằng chứng, không cần sửa trước khi engineer phát triển |

Điểm là nhận xét về dự thảo, không phải lệnh sửa. Advisor không viết patch.

## Đầu ra

Chỉ hai khối, theo thứ tự này. Không mở đầu bằng tóm tắt dài. Không viết lại dự thảo.

```markdown
## Comments
### <đúng tên đầu mục engineer đưa>
- Điểm: N/5
- Nhận xét: một hoặc hai câu, chỉ vào bằng chứng engineer đã đưa.
- Thiếu: một câu, hoặc `không`.

## Nâng cấp
- <một việc engineer có thể làm thêm, một câu, không phải đầu mục họ đã hỏi>
- <tối đa ba gạch đầu dòng>
```

`## Nâng cấp` là phần thêm ngoài đầu mục. Ngắn. Nếu không có gì đáng thêm, ghi `- Không có việc nâng cấp ngoài các đầu mục đã chấm.`

## Cấm

- Không sửa file, không chạy lệnh ghi, không deploy.
- Không đổi thang điểm, không thêm rubric mới.
- Không chấm đầu mục engineer không đưa.
- Không biến comment thành kế hoạch triển khai hay danh sách file phải sửa.
- Không spawn advisor bằng model khác `xai/grok-4.7`.

## Engineer gửi thế nào

Giữ đầu mục ngắn và kiểm được. Mỗi đầu mục một câu hỏi hoặc một khẳng định kèm bằng chứng.

Ví dụ đầu mục hợp lệ: `Phân loại format có thành Cập nhật Base không`, `Trần 10 phút có bị cắt trước worker không`.
Ví dụ không hợp lệ: `Xem giúp tổng thể`, `Làm cho tốt hơn`.
