# Quy tắc cho agent

## Ngữ cảnh và quyết định (đọc trước mọi việc)

Đọc `CONTEXT.md` (thuật ngữ, phạm vi) và mọi file trong `docs/adr/` trước khi lập kế hoạch hoặc sửa bất cứ thứ gì.
Phát hiện mâu thuẫn với một ADR: dừng lại và báo parent. Không tự lách ADR.

## Quy tắc cho agent

- So hành vi với <hệ thống chuẩn>. Không bao giờ sửa assertion của test cho khớp mã mới.
- Không `git push`, không đẩy tag. Commit sớm, từng bước nhỏ, trên nhánh feature.
- Production chỉ được đọc: chỉ gửi GET, không tạo, sửa hay xoá.
- Dọn đĩa: chỉ được dọn cache build và xoá image Docker của dự án này. Không xoá gì ngoài Docker. Thiếu đĩa: dừng, báo BLOCKED.
- Image chỉ do CI build và push. Build tay thì xoá image cũ sau đó.
- Không thay đổi cụm (`kubectl set image`, xoá, scale) trừ khi việc được giao yêu cầu.
- Gate đầy đủ: `<lệnh gate đầy đủ của repo>`.
- Nâng phụ thuộc: <cách nâng>. Sau mỗi lần cập nhật file khoá: đọc `git diff` của nó, chạy `<cổng chống hạ phiên bản>`.
- KHÔNG tự thêm ngoại lệ vào cổng chặn đang đỏ, kể cả khi việc đó làm build xanh. Ngoại lệ là quyết định của người dùng. Dừng và báo.
- Xong mỗi phase lớn: dọn thư mục build.

## Cập nhật tài liệu (bắt buộc, cùng commit với thay đổi)

- Đổi tên, đổi build/deploy, hoặc đổi quy trình nhánh: cập nhật tài liệu sống trong CÙNG commit. Quyết định mới: ADR mới, không sửa lời văn ADR cũ ngoài việc thêm dòng "đã thay bằng ADR-NNNN".
- Chạy `bash scripts/check-docs.sh`. Khi bỏ một tên hay cách làm: THÊM nó vào danh sách `RETIRED` trong script.
- Hồ sơ lịch sử có ngày (verdict, board, báo cáo phase) KHÔNG sửa đè.
