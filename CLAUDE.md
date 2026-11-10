# Quy tắc cho agent

## Ngữ cảnh và quyết định (đọc trước mọi việc)

Đọc `CONTEXT.md` (thuật ngữ, phạm vi) và mọi file trong `docs/adr/` trước khi lập kế hoạch hoặc sửa bất cứ thứ gì.
Phát hiện mâu thuẫn với một ADR: dừng lại và báo parent. Không tự lách ADR.

## Quy tắc cho agent

- So hành vi của `rlm.spawn`, `agent_message`, `agent_observe`, `rlm_heartbeat` với tài liệu runtime của Prime Agent (`CONTEXT.md`, mục Chuẩn đúng). Không đoán cú pháp. Không sửa test hay self-test cho khớp mã mới.
- Không `git push`, không đẩy tag. Commit sớm, từng bước nhỏ, trên nhánh `feature/<ticket>-<slug>`. Không commit thẳng `develop`, `test`, `master`.
- Production chỉ được đọc: chỉ gửi GET, không tạo, sửa hay xoá.
- Dọn đĩa: chỉ được dọn cache build và xoá image Docker của dự án này. Không xoá gì ngoài Docker. Thiếu đĩa: dừng, báo BLOCKED.
- Không in mật khẩu, token, khoá ra log, báo cáo hay file.
- KHÔNG tự thêm ngoại lệ vào cổng chặn đang đỏ, kể cả khi việc đó làm build xanh. Ngoại lệ là quyết định của người dùng. Dừng và báo.

## Gate

- Gate đầy đủ: `scripts/run-gate.sh "bash scripts/check-docs.sh --self-test" "bash scripts/check-docs.sh" "python3 skills/orchestrator/scripts/board.py demo"`. CI chạy đúng lệnh này (`.github/workflows/gate.yml`).
- Mọi gate chạy qua `scripts/run-gate.sh`, mỗi lệnh gate là một đối số: `GATE_LOG=<file log> scripts/run-gate.sh "<lệnh 1>" "<lệnh 2>"`.
- Mỗi gate là một lệnh đơn. Cấm `|`, `&&`, `;` và `&` trong lệnh gate. Pipe che exit code của lệnh đỏ. Script từ chối với exit 2.
- Đỏ thì dừng. Gửi parent lệnh và output trong log. Không kết luận qua `| tail` hay `| head`.

## Child và primitive (ADR-0001)

- Giữ child tới cuối run. Không gọi `rlm.delete_subagent` khi phase xong.
- Giao việc bằng `rlm.spawn` hoặc `agent_message.send`, ghi board, kết thúc lượt, chờ tin. Không chờ kết quả như một giá trị trả về.
- Child chỉ nhắn parent và không sinh child con. Đây là luật trong brief, không phải giới hạn của nền tảng.
- Báo cáo cuối của child có dòng đầu là một trong bốn token `DONE`, `DONE_WITH_CONCERNS`, `BLOCKED`, `NEEDS_CONTEXT`. Không dịch token.
- Deadline luôn là giờ tuyệt đối lấy từ đồng hồ máy. Heartbeat 5 phút chạy từ lúc khởi tạo tới khi không còn child nào chưa báo cáo.

## Cập nhật tài liệu (bắt buộc, cùng commit với thay đổi)

- Đổi tên, đổi build/deploy, hoặc đổi quy trình nhánh: cập nhật tài liệu sống trong CÙNG commit. Quyết định mới: ADR mới, không sửa lời văn ADR cũ ngoài việc thêm dòng "đã thay bằng ADR-NNNN".
- Khung chung của brief nằm ở ba nơi (`FRAME` trong `skills/orchestrator/SKILL.md`, `02-vai-tro-va-brief.md`, `mau/brief-*.md`). Sửa một nơi thì sửa cả ba.
- Khi bỏ một tên hay cách làm: THÊM nó vào `RETIRED` trong `scripts/check-docs.sh`, rồi sửa mọi chỗ còn sót. Sửa script này thì sửa cả bản mẫu `mau/check-docs-mau.sh`.
- Hồ sơ lịch sử có ngày (verdict, board, báo cáo phase) KHÔNG sửa đè.
