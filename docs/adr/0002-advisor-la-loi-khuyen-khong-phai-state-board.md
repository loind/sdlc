# Advisor là lời khuyên trong phase, không phải state board và không chặn phase

Trạng thái: chấp nhận, 10/11/2026. Người dùng đã chốt bốn điểm.

Vai `advisor` chấm dự thảo của engine trước khi engine viết mã. Nếu coi nó như một vòng review hoặc một cổng, nó sẽ làm board phức tạp thêm, ăn vào giới hạn 3 vòng review, và một provider sập sẽ chặn cả phase vì một lời khuyên.

Quyết định:

1. **Advisor không phải state board.** Board vẫn `pending -> engine -> review -> done`. Advisor chạy khi phase ở `engine`, tên `advisor-p<phase>-draft` (không có `-r<vòng>`), không tăng `round`, không tính vào giới hạn 3 vòng review. Điểm của nó không đóng phase và không tự thành vòng sửa.
2. **Advisor lỗi không block phase.** Host từ chối `xhigh`, provider sập, spawn thất bại hoặc im lặng sau lần nhắc: orchestrator gọi `bd.advisor_unavailable`, ghi `advisor unavailable: <lý do>` vào `notes` và board log, rồi báo engine đi tiếp. Không dùng `bd.block` cho advisor.
3. **Chỉ chạy lại advisor khi engine viết dự thảo mới.** Vòng sửa sau qc hoặc code-review FAIL không gửi lại advisor. `bd.advisor_draft` so mã băm nội dung dự thảo nên việc này được ép bằng code, không chỉ bằng lời dặn.
4. **Trần đầu vào.** Dự thảo tối đa 1500 từ, kèm danh sách đầu mục kiểm được và phạm vi đã đọc (file, diff, log). Advisor chỉ đọc thứ engine đưa; thiếu bằng chứng thì ghi `thiếu bằng chứng`, không tự đọc repo trừ path được liệt kê. `bd.advisor_draft` từ chối dự thảo vượt trần.

Chỗ KHÔNG được lệch: bốn điểm trên, và vị trí của advisor (trong phase, trước khi phát triển). Chỉ người dùng được đổi. Muốn đổi thì viết ADR mới và thêm dòng "đã thay bằng ADR-NNNN" ở đây.

## Các phương án đã loại

- **Thêm `advisor` vào state board:** làm `FLOW`, `advance`, `rework` và heartbeat phải biết thêm một trạng thái, trong khi advisor không đóng được phase.
- **Tên có vòng `advisor-p<phase>-r<vòng>`:** buộc advisor đi theo `round`, nên mỗi vòng sửa của reviewer sẽ kéo theo một lần chạy advisor không cần.
- **`bd.block` khi advisor `BLOCKED`:** một lời khuyên không lấy được sẽ chặn công việc mà lời khuyên đó chỉ phục vụ.
- **Chỉ ghi quy tắc "đừng chạy lại" vào tài liệu:** đúng loại quy tắc chỉ nằm trong văn xuôi mà không có gì giữ.

## Hệ quả

- Advisor có thể vắng mặt mà phase vẫn xong. Chất lượng dự thảo khi vắng advisor chỉ còn qc và code-review đỡ.
- Một dự thảo viết lại, dù chỉ đổi một ký tự, được tính là dự thảo mới và chạy lại advisor.
- Model `xai/grok-4.7` được thêm vào `skills/orchestrator/models.json` như một vai riêng. Đây là bổ sung cho bảng model ở ADR-0001, không đổi các vai còn lại. `thinking="xhigh"` được truyền rõ trong `dispatch`.
