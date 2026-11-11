# Nhiệm vụ

Sửa hai lỗi hợp đồng giữa các vai: (1) prompt vai engine trong `SKILL.md` chưa có bước dự thảo nên advisor không bao giờ được gọi, (2) vai code-review có ba hợp đồng verdict khác nhau.

# Đã sửa gì

- `skills/orchestrator/SKILL.md`: prompt vai engine có hai giai đoạn (dự thảo rồi phát triển); prompt qc và code-reviewer đòi dòng `VERDICT:` đúng token; Loop mục 4 đọc verdict bằng `bd.parse_verdict`; `LANG` không để child dịch `APPROVE` và `REQUEST_CHANGES`; bảng vai ghi đúng đầu ra.
- `board.py`: thêm `VERDICTS` và `parse_verdict`.
- `mau/brief-code-review.md`, `02-vai-tro-va-brief.md`: câu "định dạng của brief thắng định dạng của skill `ponytail-review`", kèm ánh xạ `Verdict: Ship.` sang APPROVE.
- `01-quy-trinh.md`, `CLAUDE.md`: phản hồi sai định dạng không phải verdict.
- `tests/test_role_contracts.py`, nối vào `gate.yml` và `CLAUDE.md`.

# Vấn đề thực sự

Cùng một vai được định nghĩa ở nhiều nơi và các nơi đó lệch nhau, không có gì đối chiếu chúng:

- `SKILL.md` bảo code-reviewer trả `PASS`, brief và `02` bảo trả `VERDICT: APPROVE|REQUEST_CHANGES`, còn skill `ponytail-review` tự trả `Verdict: Ship.`. Loop chờ `Both PASS` nên một child làm đúng brief sẽ không được Loop nhận ra.
- Ở lượt tích hợp advisor, tôi sửa brief mẫu nhưng không sửa prompt vai engine trong `SKILL.md`, chính là nơi `dispatch` thực sự lấy chỉ dẫn. Kết quả là engine có thể bỏ qua bước dự thảo.

# Tại sao chọn cách này

- **Chọn `APPROVE|REQUEST_CHANGES` cho code-review và `PASS|FAIL` cho qc** vì đó là hợp đồng đã có ở `01`, `02` và brief mẫu, nên đổi `SKILL.md` ít nhất.
- **Đọc verdict bằng máy, nghiêm ngặt:** đúng một dòng `VERDICT: <TOKEN>`, chữ hoa, không chữ thừa, token thuộc vai. Cái gì khác là `ValueError`, nghĩa là "chưa phải verdict" chứ không phải PASS. Điều này chặn đúng lỗi nguy hiểm nhất: hiểu nhầm một phản hồi lạ thành đạt.
- **Test lấy token từ `bd.VERDICTS`**, tức nguồn mà Loop dùng thật, rồi kiểm mọi nơi nhắc tới chúng. Mutation check: `parse_verdict` 8/8 (lần đầu 3 sống sót, do chưa có ca neo dòng và chữ hoa thường), test hợp đồng 12/12 (lần đầu 2 sống sót vì `DRAFT:` còn xuất hiện ở chỗ khác).

# Hình dạng production

- Loop vẫn là văn xuôi cho agent đọc: `parse_verdict` chỉ có tác dụng khi orchestrator gọi nó. Chưa có phiên orchestrator thật xác nhận điều này.
- Chưa kiểm một child code-review thật có tuân theo câu "brief thắng skill" hay không.
- `qc2` có trong `VERDICTS` nhưng `SKILL.md` chưa có vai `qc2` (lỗi có sẵn, chưa sửa).

# Các cách khác khả thi

1. Đổi brief và `02` theo `SKILL.md` (code-reviewer trả `PASS`).
2. Chấp nhận cả `Verdict: Ship.` của skill gốc trong `parse_verdict`.
3. Chỉ sửa văn bản, không thêm hàm đọc verdict.

# Tại sao không chọn các cách đó

1. Cách 1 bỏ mất nhãn APPROVE và REQUEST_CHANGES đã dùng khắp tài liệu và phân biệt reviewer chấm diff với qc chấm requirement. Hợp khi viết lại toàn bộ hợp đồng.
2. Cách 2 làm hợp đồng mềm đi: hai định dạng cho một ý nghĩa, và một câu như `Verdict: fix 1 first` phải được phân tích. Hợp khi không điều khiển được brief.
3. Cách 3 là cách đã để hợp đồng lệch ba nơi mà không ai biết.

# Khái niệm cốt lõi cần nắm

- **Nguồn thật và bản sao:** chọn một nơi làm nguồn (`bd.VERDICTS`), để test đối chiếu các bản sao với nó.
- **Parse nghiêm, lỗi là "chưa biết":** không đoán ý một phản hồi lạ. Nhầm "chưa biết" thành "đạt" là lỗi đắt nhất.
- **Chỉ dẫn xung đột:** khi brief và skill đều quy định định dạng, phải nói rõ bên nào thắng.

# Lỗi thường gặp

- Sửa một nơi định nghĩa vai mà quên nơi thật sự được dùng khi chạy (prompt trong `dispatch`).
- Test chỉ tìm chuỗi con (`DRAFT:`) nên bắt sót khi chuỗi đó còn ở chỗ khác. Phải kiểm cụm đúng của câu cần giữ.
- Regex không neo đầu và cuối dòng nên một câu nhắc tới verdict giữa đoạn văn bị đọc thành verdict.

# Ví dụ nhỏ

```python
bd.parse_verdict("code-reviewer", "DONE\nVERDICT: APPROVE\n")   # True
bd.parse_verdict("code-reviewer", "DONE\nVerdict: Ship.")       # ValueError: chưa phải verdict
bd.parse_verdict("qc", "DONE\nVERDICT: APPROVE")                # ValueError: sai token cho vai qc
```

# Lần sau nên nghĩ thế nào

1. Khi sửa một vai, liệt kê mọi nơi định nghĩa nó (prompt, brief mẫu, tài liệu, bảng vai, Loop) và có test đối chiếu chúng.
2. Hợp đồng đọc bằng máy thì viết hàm đọc và test nó, không chỉ viết quy tắc.
3. Tự hỏi: nếu một child làm đúng brief, orchestrator có nhận ra kết quả không?
