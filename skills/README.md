# Skill đã dùng trong quy trình

Mỗi thư mục là một skill nguồn, **giữ nguyên nội dung gốc** (tiếng Anh, không dịch). Cài repo-local: chép từng thư mục vào `.agents/skills/` ở gốc repo của dự án (Prime Agent đọc thư mục này từ `cwd` lên tới git root) và commit cùng mã, để skill được review và đúng phiên bản với repo. Công cụ agent khác: dùng thư mục skill cấp repo của công cụ đó.

| Skill | Dùng ở bước | Một dòng |
|---|---|---|
| `thinker` | Thiết kế | Biến ý tưởng thô thành gói thiết kế (PRD, SRS, design, phases) mà orchestrator chạy được. |
| `advisor` | Trong phase, trước khi engine phát triển | Chấm dự thảo theo đúng đầu mục engine đưa (điểm 0–5) và thêm tối đa ba gạch nâng cấp. Model `xai/grok-4.7`, thinking `xhigh`. |
| `orchestrator` | Thực thi | Chạy gói thiết kế: engine, qc + code-review, gate, devops, verifier, documenter; ghi board (`scripts/board.py`). |
| `grilling` | Thiết kế | Hỏi người dùng theo cây quyết định, từng vòng, kèm đáp án đề xuất. |
| `ponytail-review` (5.3.3) | Review | Vai code-review trong quy trình dùng skill này. Review chất lượng đầy đủ theo thứ tự: đúng, an toàn, chịu tải, có test, nhanh, gọn. Đọc cả mã liên quan, không chỉ diff. |
| `code-review` | Review | Rà thay đổi theo hai trục: chuẩn mã (Standards) và đúng spec (Spec), chạy hai sub-agent song song rồi gộp. Dùng khi người dùng tự yêu cầu review một nhánh. |
| `ponytail` (5.3.3) | Viết mã | Ép lời giải ít nhất mà vẫn chạy được (YAGNI, thư viện chuẩn trước). |
| `tdd` | Viết mã | Test trước: vòng red, green, refactor, ưu tiên test tích hợp. |
| `diagnosing-bugs` | Sửa lỗi | Vòng chẩn đoán cho lỗi khó và hồi quy hiệu năng. |
| `research` | Nghiên cứu | Điều tra theo nguồn chính và ghi kết quả thành file Markdown trong repo. |
| `domain-modeling` | Tài liệu | Xây thuật ngữ cho `CONTEXT.md` và ghi ADR. |
| `writing-for-agents` | Tài liệu | Viết tài liệu cho agent: skill, `AGENTS.md`, `CLAUDE.md`. |

## Lưu ý

- Bảng model theo vai nằm ở `orchestrator/models.json` (engine `deepseek-v4-flash`, documenter `gemini-3.8-flash`, advisor `grok-4.7` thinking `xhigh`, còn lại `claude-sonnet-5-5`, gồm cả qc và qc2 vì hai qc cùng model theo người dùng chốt 11/11/2026). `orchestrator/SKILL.md` giả định cài repo-local tại `.agents/skills/orchestrator/` và chạy với `cwd` là gốc repo (board nằm ở `.prime/orchestrator/board.json` tính từ đó). Tên lệnh spawn và gửi tin phụ thuộc công cụ agent.
- `orchestrator/scripts/board.py` chỉ cần Python 3, không phụ thuộc gói ngoài. Chạy `python3 scripts/board.py demo` trong thư mục `orchestrator` để chạy bộ kiểm tự thân (`demo()` in `ok`). Board nằm ở đúng một đường dẫn: `.prime/orchestrator/board.json`.
- `ponytail` và `ponytail-review` là bản **5.3.3** (upstream `DietrichGebert/ponytail`, tag `v5.3.3`). So với 5.1.0, thân `SKILL.md` của cả hai không đổi; `ponytail` chỉ thêm `off` vào `argument-hint`. Phần còn lại của 5.1.1 đến 5.3.3 là hook, giao diện (band) và nền tảng khác, không nằm trong thư mục này. Từ bản 5, `ponytail-review` không còn chỉ tìm mã thừa: nó review chất lượng đầy đủ (đúng, an toàn, chịu tải, có test, nhanh, gọn). Các skill phụ `ponytail-audit`, `ponytail-debt`, `ponytail-gain`, `ponytail-help` không nằm trong thư mục này. Cài từ nguồn gốc nếu cần.
- `code-review` cần một issue tracker để lấy spec: nó đọc cấu hình tracker mà môi trường cung cấp. Nếu repo của bạn chưa có, bỏ bước đọc spec từ ticket. Trong quy trình này child code-review **không sinh child con**, nên vai code-review dùng `ponytail-review` chứ không chạy hai sub-agent của `code-review`. Trục Spec đã do `qc` chấm.
- Skill `orchestrator` giữ child tới cuối run, không xoá sau mỗi phase (xem `../01-quy-trinh.md`, mục "Quy tắc vận hành khác"). Đội muốn dọn sớm thì đổi ở cả skill lẫn quy tắc agent.
- Mọi `SKILL.md` có `name` khớp tên thư mục và `compatibility` (skill cần gì để chạy, tối đa 500 ký tự). Chỉ frontmatter được đồng đều, nội dung gốc giữ nguyên. `python3 scripts/check-skills.py` ép điều này và chạy trong gate.
- `thinker` khuyến nghị model mạnh nhất và thinking cao. Phần dễ hỏng nhất là cây quyết định và việc gọi tên vấn đề thiết kế.
- `advisor` chỉ chấm đầu mục engineer đưa. Điểm không đóng phase. Spawn `xai/grok-4.7` thinking `xhigh`; host từ chối `xhigh` thì ghi advisor unavailable và engine đi tiếp (phase không bị block), không hạ model.
