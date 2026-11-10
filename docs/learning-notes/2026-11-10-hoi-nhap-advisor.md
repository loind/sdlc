# Nhiệm vụ

Hội nhập vai `advisor` (vừa merge từ remote) vào orchestrator theo bốn điểm đã chốt, giữ advisor trong phase và trước khi phát triển: không phải state board, lỗi không block phase, chỉ chạy lại khi có dự thảo mới, trần đầu vào.

# Đã sửa gì

- `board.py`: thêm `advisor_draft` (so mã băm nội dung dự thảo, từ chối dự thảo quá 1500 từ) và `advisor_unavailable` (ghi notes và board log, bỏ deadline, không đổi status).
- `skills/orchestrator/SKILL.md`: `child_name` trả `advisor-p<phase>-draft`; thêm `dispatch_advisor`, `THINKING`, bước draft trong Loop, ngoại lệ advisor ở Reporting contract, Watching for silence và `WATCH_INSTRUCTION`.
- `models.json`: thêm vai `advisor` (`xai/grok-4.7`).
- `01`, `02`, `mau/brief-engine.md`, `mau/brief-advisor.md`, `skills/advisor/SKILL.md`: tên mới, không tính vào 3 vòng, advisor lỗi thì engine đi tiếp, trần 1500 từ, chỉ đọc thứ engine đưa. Brief engine được thêm giai đoạn dự thảo.
- `docs/adr/0002-*.md` (số do `board.next_adr` cấp), `CONTEXT.md`, `CLAUDE.md`, mẫu `RETIRED` cho tên cũ.

# Vấn đề thực sự

Commit advisor trên remote chỉ sửa tài liệu. `01` mô tả bước advisor nhưng orchestrator không biết giao việc cho nó (`BUDGET_MIN` thiếu nên `dispatch("advisor")` sẽ `KeyError`), brief engine chưa có bước dự thảo, và tên `advisor-p<phase>-r<vòng>` buộc advisor chạy theo `round` của reviewer. Hai lỗi thiết kế nằm sau đó: coi lời khuyên như một vòng review, và để một provider sập chặn cả phase.

# Tại sao chọn cách này

- **Advisor không vào `FLOW`:** `advance`, `rework` và heartbeat không phải học thêm trạng thái nào.
- **"Chỉ chạy lại khi có dự thảo mới" được ép bằng code:** `advisor_draft` trả `False` cho cùng nội dung, nên vòng sửa sau FAIL không gửi advisor lại. Mã băm theo nội dung, không theo đường dẫn, nên dự thảo viết lại được tính là mới.
- **Trần 1500 từ cũng nằm trong `advisor_draft`**, cùng chỗ với kiểm trùng, nên orchestrator không thể quên.
- **Lỗi advisor đi qua một cửa:** `dispatch_advisor` bắt ngoại lệ của spawn (host từ chối `xhigh`) và gọi `advisor_unavailable`. Ngoại lệ cùng loại cho mọi đường khác (`BLOCKED`, im lặng) đều được ghi ở Loop, Reporting contract, Watching for silence và `WATCH_INSTRUCTION`.
- **Kiểm chứng:** test chạy nguyên văn code trong `SKILL.md` (đã có 8/8 đột biến bị bắt) và mutation cho `board.py` (9/9).

# Hình dạng production

- Advisor có thể vắng mặt mà phase vẫn xong, nên chất lượng khi vắng chỉ còn qc và code-review đỡ. Điều này ghi trong ADR-0002.
- `query="grok"` trong `models.json` là phỏng đoán theo kiểu các vai khác: cách `rlm.find_models` khớp `query` chưa kiểm chứng. Nếu không thấy đúng một bản thì `pick()` dừng.
- Chưa chạy advisor thật trên kernel.

# Các cách khác khả thi

1. Thêm trạng thái `advisor` vào board.
2. Giữ tên có vòng `advisor-p<phase>-r<vòng>`.
3. Coi `BLOCKED` của advisor như mọi child khác (`bd.block`).
4. Chỉ viết quy tắc "đừng chạy lại" vào tài liệu.

# Tại sao không chọn các cách đó

1. Cách 1 hợp khi điểm advisor thật sự đóng được phase. Ở đây nó không, nên chỉ thêm độ phức tạp.
2. Cách 2 hợp khi advisor chấm lại sau mỗi vòng sửa. Quyết định hiện tại là chấm dự thảo, không chấm vòng sửa.
3. Cách 3 hợp khi nội dung advisor là điều kiện của phase (ví dụ cổng bảo mật bắt buộc). Ở đây nó là lời khuyên.
4. Cách 4 chính là kiểu quy tắc đã để lọt `NameError` và heartbeat thiếu guard ở các đợt trước.

# Khái niệm cốt lõi cần nắm

- **State và việc phụ:** state board là thứ quyết định phase đi đâu. Một việc phụ (advisor) nên lưu dấu vết (note, log, mã băm) chứ không nên thành state.
- **Idempotency theo nội dung:** khoá chống chạy lại là mã băm của chính đầu vào, không phải tên file hay số vòng.
- **Một cửa cho lỗi:** gom xử lý lỗi vào một hàm, rồi kiểm mọi đường khác dẫn tới nó.

# Lỗi thường gặp

- Sửa "đường chính" (`BLOCKED` ở Loop) mà quên đường phụ (`Watching for silence`, ladder của heartbeat). Một lần grep `bd.block` mới lộ ra dòng còn sót.
- `dispatch("advisor")` khi `BUDGET_MIN` thiếu vai: `KeyError`, chỉ lộ khi chạy.
- Thêm vai mới vào docs nhưng không thêm vào `models.json` và tuple `pick`.
- Dự thảo viết nhiều thì advisor chấm hời hợt: trần từ phải được kiểm bằng code.

# Ví dụ nhỏ

```python
if not bd.advisor_draft(board, phase["id"], draft_path):   # False nếu cùng nội dung; AssertionError nếu > 1500 từ
    return None
try:
    return await dispatch("advisor", phase, brief, board)
except Exception as e:                                      # host từ chối xhigh, provider sập
    bd.advisor_unavailable(board, phase["id"], f"{type(e).__name__}: {e}")
```

# Lần sau nên nghĩ thế nào

1. Khi thêm một vai mới: kiểm đủ năm nơi (tên child, ngân sách, model, brief, Loop) trước khi coi là xong.
2. Với mỗi quy tắc "không làm X khi Y", tìm điểm mà X thực sự xảy ra trong code và đặt guard ở đó.
3. Sau khi sửa một đường xử lý lỗi, grep mọi đường khác cùng loại (`bd.block`) để tìm chỗ sót.
