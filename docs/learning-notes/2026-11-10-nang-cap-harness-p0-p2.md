# Nhiệm vụ

Nâng harness SDLC (repo `sdlc`) về chuẩn prime-agent theo ba nhóm: P0 (gate, board, async contract), P1 (ADR, `CONTEXT.md`, `CLAUDE.md`, cổng `check-docs`), P2 (gitflow và packaging). Ràng buộc: mỗi việc một commit nhỏ trên nhánh feature, không push, không tag, mỗi gate là một lệnh đơn.

# Đã sửa gì

- **P0.1:** `scripts/run-gate.sh` là runner duy nhất cho gate. Docs, brief engine/qc và skill `orchestrator` đều gọi qua nó.
- **P0.2:** `board.py` ghi atomic (tmp rồi `os.replace`), có `schema_version`, thêm helper `set_deadline`, `overdue`, `set_heartbeat`, `clear_heartbeat`, `next_adr`.
- **P0.3:** viết lại ví dụ spawn thành `dispatch()` fire-and-forget, thêm mục Async contract và `FRAME` dùng chung cho mọi brief, bỏ bước xoá child.
- **P0.4:** `skills/orchestrator/models.json` và resolver `pick()` khớp exact id.
- **P1:** ADR 0001, `CONTEXT.md`, `CLAUDE.md`, `scripts/check-docs.sh` với `--self-test`, workflow `.github/workflows/gate.yml`.
- **P2:** `check-pins.sh`, `check-downgrade.py`, `check-tags.sh`, `check-skills.py`, `compatibility` cho 10 skill, đường dẫn cài repo-local `.agents/skills/`.

# Vấn đề thực sự

Vấn đề không phải là thiếu script. Tài liệu và skill **lệch với runtime thật**, và nhiều cổng có thể báo xanh giả:

- Skill gọi `await rlm(...)`, nhưng kernel Prime Agent báo `'rlm' is not callable`. API đúng là `await rlm.spawn(...)`.
- Skill viết "child không thể sinh child", nhưng tài liệu runtime nói `RLM_MAX_DEPTH` mặc định là 2, nên child sinh được grandchild.
- Gate qua pipe (`... | tail`) trả exit code của `tail`, che lệnh đỏ.
- Bản mẫu `check-docs` nuốt lỗi `git grep` và in OK, vì `hits` rỗng khi regex hỏng hoặc đứng ngoài repo.

Gốc chung: viết tài liệu từ trí nhớ thay vì từ nguồn đã verify, và tin một cổng chỉ vì nó từng xanh.

# Tại sao chọn cách này

- **Verify từ nguồn cài trên máy trước khi viết:** đọc `rlm/__init__.py` và `docs/rlm-runtime.md` của bản Prime Agent 0.9.8. Nhờ vậy phát hiện được cả hai câu sai ở trên.
- **Mỗi script có `--self-test` và đã qua mutation check:** phá từng điều kiện trên bản sao, self-test phải đỏ. Kết quả: check-docs 6/6, check-pins 7/7, check-downgrade 11/11, check-tags 7/7, check-skills 10/10, board 9/9. Hai lần có đột biến sống sót (chưa test đường lỗi `git grep`, chưa test chuẩn hoá `1.2` và `1.2.0`) và đều được bù test.
- **Test chạy đúng đoạn code trích từ `SKILL.md`** với kernel giả, nên tài liệu và test không tách rời.
- **Ngoại lệ phải có lý do:** `downgrade-allow.txt` từ chối dòng không có `# lý do`.

# Hình dạng production

- CI: `.github/workflows/gate.yml` chạy đúng lệnh "Gate đầy đủ" trong `CLAUDE.md` (đã so khớp bằng lệnh, và đã chạy thử trong một clone sạch: 8/8 xanh). Chưa chạy trên runner GitHub.
- Tag: `check-tags.sh` chỉ bắt được tag sai mẫu, tag chỉ ở local, tag bị dời. Việc chỉ cho CI tạo `MASTER-*` và `TEST-*` phải do **protected tags** trên remote đảm bảo.
- Ghim phụ thuộc: pipeline của MR truyền nhánh đích (`--branch develop`).
- Child sinh child: hiện chỉ là luật trong brief. Chặn cứng nhiều khả năng cần đặt giới hạn độ sâu thấp hơn mặc định (tài liệu runtime nhắc `RLM_MAX_DEPTH`), nhưng tôi chưa tìm thấy cách cấu hình trong tài liệu và chưa kiểm chứng, nên chưa làm.

# Các cách khác khả thi

