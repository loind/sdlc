# SDLC harness - quy trình phát triển phần mềm có agent tham gia

Tháng 11/2026. Repo này là bộ tài liệu, mẫu, skill và script để một đội chạy quy trình agent viết mã, kiểm và rà soát. Người dùng repo là đội áp dụng quy trình, và các agent của họ đọc repo này trước khi làm việc.

## Thành phần

**orchestrator**:
Phiên điều phối. Đọc gói thiết kế, giao việc, ghi board, chạy gate, merge. Không tự sửa mã.
_Tránh dùng_: manager, controller.

**child**:
Phiên con do orchestrator giao việc: engine, advisor, qc, code-review, documenter, research, devops, verifier. Giữ tới cuối run, không xoá sau phase (ADR-0001).
_Tránh dùng_: worker, sub-agent.

**advisor**:
Child chấm dự thảo của engine trước khi engine viết mã, tên `advisor-p<phase>-draft`. Không phải state board, không tăng round, không tính vào 3 vòng review. Lỗi thì phase vẫn chạy (ADR-0002).
_Tránh dùng_: reviewer (reviewer chấm diff, không chấm dự thảo).

**phase**:
Đơn vị giao cho một engine. Có `REQ-xxx`, acceptance và lệnh gate riêng. Lấy từ `phases.md` của gói thiết kế.
_Tránh dùng_: step, task (dành cho việc nhỏ hơn).

**gói thiết kế**:
Bốn file `prd.md`, `srs.md`, `design.md`, `phases.md` trong `docs/design/<slug>/`, do skill `thinker` viết.
_Tránh dùng_: spec, plan.

**gate**:
Lệnh chạy thật, xanh khi exit 0, chạy qua `scripts/run-gate.sh`. Reviewer nói PASS không phải gate.
_Tránh dùng_: check, bước kiểm.

**board**:
File JSON ghi trạng thái phase, child, deadline, heartbeat. Chỉ một đường dẫn: `.prime/orchestrator/board.json`. Chỉ orchestrator được ghi.
_Tránh dùng_: state file.

**heartbeat**:
Watchdog 5 phút do `rlm_heartbeat` chạy, kiểm từng child đã giao mà chưa báo cáo cuối. Tắt khi mọi phase `done` và không còn child nào đang chạy.
_Tránh dùng_: cron, poller.

## Phạm vi

**Trong phạm vi**:
Tài liệu quy trình (`01` đến `05`), mẫu trong `mau/`, skill trong `skills/`, script trong `scripts/`.

**Ngoài phạm vi**:
Mã ứng dụng của dự án dùng quy trình này. Nội dung gốc của các skill nguồn bên ngoài (`ponytail`, `ponytail-review`, `tdd`, `code-review`...): giữ nguyên, chỉ frontmatter được đồng đều.

## Chuẩn đúng

**Runtime Prime Agent**:
Tài liệu runtime của bản Prime Agent cài trên máy (`docs/rlm-runtime.md`) là chuẩn cho hành vi của `rlm.spawn`, `agent_message`, `agent_observe`, `rlm_heartbeat`. Tài liệu trong repo lệch runtime thì sửa tài liệu, không đoán.

## Dữ liệu dùng chung

**`skills/orchestrator/models.json`**:
Bảng model theo vai. Skill `orchestrator` đọc file này để chọn model. Không ghi cứng model id ở nơi khác.

**Khung chung của brief**:
Nằm ở ba nơi phải khớp nhau: `FRAME` trong `skills/orchestrator/SKILL.md`, mục "Khung chung" trong `02-vai-tro-va-brief.md`, và các file `mau/brief-*.md`. Sửa một nơi thì sửa cả ba trong cùng commit.

## Số liệu

**Hạn gợi ý cho child**:
engine 45 phút mỗi phase, advisor 20 phút mỗi dự thảo, qc và code-review 20 phút mỗi vòng, devops 20, verifier 30, documenter 20. Deadline luôn là giờ tuyệt đối lấy từ đồng hồ máy.
