# Nhiệm vụ

Tự đánh giá lại toàn bộ phần đã làm (gate, board, các script kiểm, skill orchestrator, tài liệu) rồi đẩy bản sửa lên `main`.

# Đã sửa gì

- `scripts/run-gate.sh`: từ chối khi không có lệnh, lệnh rỗng, lệnh có xuống dòng, `TIMEOUT_SEC` không phải số giây dương. Thêm `tests/test_run_gate.py`.
- `scripts/check-downgrade.py`: tính đường dẫn theo gốc repo (chạy từ thư mục con không còn bỏ qua file); so thêm theo từng nhóm major (`syn 1.x` bị hạ khi `2.x` giữ nguyên).
- `scripts/check-skills.py`: bắt nháy kép lồng chưa escape, nháy không đóng, giá trị bắt đầu bằng ký tự dành riêng của YAML, thư mục skill thiếu `SKILL.md`.
- `scripts/check-pins.sh`: quét thêm `uv.lock`, `poetry.lock`, `yarn.lock`, `pnpm-lock.yaml`, `Pipfile`, `Pipfile.lock`, `Dockerfile`.
- `board.py`: `advance` tin exit code thay vì `ok` và bắt chạy đủ gate đã cấu hình; dừng khi chạy với `python -O`; file tạm riêng cho mỗi lần ghi; `parse_verdict` bắt dòng đầu `DONE` và bỏ qua code fence; CLI chỉ nhận `demo`. Thêm `tests/test_board_cli.py`.
- `skills/orchestrator/SKILL.md`: Loop bước 0 gọi `bd.clear_deadline` cho mọi báo cáo cuối; `dispatch` xoá deadline khi spawn lỗi; `child_name` dừng với vai lạ thay vì trả tên engine.
- `01`, `02`: ngoại lệ advisor ở dòng `BLOCKED` và thang heartbeat; dòng `PROGRESS` nói tới `DRAFT:`.
- Siết test chỉ kiểm chuỗi con (`test_engine_ponytail`, `test_role_contracts`).

# Vấn đề thực sự

Phần lớn lỗi cùng một loại: **cổng báo xanh khi đầu vào lạ**. Không có lệnh nào, lệnh rỗng, chạy từ thư mục con, file khoá không quét tới, giá trị YAML có nháy lồng, phản hồi `BLOCKED` có dòng `VERDICT: PASS`. Mỗi cổng đã được kiểm với đầu vào "bình thường", và mutation test chỉ chứng minh test bắt được đột biến của chính code đã viết, không chứng minh đã nghĩ đủ loại đầu vào.

Thêm một lỗi đúng đắn lớn: Loop không bao giờ xoá deadline, nên heartbeat không thể tắt và advisor chạy xong vẫn bị đánh dấu unavailable sau 20 phút.

# Tại sao chọn cách này

- **Giao review mã cho một reviewer có ngữ cảnh sạch.** Nó tìm 13 phát hiện kèm ca đã chạy, trong đó nhiều ca tôi không nghĩ tới vì đã quen cách mình viết.
- **Mỗi phát hiện được chứng minh hai lần:** test mới đỏ trên bản cũ (ví dụ `test_run_gate.py` đỏ đúng 6 ca trên `run-gate.sh` của `main`), và mutation test trên bản sửa.
- **Đối chiếu `check-skills` với parser YAML thật (Ruby Psych).** Không có ca nào Ruby báo lỗi mà checker cho qua. Ba ca checker nghiêm hơn (`a # b`, `&anchor v`, `!tag v`) là chủ đích vì chúng âm thầm đổi giá trị.

# Hình dạng production

- CI trên GitHub đã chạy thật cho cả 5 lần push trước đó, đều xanh. Lần push này sẽ là lần đầu chạy 13 lệnh gate.
- `check-tags.sh` vẫn tốn vài lần fork mỗi tag (khoảng 50 giây cho 2000 tag), đã ghi `shortcut:` trong code.
- `qc2` và `research` có trong tài liệu nhưng orchestrator chưa hỗ trợ; nay `child_name` dừng rõ ràng thay vì gửi nhầm cho engine. Thêm `qc2` cần chọn model khác họ với qc, là quyết định của người dùng.

# Các cách khác khả thi

1. Dùng parser YAML thật (PyYAML) thay cho checker tự viết.
2. Viết lại `check-tags.sh` bằng một lệnh awk ngay bây giờ.
3. Hỗ trợ luôn `qc2` với một model mặc định.

# Tại sao không chọn các cách đó

1. Cách 1 thêm phụ thuộc mà repo đang không cần (máy dev không có PyYAML). Hợp khi frontmatter phức tạp hơn (khối flow lồng nhau).
2. Cách 2 hợp khi repo dùng thật có nhiều nghìn tag. Hiện chưa có số đo thật nào ở cỡ đó.
3. Cách 3 tự quyết thay người dùng một điều tài liệu yêu cầu rõ (model khác họ với qc).

# Khái niệm cốt lõi cần nắm

- **Xanh giả là lỗi đắt nhất của một cổng:** một cổng đỏ nhầm tốn vài phút, một cổng xanh nhầm làm hỏng thứ đã ship.
- **Mutation test có giới hạn:** nó đo chất lượng test so với code đang có, không đo việc đã nghĩ đủ loại đầu vào chưa.
- **Review độc lập:** người đọc không neo vào cách nghĩ của tác giả tìm được loại lỗi tác giả không thấy.

# Lỗi thường gặp

- Cổng chỉ thử với đầu vào điển hình: không thử "không có gì", "rỗng", "chạy ở chỗ khác", "ký tự lạ".
- Tin trường `ok` do caller khai thay vì exit code thật.
- Dùng `assert` cho kiểm tra quan trọng mà không chặn `python -O`.
- Quy tắc trong tài liệu (xoá deadline khi child báo cáo xong) mà không có bước nào trong Loop làm việc đó.
- Grep DoD theo từ khoá ("advisor") nên bỏ sót câu quy tắc chung không nhắc từ khoá đó.

# Ví dụ nhỏ

```bash
scripts/run-gate.sh                     # trước: GATE_GREEN all 0, exit 0. Nay: REJECT, exit 2
scripts/run-gate.sh $'false\ntrue'      # trước: EXIT=0, xanh. Nay: REJECT, exit 2
```

# Lần sau nên nghĩ thế nào

1. Với mỗi cổng, liệt kê đầu vào "lạ" trước khi viết: không có, rỗng, sai chỗ, sai định dạng, ký tự đặc biệt. Mỗi cái phải đỏ hoặc exit 2.
2. Sau khi tự kiểm, nhờ một người đọc độc lập trước khi coi là xong.
3. Mỗi quy tắc trong tài liệu phải có một bước trong quy trình thực hiện nó, và một test kiểm bước đó.
