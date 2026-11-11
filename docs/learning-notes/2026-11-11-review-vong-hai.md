# Nhiệm vụ

Tự đánh giá vòng hai: review chính các bản sửa của vòng một (`02ccb3d..8e1e0ee`), sửa những gì tìm ra, rồi đẩy lên `main`.

# Đã sửa gì

- `skills/orchestrator/SKILL.md`: Loop bước 0 chỉ xoá deadline khi báo cáo được chấp nhận; `NEEDS_CONTEXT` và verdict sai định dạng trả lời qua `dispatch` (deadline mới). Đoạn `run_gate` chỉ gọi `advance` khi gate xanh. `dispatch` khôi phục deadline cũ khi gửi lỗi cho child đang tồn tại.
- `scripts/check-downgrade.py`: một luật duy nhất, xét từng bản cũ bị mất, so với bản mới-thêm cùng nhóm trước, rồi mọi bản mới-thêm.
- `scripts/check-skills.py`: duyệt từng ký tự để kiểm chuỗi nháy (escape hợp lệ, nháy đóng, comment sau nháy), thêm `- `, `? `, `,` vào ký tự dành riêng.
- `board.py`: `parse_verdict` chịu được BOM, khoảng trắng, `**DONE**`, CRLF, fence `~~~`, và từ chối `DONE-ish`; `save` giữ quyền file; test cho `phase_gate`.
- `scripts/run-gate.sh`: từ chối lệnh gate chỉ là comment.
- Test: `test_run_gate_snippet` chạy nguyên văn đoạn `run_gate`, test gửi lỗi cho child đang tồn tại.

# Vấn đề thực sự

Bốn trong chín phát hiện **do chính bản sửa vòng một gây ra**:

- Bước 0 xoá deadline ngay khi nhận `DONE`, nên đường "gửi lại định dạng" (vốn xảy ra nhiều hơn sau khi `parse_verdict` chặt hơn) để child nợ báo cáo mà không ai canh.
- So theo nhóm major để vá một lỗ lại tạo hai lỗ: không thấy hạ sang nhóm mới, và báo đỏ oan khi chỉ bớt bản.
- `advance` chặt hơn làm lộ lỗi có sẵn của đoạn `run_gate`: gate đỏ thì ném lỗi thay vì gửi về engine.

# Tại sao chọn cách này

- **Reviewer mới, ngữ cảnh sạch, không thấy vòng một:** đúng như `01-quy-trinh.md` quy định cho vòng 2.
- **Thay hai luật chồng nhau bằng một luật** cho check-downgrade, rồi kiểm trên cả 9 ca của hai vòng trước khi viết test.
- **Duyệt ký tự thay vì regex** cho chuỗi nháy, đối chiếu với Ruby Psych: 27 ca, không xanh giả, không đỏ oan.
- **Sửa ở nguồn chung:** "trả lời child còn nợ báo cáo" luôn đi qua `dispatch`, thay vì vá riêng từng đường.

# Hình dạng production

- Các test chạy nguyên văn code trong `SKILL.md` nay phủ `child_name`, `dispatch`, `dispatch_advisor`, đoạn heartbeat và đoạn `run_gate`. Loop vẫn là văn xuôi: chỉ test được các câu quy tắc, không test được việc orchestrator làm theo.
- `:` và `exit 0` vẫn được `run-gate.sh` chấp nhận (no-op tường minh như `true`).
- `parse_verdict` chưa được thử với tin thật từ `agent_message`: nếu runtime thêm tiền tố trước dòng đầu, mọi verdict sẽ bị từ chối.

# Các cách khác khả thi

1. Bỏ bước 0, để heartbeat tự xoá deadline khi thấy child idle.
2. Dùng parser YAML thật thay vì vòng duyệt ký tự.
3. Chặn cả `:` và `exit 0` trong `run-gate.sh`.

# Tại sao không chọn các cách đó

1. Cách 1 không phân biệt được "child xong" với "child treo": đúng lỗi mà heartbeat tồn tại để bắt.
2. Cách 2 hợp khi frontmatter có khối flow hoặc nhiều dòng phức tạp. Hiện chỉ có giá trị một dòng, và thêm phụ thuộc là chi phí thật.
3. Cách 3 tuỳ tiện: `true` cũng là no-op. Lỗi thật là gate bị comment mất, và cái đó đã chặn.

# Khái niệm cốt lõi cần nắm

- **Bản sửa là mã mới:** nó cần review như mã mới, vì nó thường tạo lỗi ở đường mà người sửa không nghĩ tới.
- **Siết một cổng làm thay đổi tần suất các đường khác:** `parse_verdict` chặt hơn thì đường "gửi lại định dạng" xảy ra nhiều hơn, và mọi lỗ ở đường đó lộ ra.
- **Một luật rõ thay hai luật chồng nhau:** hai luật vá lẫn nhau khó suy luận ca biên hơn một luật.

# Lỗi thường gặp

- Vá đúng ca reviewer đưa ra mà không thử các ca lân cận (hạ sang nhóm mới, chỉ bớt bản).
- Thêm điều kiện chặt ở hàm được gọi mà không đọc lại người gọi (`run_gate` gọi `advance` vô điều kiện).
- Có ghi lại trạng thái cũ rồi khi lỗi thì xoá luôn thay vì khôi phục.

# Ví dụ nhỏ

```python
downgrades({"rand": {"0.8.5", "0.9.0"}}, {"rand": {"0.7.3", "0.9.0"}})
# vòng 1: []   (hạ sang nhóm 0.7 chưa từng có, bị bỏ sót)
# vòng 2: [("rand", "0.8.5", "0.7.3")]
```

# Lần sau nên nghĩ thế nào

1. Sau mỗi đợt sửa, review lại chính đợt sửa bằng một người đọc mới.
2. Khi siết một kiểm tra, liệt kê mọi người gọi và mọi đường "bị từ chối" của nó, rồi kiểm xem đường đó còn đúng không.
3. Khi vá một ca, viết thêm hai ca lân cận trước khi coi là xong.
