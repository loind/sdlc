# Skill đã dùng trong quy trình

Mỗi thư mục là một skill nguồn, **giữ nguyên nội dung gốc** (tiếng Anh, không dịch). Cài bằng cách chép thư mục vào nơi công cụ agent của bạn đọc skill (ví dụ `~/.agents/skills/`).

| Skill | Dùng ở bước | Một dòng |
|---|---|---|
| `thinker` | Thiết kế | Biến ý tưởng thô thành gói thiết kế (PRD, SRS, design, phases) mà orchestrator chạy được. |
| `orchestrator` | Thực thi | Chạy gói thiết kế: engine, qc + code-review, gate, devops, verifier, documenter; ghi board (`scripts/board.py`). |
| `grilling` | Thiết kế | Hỏi người dùng theo cây quyết định, từng vòng, kèm đáp án đề xuất. |
| `code-review` | Review | Rà thay đổi theo hai trục: chuẩn mã và đúng spec, chạy song song. |
| `ponytail-review` | Review | Rà chỉ để tìm thứ nên xoá: thừa thãi, phụ thuộc không cần, trừu tượng suy đoán. |
| `ponytail` | Viết mã | Ép lời giải ít nhất mà vẫn chạy được (YAGNI, thư viện chuẩn trước). |
| `tdd` | Viết mã | Test trước: vòng red, green, refactor, ưu tiên test tích hợp. |
| `diagnosing-bugs` | Sửa lỗi | Vòng chẩn đoán cho lỗi khó và hồi quy hiệu năng. |
| `research` | Nghiên cứu | Điều tra theo nguồn chính và ghi kết quả thành file Markdown trong repo. |
| `domain-modeling` | Tài liệu | Xây thuật ngữ cho `CONTEXT.md` và ghi ADR. |
| `writing-for-agents` | Tài liệu | Viết tài liệu cho agent: skill, `AGENTS.md`, `CLAUDE.md`. |

## Lưu ý

- `orchestrator/SKILL.md` có bảng model theo vai và vài đường dẫn của môi trường gốc (ví dụ `~/.agents/skills/...`). Chỉnh theo môi trường của bạn. Tên lệnh spawn và gửi tin phụ thuộc công cụ agent.
- `orchestrator/scripts/board.py` chỉ cần Python 3, không phụ thuộc gói ngoài. Chạy `python3 board.py` để chạy bộ kiểm tự thân (`demo()` in `ok`).
- `code-review` nói đến một file cấu hình issue tracker (`docs/agents/issue-tracker.md`). Nếu repo của bạn chưa có, tạo file đó hoặc bỏ bước đọc spec từ ticket.
- Skill `orchestrator` bản gốc bảo xoá child sau mỗi phase. Dự án gốc đổi luật này: **không xoá child** (xem `../01-quy-trinh.md`, mục "Quy tắc vận hành khác"). Chọn một cách và ghi vào quy tắc agent của bạn.
- `thinker` khuyến nghị model mạnh nhất và thinking cao. Phần dễ hỏng nhất là cây quyết định và việc gọi tên vấn đề thiết kế.
