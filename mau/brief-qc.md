# Mẫu brief: qc

> Điền mọi chỗ `<...>`. Brief gồm ba khối ghép theo thứ tự: **nhiệm vụ riêng của vai**, **khung chung**, **khối ngôn ngữ**. Gửi cả ba cho child.

## 1. Nhiệm vụ riêng của vai

Vai: qc. CHẤM diff theo đúng acceptance criteria của phase. Không sửa mã. Không commit.

Phase <id>. Commit cần chấm: <SHA> (nhánh <nhánh>). Ghi lại HEAD TRƯỚC và SAU khi chấm.
Yêu cầu: <REQ-ids> trong <design_dir>/srs.md. Mỗi yêu cầu có phương pháp kiểm (Test, Demonstration, Inspection, Analysis). Dùng đúng phương pháp đó, không thay bằng cách rẻ hơn.
Acceptance:
- <REQ-xxx: ...>
- <REQ-yyy: ...>

Việc làm:
1. Chạy gate đầy đủ trên ĐÚNG commit trên qua `GATE_LOG=<file log> scripts/run-gate.sh "<lệnh 1>" "<lệnh 2>"`, mỗi lệnh một đối số, không `|`, `&&`, `;`. Đọc `EXIT=` và `GATE_GREEN`/`GATE_RED` trong log, không kết luận qua `| tail`.
2. Tự kiểm độc lập bằng chương trình thật khi có thể (chạy binary, gửi request, đọc log). Đừng chỉ tin test của engine.
3. Thử các nhánh lỗi, dữ liệu biên, và hồi quy so với hệ thống tham chiếu.
4. Nếu thư mục build dùng chung với reviewer khác: KHÔNG xoá nó. Trước khi chạy trên checkout khác, `touch` file nguồn để cargo/bundler không dùng nhầm bản build cũ.
5. Nếu ticket yêu cầu "không log, không lộ bí mật": quét output thật bằng regex (token dạng JWT, `key=<giá trị không phải ***>`, header Basic, khối PEM). Có thể thêm một bộ phân loại bằng model phụ: ngưỡng 0,5 trở lên là nghi lộ, và bạn PHẢI tự xác minh bằng mắt rồi ghi `file:dòng`.

Báo cáo (dòng đầu DONE, rồi VERDICT):
- `VERDICT: PASS` hoặc `VERDICT: FAIL`.
- Một dòng cho mỗi yêu cầu: `REQ-xxx PASS` hoặc `REQ-xxx FAIL` kèm đúng thứ còn thiếu. Yêu cầu bạn không thực hiện được phương pháp kiểm: FAIL, không phải PASS.
- Phát hiện khác: mức độ (BLOCKER, MAJOR, MINOR, NIT), `file:dòng`, cách sửa ngắn.
- HEAD trước và sau, lệnh đã chạy, điểm chưa chắc.
Bạn không soát phong cách hay cấu trúc mã: reviewer khác làm việc đó.

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
