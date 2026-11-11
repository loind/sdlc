# Nhiệm vụ

Nâng skill `ponytail` (và `ponytail-review`) trong repo lên bản mới nhất, đồng thời đánh giá các agent của quy trình có cần đổi để đối ứng không.

# Đã sửa gì

- `skills/ponytail/SKILL.md`: `argument-hint` từ `[lite|full|ultra]` thành `[lite|full|ultra|off]`. Dòng `compatibility` của repo được giữ.
- `skills/ponytail-review/SKILL.md`: không đổi (giống hệt upstream v5.3.3).
- `skills/README.md`, `04-tai-lieu-cho-agent.md`: nhãn phiên bản 5.1.0 thành 5.3.3, ghi rõ nguồn và phần nào đã đổi.

# Vấn đề thực sự

"Nâng cấp lên bản mới nhất" dễ bị hiểu là có nhiều thứ phải đổi. Thực tế repo này chỉ chứa `SKILL.md` của hai skill. Phần lớn thay đổi 5.1.1 đến 5.3.3 nằm ngoài đó: hook, band và ledger của plugin Claude Code, cache bản đồ codebase, các nền tảng khác (OpenCode, Cursor, pi, Hermes), và các skill phụ mà repo không chứa.

# Tại sao chọn cách này

- **Xác định bản mới nhất từ upstream, không từ cache:** `git ls-remote --tags` cho `v5.3.3`, và `plugin.json` ở `main` cũng là 5.3.3. Bản marketplace cục bộ đang ở đúng HEAD upstream (`96608e0`).
- **So từng byte với các tag:** sau khi bỏ dòng `compatibility`, `ponytail-review` giống hệt v5.1.0, v5.1.1 và v5.3.3. `ponytail` giống v5.1.0 và v5.1.1, chỉ khác v5.3.3 đúng một dòng. Vì vậy "nâng cấp" thực chất là một dòng frontmatter.
- **Copy từ upstream rồi chèn lại `compatibility`** thay vì sửa tay, để đảm bảo giống upstream.

# Hình dạng production

- `~/.agents/skills/ponytail*` là symlink vào repo, nên bản mới có hiệu lực khi nhánh này nằm trên nhánh đang checkout.
- Plugin Claude Code `ponytail@ponytail` đã ở 5.3.3 sẵn, không cần làm gì thêm. Hook và band của nó chỉ chạy trong Claude Code, không chạy trong Prime Agent.

# Các cách khác khả thi

1. Cài lại cả plugin upstream vào repo (kèm hook, lệnh, các skill phụ).
2. Không đổi gì, chỉ ghi chú "tương đương 5.3.3".
3. Tự động hoá: script so repo với tag upstream và báo lệch.

# Tại sao không chọn các cách đó

1. Cách 1 kéo theo hook và code chạy trong Claude Code vào một repo chỉ chứa skill tài liệu, trái với phạm vi trong `CONTEXT.md`. Hợp khi repo là bản phân phối plugin.
2. Cách 2 để `argument-hint` lệch: người dùng không thấy tham số `off` mà upstream đã hỗ trợ.
3. Cách 3 hợp khi nâng cấp xảy ra thường xuyên. Mới chỉ có hai file, nên chưa đáng.

# Khái niệm cốt lõi cần nắm

- **Phiên bản của plugin khác phiên bản của file bạn đang giữ:** version 5.3.3 mô tả cả gói. File `SKILL.md` có thể không đổi qua nhiều bản.
- **Đối chiếu nội dung, không tin nhãn:** nhãn "5.1.0" trong docs không chứng minh nội dung đang là 5.1.0.
- **`rg -c` không in gì khi 0 khớp:** một chuỗi rỗng ở kết quả so sánh nghĩa là "không khác", nhưng dễ đọc nhầm thành "lỗi".

# Lỗi thường gặp

- Coi cache plugin là "mới nhất" mà không hỏi upstream.
- Sửa tay một skill bên thứ ba rồi lệch byte với bản gốc.
- Ghi nhãn phiên bản vào docs mà không nói phần nào của gói thực sự nằm trong repo.
- Kết luận "agent không cần đổi" chỉ vì skill không đổi, mà không đối chiếu brief với đầu ra thật của skill. Lần này phát hiện lệch hợp đồng verdict của vai code-review có từ trước (xem bàn giao).

# Ví dụ nhỏ

```bash
git ls-remote --tags --sort=-v:refname https://github.com/DietrichGebert/ponytail.git | head -1
# 7801d06...  refs/tags/v5.3.3
curl -m 10 -sf https://raw.githubusercontent.com/DietrichGebert/ponytail/v5.3.3/skills/ponytail/SKILL.md -o up.md
diff <(grep -v '^compatibility:' skills/ponytail/SKILL.md) up.md    # chỉ khác argument-hint
```

# Lần sau nên nghĩ thế nào

1. Hỏi upstream (tag, `main`) trước, rồi so nội dung từng file với tag, rồi mới nói "đổi gì".
2. Tách rõ phần nào của bản phát hành nằm trong repo của mình, phần nào không.
3. Khi đánh giá tác động lên agent, đọc đầu ra thật của skill và đối chiếu với brief, không dừng ở "skill không đổi".
