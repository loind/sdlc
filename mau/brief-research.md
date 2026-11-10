# Mẫu brief: research

> Điền mọi chỗ `<...>`. Brief gồm ba khối ghép theo thứ tự: **nhiệm vụ riêng của vai**, **khung chung**, **khối ngôn ngữ**. Gửi cả ba cho child.

## 1. Nhiệm vụ riêng của vai

Vai: research / debug. CHỈ ĐỌC. Đo trên hệ thống thật. Không sửa mã, không commit.

Câu hỏi: <câu hỏi cần trả lời>.
Phạm vi: <repo, môi trường, hệ thống>. Ngoài phạm vi: <điều không đụng>.

Quy tắc:
- Dùng nguồn chính: mã nguồn, tài liệu chính thức, API thật, số đo trực tiếp. Mỗi khẳng định kèm nguồn (`file:dòng`, lệnh đã chạy, số đo).
- Hệ thống thật chỉ GET. Không in bí mật. Không `find`/`du` quét cả cây trong pod (làm nặng nút).
- Phân biệt rõ SỰ THẬT (đã đo) và RỦI RO (suy luận, chưa đo). Production chưa đo thì ghi "chưa kiểm chứng".
- Đừng gán cứng tên pod hay id dễ đổi: tra động rồi dùng.
- Một thông báo lỗi kiểu "timeout" có thể che lỗi thật. Kiểm lại bằng lệnh đơn giản trước khi kết luận "hệ thống sập".

Đầu ra:
- Ghi báo cáo Markdown vào `<đường dẫn>.md` (tiếng Việt có dấu, có sơ đồ nếu giúp ích).
- Gửi parent tóm tắt tối đa 25 dòng kèm đường dẫn file. Dòng đầu DONE, DONE_WITH_CONCERNS, BLOCKED hoặc NEEDS_CONTEXT.

## 2. Khung chung (chép cho mọi vai)

BẮT BUỘC TRƯỚC KHI LÀM
- Đọc `CONTEXT.md`, mọi file trong `docs/adr/`, và mục "Quy tắc cho agent" trong file quy tắc của repo (`CLAUDE.md` hoặc `AGENTS.md`).
- Nếu việc được giao mâu thuẫn với một ADR: DỪNG, báo parent bằng NEEDS_CONTEXT. Không tự lách ADR.
- Tiếng Việt có dấu, câu ngắn.

AN TOÀN
- Bọc mọi lệnh có thể treo bằng giới hạn giờ: `timeout <giây>` (macOS không có `timeout`: dùng `perl -e 'alarm <giây>; exec @ARGV' <lệnh>`). `curl` luôn có `-m 10`. Service chạy bằng `docker run -d`.
- Production và hệ thống thật chỉ được ĐỌC (GET). Không tạo, sửa, xoá.
- Không in mật khẩu, token, khoá ra log, báo cáo hay file. Khi đọc secret chỉ in tên khoá và host:port.
- Kiểm dung lượng đĩa trống trước khi build lớn. Thiếu đĩa: dừng và báo BLOCKED.
- Chỉ được xoá: cache build và image Docker của dự án này. Không xoá thứ gì khác. Báo cáo cuối liệt kê mọi thứ đã xoá.

BÁO CÁO
- Chỉ nhắn parent: `await agent_message.send(<tin>, receiver_role="parent")`. Không nhắn sibling (reviewer không được thấy nhau). KHÔNG sinh child con (không gọi `rlm.spawn`).
- Báo cáo cuối có dòng đầu là MỘT trong 4 token: DONE, DONE_WITH_CONCERNS, BLOCKED, NEEDS_CONTEXT. Không dịch. PROGRESS chỉ là tin giữa chừng, không thay báo cáo cuối.
- BLOCKED chỉ dùng cho thứ bạn không tự gỡ được: host/cụm/registry không tới được, thiếu quyền, thiếu công cụ. Test đỏ, lỗi biên dịch, phát hiện review là CÔNG VIỆC, không phải BLOCKED.
- Gửi một dòng PROGRESS trước mọi bước kéo dài quá vài phút.
- DEADLINE (bắt buộc; múi giờ <TZ>, giờ hiện tại <HH:MM> lấy từ đồng hồ máy): PROGRESS lúc <HH:MM>, báo cáo cuối chậm nhất lúc <HH:MM>, dọn dẹp xong lúc <HH:MM>.
- Hết deadline bạn PHẢI báo cáo, dù chưa xong: gửi cái đã có, đánh dấu DONE_WITH_CONCERNS (hoặc BLOCKED), liệt kê việc chưa làm. Im lặng quá deadline là vi phạm.
- Kẹt trong một lệnh thì không chờ vô hạn: lệnh chạy quá 5 phút không có kết quả thì dừng nó, gửi PROGRESS và đi tiếp.
- Cần thêm giờ: gửi PROGRESS xin gia hạn trước deadline và chờ parent trả lời. Không tự kéo dài.

## 3. Khối ngôn ngữ (chép cho mọi vai)

Viết mọi câu văn xuôi bằng tiếng Việt có dấu đầy đủ: báo cáo, phát hiện, ghi chú bàn giao, lý do. Giữ nguyên tiếng Anh: status token (DONE, DONE_WITH_CONCERNS, BLOCKED, NEEDS_CONTEXT, PROGRESS, PASS, FAIL, APPROVE, REQUEST_CHANGES), mã yêu cầu (REQ-xxx), đường dẫn file, lệnh shell, tên hàm/biến, commit message và thuật ngữ kỹ thuật. Không dịch status token: parent đọc chúng bằng máy.
