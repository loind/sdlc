# Skill đã dùng trong quy trình

Mỗi thư mục là một skill nguồn, **giữ nguyên nội dung gốc** (tiếng Anh, không dịch). Cài bằng cách chép thư mục vào nơi công cụ agent của bạn đọc skill (ví dụ `~/.agents/skills/`).

| Skill | Dùng ở bước | Một dòng |
|---|---|---|
| `thinker` | Thiết kế | Biến ý tưởng thô thành gói thiết kế (PRD, SRS, design, phases) mà orchestrator chạy được. |
| `orchestrator` | Thực thi | Chạy gói thiết kế: engine, qc + code-review, gate, devops, verifier, documenter; ghi board (`scripts/board.py`). |
| `grilling` | Thiết kế | Hỏi người dùng theo cây quyết định, từng vòng, kèm đáp án đề xuất. |
| `ponytail-review` (5.1.0) | Review | Vai code-review trong quy trình dùng skill này. Review chất lượng đầy đủ theo thứ tự: đúng, an toàn, chịu tải, có test, nhanh, gọn. Đọc cả mã liên quan, không chỉ diff. |
| `code-review` | Review | Rà thay đổi theo hai trục: chuẩn mã (Standards) và đúng spec (Spec), chạy hai sub-agent song song rồi gộp. Dùng khi người dùng tự yêu cầu review một nhánh. |
| `ponytail` (5.1.0) | Viết mã | Ép lời giải ít nhất mà vẫn chạy được (YAGNI, thư viện chuẩn trước). |
| `tdd` | Viết mã | Test trước: vòng red, green, refactor, ưu tiên test tích hợp. |
| `diagnosing-bugs` | Sửa lỗi | Vòng chẩn đoán cho lỗi khó và hồi quy hiệu năng. |
| `research` | Nghiên cứu | Điều tra theo nguồn chính và ghi kết quả thành file Markdown trong repo. |
| `domain-modeling` | Tài liệu | Xây thuật ngữ cho `CONTEXT.md` và ghi ADR. |
| `writing-for-agents` | Tài liệu | Viết tài liệu cho agent: skill, `AGENTS.md`, `CLAUDE.md`. |

## Lưu ý

- Bảng model theo vai nằm ở `orchestrator/models.json` (engine `deepseek-v4-flash`, documenter `gemini-3.8-flash`, còn lại `claude-sonnet-5-5`). `orchestrator/SKILL.md` còn vài đường dẫn của môi trường gốc (ví dụ `~/.agents/skills/...`). Chỉnh theo môi trường của bạn. Tên lệnh spawn và gửi tin phụ thuộc công cụ agent.
- `orchestrator/scripts/board.py` chỉ cần Python 3, không phụ thuộc gói ngoài. Chạy `python3 scripts/board.py demo` trong thư mục `orchestrator` để chạy bộ kiểm tự thân (`demo()` in `ok`). Board nằm ở đúng một đường dẫn: `.prime/orchestrator/board.json`.
- `ponytail` và `ponytail-review` là bản **5.1.0**. Từ bản 5, `ponytail-review` không còn chỉ tìm mã thừa: nó review chất lượng đầy đủ (đúng, an toàn, chịu tải, có test, nhanh, gọn). Các skill phụ `ponytail-audit`, `ponytail-debt`, `ponytail-gain`, `ponytail-help` không nằm trong thư mục này. Cài từ nguồn gốc nếu cần.
- `code-review` cần một issue tracker để lấy spec: nó đọc cấu hình tracker mà môi trường cung cấp. Nếu repo của bạn chưa có, bỏ bước đọc spec từ ticket. Trong quy trình này child code-review **không sinh child con**, nên vai code-review dùng `ponytail-review` chứ không chạy hai sub-agent của `code-review`. Trục Spec đã do `qc` chấm.
- Skill `orchestrator` giữ child tới cuối run, không xoá sau mỗi phase (xem `../01-quy-trinh.md`, mục "Quy tắc vận hành khác"). Đội muốn dọn sớm thì đổi ở cả skill lẫn quy tắc agent.
- Mọi `SKILL.md` có `name` khớp tên thư mục và `compatibility` (skill cần gì để chạy, tối đa 500 ký tự). Chỉ frontmatter được đồng đều, nội dung gốc giữ nguyên. `python3 scripts/check-skills.py` ép điều này và chạy trong gate.
- `thinker` khuyến nghị model mạnh nhất và thinking cao. Phần dễ hỏng nhất là cây quyết định và việc gọi tên vấn đề thiết kế.
