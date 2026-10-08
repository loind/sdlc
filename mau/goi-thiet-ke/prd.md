# Giới hạn tốc độ theo khách hàng - PRD

> Mẫu minh hoạ. Ví dụ là một gateway giả định. Thay bằng tính năng của bạn. Chỉ ghi điều người dùng nói cho bạn; thứ có trong repo thì trỏ tới.

Ticket: `<gitlab>/<nhóm>/<repo>#NN`. Ngày: dd/mm/yyyy.

## Vấn đề

Hôm nay một khách hàng gửi quá nhiều request làm chậm mọi khách hàng khác trên cùng gateway. Tuần trước có hai sự cố chậm toàn hệ thống do một khách hàng chạy script lặp. Chưa có cách chặn mà không phải tắt cả đường vào.

- Chặn bằng tay ở proxy phía trước mất khoảng 30 phút và chặn nhầm khách khác dùng chung địa chỉ.
- Không biết khách nào đang tiêu hạn mức vì chưa có số đếm theo khách.

## Người dùng & bên liên quan

- **Team vận hành gateway:** cần một cầu dao tự động, và số liệu để chỉnh hạn mức.
- **Dev backend của các dịch vụ phía sau:** được bảo vệ khỏi tải bất thường, không phải sửa gì.
- **Khách hàng:** nhận mã 429 kèm thời gian chờ, thay vì chậm không rõ lý do.
- **Bị ảnh hưởng mà không yêu cầu:** team dùng kho dữ liệu chung cho bộ đếm. Thêm tải lên nó.

## Tiêu chí thành công

- Khách vượt hạn mức nhận 429 trong vòng 1 giây từ lúc vượt. Khách khác không đổi độ trễ (p95 tăng dưới 5%).
- Metric `rate_limit_rejected_total{tenant}` hiện trên bảng giám sát.
- Bảng hạn mức hỏng làm tiến trình dừng lúc khởi động, không chạy với bảng sai.

## Ngoài phạm vi

- Hạn mức theo từng route (chỉ theo khách hàng).
- Giao diện chỉnh hạn mức. Hạn mức nằm trong file cấu hình nhúng, đổi bằng deploy.
- Chặn theo địa chỉ IP.

## Câu hỏi còn treo

- Hạn mức mặc định cho khách chưa khai báo? **Người trả lời: chủ sản phẩm.** Tạm dùng 600 request/phút (giả định, chưa ai xác nhận: coi là rủi ro).
