# Giữ child tới cuối run và dùng đúng primitive của Prime Agent

Trạng thái: chấp nhận, 10/11/2026. Người dùng đã chốt.

Skill `orchestrator` bản gốc bắt xoá child sau mỗi phase, còn `01-quy-trinh.md` cấm xoá: hai tài liệu mâu thuẫn nhau. Ví dụ trong skill còn gọi `await rlm(...)`, trong khi kernel Prime Agent báo `'rlm' is not callable`.

Quyết định:

1. **Giữ child tới cuối run.** Không gọi `rlm.delete_subagent` khi phase xong. Người dùng muốn thấy mọi agent đã tham gia; vết nằm ở file verdict và ticket.
2. **Giữ bộ primitive của Prime Agent:** `rlm.spawn`, `agent_message.send`, `agent_observe.get_agent` cùng `recent_messages`, và `rlm_heartbeat` chu kỳ 5 phút. Spawn là fire-and-forget: giao việc, ghi board, kết thúc lượt, chờ tin.
3. **Giữ bảng model gốc:** engine `deepseek-v4-flash`, documenter `gemini-3.8-flash`, các vai còn lại `claude-sonnet-5-5`. Bảng nằm ở `skills/orchestrator/models.json`. Resolver khớp exact id qua `rlm.find_models`, không lấy phần tử đầu.

Chỗ KHÔNG được lệch: ba điều trên. Chỉ người dùng được đổi. Muốn đổi thì viết ADR mới và thêm dòng "đã thay bằng ADR-NNNN" ở đây.

## Bằng chứng

> The `rlm` object itself is not callable, and the old `rlm.run` attribute is gone; both raise an error naming `rlm.spawn`.
>
> — nguồn: `docs/rlm-runtime.md` trong bản Prime Agent 0.9.8 cài trên máy (`~/.local/share/prime-agent/releases/0.9.8-*/docs/rlm-runtime.md`)

> The default maximum depth is 2, so root sessions may create children and grandchildren; grandchildren may not create another generation unless the limit is configured higher.
>
> — nguồn: cùng file

## Các phương án đã loại

- **Xoá child sau mỗi phase (skill bản gốc):** mất khả năng quan sát. Người dùng không thấy ai đã làm gì, và heartbeat không còn child để kiểm.
- **`await rlm(...)` hoặc `rlm.run`:** kernel từ chối cả hai.
- **`rlm.find_models(...)[0]`:** theo ghi chú gốc trong skill (chưa kiểm lại khi viết ADR này), thứ tự kết quả không phải mới nhất trước: query `sonnet` ra nhiều bản và phần tử đầu là 4.5. Child sẽ chạy model cũ mà board không ghi gì.

## Hệ quả

- Child nhàn rỗi tích lại tới hết run. Tên child duy nhất theo phase và vòng, nên không đụng nhau.
- "Child không sinh child" chỉ là luật trong brief (`FRAME` của skill `orchestrator`). Mặc định nền tảng cho phép child sinh grandchild, nên không được coi luật này là giới hạn cứng.
- `rlm.find_models` mặc định `limit=8` có thể cắt mất bản cần chọn. Resolver truyền `limit=50` và dừng nếu không thấy đúng một bản.
