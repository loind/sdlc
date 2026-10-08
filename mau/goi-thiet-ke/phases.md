# Giới hạn tốc độ theo khách hàng - Phases

> Heading và key tiếng Anh (`Goal`, `Gate`, `Phase N`, `Requirements`, `Acceptance`, `Depends on`, `Notes`) là hợp đồng với orchestrator: giữ nguyên. Nội dung viết bằng ngôn ngữ của đội.

**Goal:** Gateway giới hạn tốc độ theo khách hàng: vượt hạn mức thì trả 429, số đếm dùng chung giữa các pod qua kho dữ liệu chung.

**Gate (every phase):** rẻ nhất trước. Mỗi dòng một lệnh, không nối bằng `&&`.
```
cargo fmt --all --check
cargo clippy --all-targets --locked -- -D warnings
cargo test --locked
```

## Phase 1 - Bộ đếm cửa sổ trượt (module độc lập)
- **Requirements:** REQ-001, REQ-002
- **Acceptance:**
  - REQ-001: Test - bộ đếm trả đúng số request trong cửa sổ 60 giây; 6 ca biên trong `rate_window_test`.
  - REQ-002: Test - hai pod đếm chung một khoá; số đếm không lệch quá 1 (cần kho thật, `#[ignore]`).
- **Gate:** `cargo test --locked --test rate_window_test`
- **Depends on:** none
- **Notes:** gate hiện đỏ: không tìm thấy `rate_window_test` (module chưa có). Phase này cũng đo tải kho dữ liệu chung (giả định không có chủ).

## Phase 2 - Móc vào luồng request, trả 429 kèm Retry-After
- **Requirements:** REQ-003, REQ-004
- **Acceptance:**
  - REQ-003: Test - vượt hạn mức trả 429; trong hạn mức giữ nguyên hành vi cũ, so với hệ thống chuẩn.
  - REQ-004: Test - 429 có header `Retry-After` đúng số giây còn lại.
- **Gate:** `cargo test --locked --test rate_limit_hook_test`
- **Depends on:** Phase 1
- **Notes:** gate hiện đỏ: test chưa có. Header phải GHI ĐÈ (không thêm) nếu hệ thống chuẩn ghi đè.

## Phase 3 - Cấu hình hạn mức, metric và log khởi động
- **Requirements:** REQ-005, REQ-006
- **Acceptance:**
  - REQ-005: Inspection - bảng hỏng hoặc rỗng làm tiến trình dừng khi khởi động, log nêu tên file và lý do.
  - REQ-006: Demonstration - `rate_limit_rejected_total{tenant}` tăng khi có 429 trên cụm test.
- **Gate:** `cargo test --locked --test rate_config_test`
- **Depends on:** Phase 2
- **Notes:** có deploy lên cụm test (Demonstration), nên chạy MỘT mình, không song song với phase khác cùng deploy. Ghim tag thư viện theo luật nhánh. Một build CI một lúc.
