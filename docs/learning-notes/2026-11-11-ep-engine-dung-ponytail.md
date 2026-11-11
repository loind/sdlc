# Nhiệm vụ

Bắt engine dùng skill `ponytail` ở mức `full`. Trước đó engine không được chỉ định dùng skill nào, nên việc có nạp `ponytail` hay không phụ thuộc vào việc model tự quyết.

# Đã sửa gì

- `mau/brief-engine.md`, khối engine trong `02-vai-tro-va-brief.md`, prompt vai engine trong `skills/orchestrator/SKILL.md`: thêm yêu cầu đọc và áp dụng `ponytail` mức `full` suốt phase.
- `CLAUDE.md`: thêm luật tương ứng.
- `tests/test_engine_ponytail.py`: kiểm cả ba nơi đều có yêu cầu, đã nối vào `gate.yml` và `CLAUDE.md`.

# Vấn đề thực sự

Mức `full` là mặc định của chính skill, không phải của quy trình. Docs Prime Agent nói model không phải lúc nào cũng nạp skill khi nhiệm vụ khớp mô tả ("models don't always do this; use prompting or `/skill:name` to force it"). Muốn chắc chắn thì phải nói thẳng trong brief.

Engine nhận chỉ dẫn từ ba nơi (brief mẫu, khối trong `02`, prompt vai trong `SKILL.md`), nên sửa một nơi thì hai nơi còn lại lệch.

# Tại sao chọn cách này

- **Ghi yêu cầu cả ba nơi và có test:** cùng bài học với khung chung của brief: nguồn nhân bản phải có gì đó giữ cho chúng khớp nhau.
- **Brief thắng skill khi xung đột:** skill đòi kết thúc bằng hai dòng "đã bỏ gì, chưa kiểm gì" và viết ngắn bằng tiếng Anh, còn quy trình đòi báo cáo tiếng Việt có dấu theo mẫu. Hai dòng của skill được đưa vào mục `Điểm chưa chắc`.
- **Mutation check:** 4/4 đột biến bị bắt (xoá ở từng nơi, đổi `full` thành `lite`).

# Hình dạng production

Yêu cầu nằm trong brief nên có hiệu lực với mọi engine, bất kể model. Việc engine thực sự nạp skill vẫn do model thực hiện: chưa chạy một phiên engine thật để xác nhận. Chưa kiểm child của Prime Agent có thấy danh sách skill của `~/.agents/skills` hay không.

# Các cách khác khả thi

1. Đặt `ponytail` vào system prompt hoặc cấu hình của Prime Agent cho mọi child.
2. Truyền `/skill:ponytail full` khi spawn.
3. Không ép, để model tự nạp theo mô tả skill.

# Tại sao không chọn các cách đó

1. Cách 1 áp cho cả vai không viết mã (qc, verifier, documenter). Hợp khi mọi child đều cần phong cách này.
2. Cách 2 là lệnh của người dùng trong giao diện, child chạy nền không gõ được. Hợp khi người dùng spawn trực tiếp.
3. Cách 3 là hiện trạng: không đảm bảo và không kiểm được.

# Khái niệm cốt lõi cần nắm

- **Mặc định của công cụ khác mặc định của quy trình:** `full` chỉ có nghĩa khi skill đã được nạp.
- **Xung đột chỉ dẫn:** khi hai nguồn chỉ dẫn mâu thuẫn, phải nói rõ nguồn nào thắng, nếu không child chọn theo cảm tính.
- **Progressive disclosure:** chỉ mô tả skill luôn nằm trong context, thân `SKILL.md` chỉ nạp khi cần.

# Lỗi thường gặp

- Tin rằng skill đang "bật" chỉ vì nó được cài.
- Sửa brief mẫu mà quên prompt vai trong `SKILL.md`. Khi sửa lần này phát hiện prompt vai engine trong `SKILL.md` vẫn chưa có bước dự thảo của advisor (xem bàn giao).
- Thêm yêu cầu mà không có test giữ nó.

# Ví dụ nhỏ

```text
Kỹ năng bắt buộc: đọc và áp dụng skill `ponytail` ở mức `full` (mặc định của skill) trong suốt phase ...
Khi chỉ dẫn của skill xung đột với brief này thì brief thắng ...
```

# Lần sau nên nghĩ thế nào

1. Muốn một hành vi chắc chắn thì viết nó vào brief, không dựa vào việc model tự nạp.
2. Với nội dung nhân bản ở nhiều nơi, thêm test kiểm cả các nơi cùng lúc.
3. Khi sửa một vai, đọc lại mọi nơi định nghĩa vai đó, vì chúng có thể đã lệch từ trước.
