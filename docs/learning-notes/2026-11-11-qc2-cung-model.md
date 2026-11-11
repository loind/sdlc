# Nhiệm vụ

Người dùng chốt: hai qc dùng cùng model. Đưa `qc2` vào orchestrator (trước đó tài liệu có nhắc nhưng skill không hỗ trợ) và sửa các chỗ đang ghi "model khác họ với qc".

# Đã sửa gì

- `skills/orchestrator/SKILL.md`: `qc2` có trong `child_name` (tên `qc2-p<phase>-r<vòng>`), `BUDGET_MIN`, tuple `pick()`, bảng vai và prompt vai riêng. Loop dispatch cả `qc`, `qc2`, `code-reviewer`, chờ đủ ba verdict, và ba bên phải đạt mới chạy gate.
- `models.json`: cố ý không có mục `qc2`, nên `qc` và `qc2` cùng lấy model mặc định `claude-sonnet-5-5`.
- `01`, `02`, `mau/brief-qc2.md`, `skills/README.md`: ghi "cùng model với qc (người dùng chốt 11/11/2026)". Ghi chú đo lường cũ ở `02` được giữ nguyên làm lịch sử, chỉ thêm mục "Chốt".
- Test: `child_name("qc2")`, hợp đồng verdict của qc2 ở ba nơi, `models.json` không ghim qc2 khác qc.

# Vấn đề thực sự

`qc2` nằm trong tài liệu nhưng orchestrator không biết tới. Gọi `dispatch("qc2")` sẽ `KeyError`, và trước đợt sửa vòng một còn có thể bị đặt tên trùng engine.

# Tại sao chọn cách này

- **Không thêm mục `qc2` vào `models.json`** để "cùng model" là cấu trúc, không phải hai dòng phải giữ khớp. Test chặn việc ai đó ghim qc2 sang model khác.
- **Độc lập đến từ phiên riêng và brief khác:** qc2 không thấy báo cáo của qc, ưu tiên nhánh lỗi, dữ liệu biên, hồi quy, lộ bí mật.
- **qc2 chạy mỗi phase:** "2 qc" nghĩa là luôn có hai qc. Trước đây tài liệu ghi "nếu dùng".

# Hình dạng production

Mỗi vòng review tốn thêm một phiên Sonnet. Hai qc cùng model có thể chia sẻ điểm mù của model: ghi chú đo lường cũ ở `02` cho thấy qc2 khác họ từng bắt được lỗi qc bỏ sót. Đó là đánh đổi người dùng đã chọn.

# Các cách khác khả thi

1. Thêm mục `qc2` trong `models.json` trỏ cùng id với qc.
2. Giữ qc2 là tuỳ chọn mỗi run (ghi trên board).

# Tại sao không chọn các cách đó

1. Cách 1 tạo hai dòng phải giữ khớp tay. Hợp khi muốn đổi model của qc2 độc lập về sau.
2. Cách 2 thêm một cờ cấu hình chưa ai cần. Hợp khi có run nhỏ muốn tiết kiệm chi phí review.

# Khái niệm cốt lõi cần nắm

- **Mặc định là cấu trúc, không phải bản sao:** để hai vai dùng chung giá trị mặc định thay vì chép giá trị ra hai nơi.
- **Độc lập của reviewer** đến từ ngữ cảnh sạch và nhiệm vụ khác, không chỉ từ model khác.

# Lỗi thường gặp

- Thêm vai vào tài liệu mà quên `child_name`, `BUDGET_MIN`, `pick()` và Loop.
- Đổi quyết định mà sửa đè ghi chú đo lường cũ, làm mất lý do của lúc đó.

# Ví dụ nhỏ

```text
dispatch("qc",  phase 2) -> spawn qc-p2-r1  model anthropic/claude-sonnet-5-5
dispatch("qc2", phase 2) -> spawn qc2-p2-r1 model anthropic/claude-sonnet-5-5
```

# Lần sau nên nghĩ thế nào

1. Thêm một vai: kiểm đủ tên, ngân sách, model, prompt, Loop, verdict, rồi mới sửa tài liệu.
2. Khi người dùng đảo một khuyến nghị cũ, giữ lý do cũ và thêm mục "Chốt" có ngày.
