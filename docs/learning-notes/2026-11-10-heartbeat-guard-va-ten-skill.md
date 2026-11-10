# Nhiệm vụ

Sửa ba khoảng trống tìm thấy khi kiểm "orchestration giao việc kèm deadline và bật heartbeat 5 phút": `WATCH_INSTRUCTION` chưa được định nghĩa, không có gì ép heartbeat tồn tại trước khi giao việc, và tên skill khi gọi bị lệch.

# Đã sửa gì

- `skills/orchestrator/SKILL.md`: định nghĩa `WATCH_INSTRUCTION` thành chuỗi cụ thể (kèm thang xử lý), thêm `assert` heartbeat vào đầu `dispatch()`, thêm bước "start the heartbeat" vào cuối mục Gate verification.
- `skills/thinker/SKILL.md`, `skills/thinker/references/builder-check.md`: `/orchestration` thành `/skill:orchestrator`. Ở `orchestrator/SKILL.md`, `/thinker` thành `/skill:thinker`.
- `scripts/check-docs.sh`: thêm `/orchestration` vào `RETIRED`.
- `tests/test_skill_snippets.py`: chạy nguyên văn đoạn code heartbeat và `dispatch` trong `SKILL.md`, đã nối vào `gate.yml` và `CLAUDE.md`.

# Vấn đề thực sự

Một quy tắc chỉ nằm trong văn xuôi thì không có gì giữ nó. Đoạn code `rlm_heartbeat.create(WATCH_INSTRUCTION, ...)` tham chiếu một biến không tồn tại, nên chạy nguyên văn sẽ lỗi `NameError`. Còn "bật heartbeat trước khi giao việc" chỉ là một câu dặn: bỏ qua nó thì `dispatch` vẫn giao việc, và child chạy không ai canh.

Tên skill cũng là một dạng lệch với runtime: tài liệu Prime Agent nói skill được gọi bằng `/skill:name`, còn skill chép `/orchestration` (tên không tồn tại trong repo này).

# Tại sao chọn cách này

- **`WATCH_INSTRUCTION` tự chứa toàn bộ thang xử lý:** một lượt heartbeat không cần `SKILL.md` còn nằm trong context. Điều này quan trọng khi context bị nén.
- **`assert` ở đầu `dispatch`, trước khi ghi deadline:** bị từ chối thì không để lại dấu vết nào trên board. Một đột biến "đặt guard sau `set_deadline`" bị test bắt.
- **Test chạy nguyên văn đoạn code trích từ tài liệu**, nên sửa tài liệu thành sai là test đỏ. Mutation check: 10/10 đột biến bị bắt (bỏ guard, đổi `interval`, đổi `delivery_mode`, thiếu quy tắc "không xoá child", brief mất `FRAME`...).
- **Dạng gọi lấy từ docs đã cài**, không đoán: `docs/skills.md` của Prime Agent, mục "Skills register as `/skill:name` commands".

# Hình dạng production

- Heartbeat: `interval="5m"` và `delivery_mode="follow_up"` (chờ lượt hiện tại xong, không ngắt giữa chừng). Cả hai đã đối chiếu với skill `rlm-heartbeat` của Prime Agent. Chưa chạy heartbeat end-to-end trên kernel thật.
- Guard nằm trong đoạn code mẫu của skill. Nó chỉ có tác dụng khi orchestrator dùng đúng `dispatch()`. Chưa có cơ chế ép ở phía runtime.

# Các cách khác khả thi

1. `WATCH_INSTRUCTION` chỉ trỏ về skill ("làm theo mục Heartbeat trong skill `orchestrator`").
2. Đưa guard vào `board.py` thành helper (ví dụ `require_heartbeat`) thay vì `assert` trong đoạn code mẫu.
3. Chỉ sửa văn xuôi và để reviewer kiểm.

# Tại sao không chọn các cách đó

1. Cách 1 ngắn hơn, nhưng phụ thuộc skill còn trong context ở mỗi lượt heartbeat. Hợp khi context ổn định và skill luôn được nạp lại.
2. Cách 2 hợp khi có nhiều chỗ giao việc ngoài `dispatch`. Hiện chỉ có một chỗ, nên một `assert` là đủ và ít code hơn.
3. Cách 3 chính là cách đã để lọt `NameError` vào tài liệu.

# Khái niệm cốt lõi cần nắm

- **`delivery_mode`:** `steer` (mặc định) ngắt lượt đang chạy, `follow_up` chờ lượt xong. Watchdog của orchestrator nên dùng `follow_up`.
- **Guard trước side effect:** kiểm điều kiện trước khi ghi bất cứ thứ gì, để bị từ chối thì không để lại trạng thái dở.
- **Test = tài liệu:** trích code từ chính file tài liệu rồi chạy nó. Trôi lệch giữa tài liệu và hành vi sẽ lộ ra ngay.
- **Top-level await:** `compile(..., flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)` cho phép chạy đoạn code kiểu kernel trong test.

# Lỗi thường gặp

- Dặn trong văn xuôi "phải làm X trước Y" mà không có gì kiểm.
- Tham chiếu một biến (`WATCH_INSTRUCTION`) chỉ được mô tả, không được định nghĩa.
- Đề xuất dạng gọi skill theo trí nhớ (`/orchestrator`) thay vì đọc docs. Dạng đúng là `/skill:orchestrator`.
- Một mẫu mutation khớp hai chỗ (cả code lẫn đoạn văn) thì harness phải từ chối chạy. Đó là hành vi đúng: thu hẹp mẫu.

# Ví dụ nhỏ

```python
async def dispatch(role, phase, brief, board):
    assert board.get("heartbeat"), "start the heartbeat first (see Heartbeat and deadlines)"
    name = child_name(role, phase)
    due = bd.set_deadline(board, name, BUDGET_MIN[role])   # chỉ ghi board khi đã qua guard
```

# Lần sau nên nghĩ thế nào

1. Mỗi quy tắc "phải làm trước khi giao việc" cần một điểm kiểm trong code, không chỉ một câu trong tài liệu.
2. Mỗi biến trong đoạn code mẫu phải được định nghĩa trong chính tài liệu, và có test chạy nó.
3. Dạng gọi lệnh, tên API: đọc từ docs của bản đang cài trước khi viết hoặc đề xuất.