1. **Chặn child sinh child bằng cấu hình runtime** (`RLM_MAX_DEPTH=1`) thay vì luật trong brief.
2. **Kiểm hạ phiên bản bằng `git diff` và `grep`** thay vì parse file khoá.
3. **Kiểm tag bằng protected tags trên remote**, không dùng script.
4. **Commit các test snippet vào `tests/`** thay vì chỉ chạy trong scratchpad.

# Tại sao không chọn các cách đó

1. Cách 1 là cứng hơn, nhưng cần biết chỗ cấu hình và quyền sửa runtime. Hợp khi bạn sở hữu runtime và muốn một giới hạn không phụ thuộc vào việc model có nghe brief hay không.
2. Cách 2 nhanh cho một repo một ngôn ngữ. Nó không phân biệt được hạ và xoá, mà `03-gitflow` yêu cầu phân biệt hai việc này. Hợp khi chỉ cần cảnh báo, không cần chặn.
3. Cách 3 là cách đúng nhất cho "không gắn tay", nhưng nằm ngoài repo và cần quyền quản trị remote. Nên làm song song với script, không thay script.
4. Cách 4 giữ được test cho `dispatch` và `pick` trong CI. Tôi chưa làm vì ngoài phạm vi P0 đến P2. Hợp khi `SKILL.md` còn thay đổi nhiều.

# Khái niệm cốt lõi cần nắm

- **Admission khác completion:** `rlm.spawn` trả handle khi child được nhận, không trả câu trả lời. Kết quả về sau qua `agent_message`.
- **Exit code và pipe:** pipeline trả exit code của lệnh cuối, trừ khi bật `pipefail`. Gate một lệnh đơn tránh cả vấn đề này.
- **Cổng không rỗng:** cổng chỉ đáng tin khi đã thấy nó đỏ. Mẫu mồi (canary) trong repo tạm làm việc đó.
- **`git grep` exit code:** 0 có khớp, 1 không khớp, từ 2 trở lên là lỗi. Lỗi không được tính là sạch.
- **Atomic write:** ghi file tạm cùng thư mục rồi `os.replace`. Reader thấy bản cũ hoặc bản mới, không bao giờ thấy nửa file.
- **ID đơn điệu:** `next_adr` lấy max của counter trên board và số lớn nhất trên đĩa, rồi cộng 1.
- **HẠ khác XOÁ:** package biến mất hoặc chỉ bớt bản là xoá. Hạ là bản cao nhất cũ mất và một bản thấp hơn xuất hiện.

# Lỗi thường gặp

- Viết `"1.10.0" < "1.9.0"` bằng so chuỗi. Phải so từng số.
- Lấy `find_models(...)[0]`, hoặc quên rằng `limit` mặc định là 8 nên bản cần chọn có thể bị cắt.
- Tin ref hoặc đường dẫn gõ sai là "không có gì để so" và trả OK. Phải dừng với exit 2.
- Chạy test ghi file theo `cwd` ngay trong repo. Chính tôi đã làm tạo ra `.prime/` ở gốc repo khi chạy một test trong gate; đã xoá đúng các file đó. Test nên chạy trong thư mục tạm.
- Dùng mảng kết hợp trong bash: macOS mặc định là bash 3.2, không có. `check-tags.sh` dùng `awk`.
- Sửa file bằng thay chuỗi mà không `assert count == 1`. Dấu nháy kiểu typographic từng làm một lệnh Edit không khớp.

# Ví dụ nhỏ

Gate qua runner, đỏ thì dừng ở lệnh đầu tiên, và pipe bị từ chối:

```bash
scripts/run-gate.sh "false" "echo hi"      # GATE_RED at [1], exit 1, "echo hi" không chạy
scripts/run-gate.sh "false | tail -5"      # REJECT, exit 2
```

Phân biệt "không khớp" với "lỗi" khi dùng `git grep`:

```bash
hits="$(git grep -nE "$pat" -- . "${EXCLUDE[@]}")"; rc=$?
[ "$rc" -gt 1 ] && { echo "git grep lỗi (exit $rc)" >&2; exit 2; }
```

# Lần sau nên nghĩ thế nào

1. Trước khi viết ví dụ về một công cụ, đọc nguồn hoặc tài liệu của bản đang cài. Câu nào về giới hạn nền tảng cũng phải có trích dẫn.
2. Với mỗi cổng, hỏi: "Làm sao tôi biết nó đỏ được?" Nếu chưa thấy nó đỏ, chưa coi nó là cổng.
3. Với mỗi lỗi đầu vào (ref sai, file sai, định dạng lạ), mặc định là dừng với exit 2, không phải pass.
4. Tách rõ cái script kiểm được và cái phải do quyền hạn trên hệ thống khác đảm bảo, rồi ghi thẳng vào tài liệu.
