# Mẫu comment nhật ký ticket

> Orchestrator ghi một comment ở MỖI MỐC (xem `01-quy-trinh.md`, mục "Nhật ký ticket").
> Không chứa bí mật. Có giờ. Tiếng Việt có dấu. Liên kết chéo với ticket các repo khác.

## Mốc 1 - Mở việc

```markdown
**Nhật ký phase <N> (orchestrator, dd/mm/yyyy)**

- 09:10 Mở việc. Ticket: <repo>#<NN>. Nhánh: `feature/<NN>-<slug>`. Worktree: `<đường dẫn>`.
- Model: engine `<model>`, qc `<model>`, qc2 `<model>`, code-review `<model>`.
- Gói thiết kế: `docs/design/<slug>/`. Gate chung xanh trên cây sạch (<lệnh>, exit 0).
```

## Mốc 2 - engine DONE

```markdown
- 10:42 engine DONE. HEAD `<sha>`, <k> commit. Test trước: <a> pass; sau: <b> pass (<b-a> test mới).
```

## Mốc 3 - Mỗi vòng review

```markdown
- 11:20 Review vòng <r> (HEAD `<sha>`):
  - qc: FAIL. REQ-002 thiếu: <điều thiếu> (`file:dòng`).
  - qc2: PASS. Ghi nhận MINOR: <...>.
  - code-review: REQUEST_CHANGES. MAJOR: <...> (`file:dòng`).
  - Khác biệt giữa reviewer: <ghi lại>.
```

## Mốc 4 - Sửa (rework)

```markdown
- 12:05 Gửi engine cả ba phản hồi trong một tin. engine DONE, HEAD mới `<sha>`.
```

## Mốc 5 - Gate

```markdown
- 12:30 Gate (chạy một mình, đúng chuỗi CI):
  - `<lệnh 1>` -> exit 0
  - `<lệnh 2>` -> exit 0, <n> test pass, <m> ignored (đã chạy riêng)
```

## Mốc 6 - Phát hành

```markdown
- 14:00 MR !<số> merge vào `test` (commit `<sha>`). CI build #<số> SUCCESS. Tag `TEST-<n>`.
- 16:30 (sau THÔNG BÁO) merge vào `develop`. Release `release/<YYYY.MM.DD>` -> `master`. CI build #<số>, tag `MASTER-<n>` (commit `<sha>`).
```

## Mốc 7 - Chặn hoặc quyết định của người dùng

```markdown
- 15:10 BLOCKED: <lệnh> -> <lỗi ngắn>. Cần: <điều cần từ ngoài>.
- 15:40 Người dùng quyết: <quyết định>. Lý do: <ngắn>.
```

## Tổng kết (trước khi đóng ticket)

```markdown
**Tổng kết (dd/mm/yyyy)**
- Đã phát hành: tag `MASTER-<n>`, image `<registry>/<tên>:MASTER-<n>`.
- Phase: 3/3 done. Số vòng review: <r1>, <r2>, <r3>.
- Ticket phụ (MINOR/NIT không chặn): #<NN>, #<MM>.
- Việc còn lại: <hoặc "không">.
```
