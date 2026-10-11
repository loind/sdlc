# 02 - Vai trò và mẫu brief

## Nguyên tắc

- **Mỗi vai một phiên.** Người viết, người chấm và người soát là ba phiên khác nhau. Một phiên được hỏi hai câu khác nhau sẽ trả lời câu dễ hai lần.
- **Reviewer luôn là phiên mới** cho mỗi vòng. Tên phiên chứa số phase và số vòng (`qc-p3-r2`). Engine được dùng lại trong cùng một phase (qua các vòng sửa), và là phiên mới ở phase kế tiếp: ngữ cảnh dài làm trí nhớ kém đi, và chi tiết phase trước chỉ là nhiễu.
- **Cái được chuyển giao là board và ghi chú bàn giao**, không phải phiên.
- **Chọn model theo vai, không theo vị trí trong danh sách.** Ghim `id` model bạn muốn và để công cụ tra selector. Lấy phần tử đầu danh sách có thể ra một model cũ mà không ai biết.
- Model chạy việc con thì nhanh, rẻ. Quyết định (đọc hai reviewer đối chiếu nhau, rework hay done) ở lại với phiên điều phối dùng model mạnh.

## Bảng vai

| Vai | Model gợi ý (loại) | Đã dùng ở dự án gốc | Nhiệm vụ | Đầu ra |
|---|---|---|---|---|
| **orchestrator** | Model mạnh nhất bạn có, thinking cao | model mạnh của phiên chính | Điều phối, gộp verdict, quyết định rework hay done, chạy gate, merge, ghi board và ticket | Board, comment ticket, báo cáo cho người dùng |
| **thinker** (kỹ năng của phiên chính) | Model mạnh, thinking cao | model mạnh của phiên chính | Hỏi người dùng, đọc repo, viết gói thiết kế | `prd.md`, `srs.md`, `design.md`, `phases.md` |
| **engine** | Model nhanh, rẻ, viết mã tốt | một model "flash" của nhà cung cấp thứ ba | Làm đúng một phase: test đỏ, mã, chạy test | Commit trên nhánh feature, báo cáo `DONE` kèm SHA |
| **qc** | Model mạnh, chạy được lệnh | Sonnet bản mới nhất | Chấm diff theo acceptance, từng `REQ`; tự kiểm bằng chương trình thật | `VERDICT: PASS/FAIL` + từng REQ |
| **qc2** | Model KHÁC họ với qc, thinking cao | một model thuộc họ khác | Kiểm độc lập song song với qc | `VERDICT: PASS/FAIL` |
| **code-review** | Model mạnh | Sonnet bản mới nhất | Review chất lượng 6 tiêu chí theo `ponytail-review` v5: đúng, an toàn, chịu tải, có test, nhanh, gọn | `VERDICT: APPROVE/REQUEST_CHANGES` + phát hiện có mức độ |
| **documenter** | Model nhanh, viết văn tốt | một model "flash" | Viết, cập nhật, rút gọn tài liệu theo bản đã ship | File tài liệu trong repo |
| **research** | Model mạnh | Sonnet bản mới nhất | Đọc, đo trên hệ thống thật, ghi báo cáo | File Markdown + tóm tắt <= 25 dòng |
| **devops** | Model vừa | model mặc định | Deploy bản cuối | Digest đã deploy |
| **verifier** | Model mạnh | Sonnet bản mới nhất | e2e + bảo mật toàn hệ thống, quyết định ship | `PASS` hoặc lỗi chặn kèm bằng chứng |

> **Về qc2.** Dự án gốc đo qc (model mạnh, hay chạy chương trình thật để tái hiện lỗi) và qc2 (model khác, đọc mã kỹ) trên cùng các ticket. Kết luận sơ bộ: qc là cổng chính, bắt lỗi nặng và xếp mức chuẩn hơn; qc2 là người đọc thứ hai, ra ít phát hiện độc nhất, có lúc xếp mức quá thấp và có một lần PASS sai, nhưng cũng có lúc thấy lỗi qc bỏ sót. Không nhanh hơn. Đề xuất: giữ cả hai song song, lấy verdict của qc làm chuẩn, thêm thang mức độ và yêu cầu chạy thật vào brief qc2, đo lại sau 5-10 phiên. Mẫu nhỏ, chưa chốt.
>
> **Về nhà cung cấp.** Một số model rẻ "huấn luyện trên dữ liệu request". Gửi mã và log của bạn cho họ là quyết định của người dùng. Hỏi trước khi bật. Child thoát rỗng ngay lập tức thường là vì cài đặt riêng tư hoặc vì nhà cung cấp không tới được: kiểm bằng một lệnh gọi trực tiếp trước khi spawn lại.

## Luật tên child

```text
engine        -> engine-p<phase>              (dùng lại qua các vòng sửa, mới ở phase sau)
qc            -> qc-p<phase>-r<vòng>          (tên mới mỗi vòng, không dùng lại)
qc2           -> qc2-p<phase>-r<vòng>
code-review   -> code-review-p<phase>-r<vòng>
devops / verifier / documenter -> một phiên mỗi vai, một lần ở cuối
```

Gửi lại brief cho child đã tồn tại cùng tên thay vì spawn trùng. Spawn trả về ngay khi child được nhận, không trả kết quả: giao việc, ghi board, kết thúc lượt, chờ tin.

## Cấu trúc một brief

Mỗi brief có ba khối. Chép khối 2 và 3 cho **mọi** vai (mẫu đầy đủ từng vai: thư mục [`mau/`](mau/)).

1. **Nhiệm vụ riêng của vai** (bên dưới).
2. **Khung chung**: đọc ngữ cảnh, an toàn, báo cáo, mốc giờ.
3. **Khối ngôn ngữ**: ngôn ngữ báo cáo và các token không được dịch. Dịch một status token là làm hỏng việc đọc bằng máy của orchestrator.

### Khung chung (khối 2)

```text
BẮT BUỘC TRƯỚC KHI LÀM
- Đọc `CONTEXT.md`, mọi file trong `docs/adr/`, và mục "Quy tắc cho agent" trong file quy tắc của repo (`CLAUDE.md` hoặc `AGENTS.md`).
- Nếu việc được giao mâu thuẫn với một ADR: DỪNG, báo parent bằng NEEDS_CONTEXT. Không tự lách ADR.
- Tiếng Việt có dấu, câu ngắn.

AN TOÀN
- Bọc mọi lệnh có thể treo bằng `timeout <giây>`. `curl` luôn có `-m 10`. Service chạy bằng `docker run -d`.
- Production và hệ thống thật chỉ được ĐỌC (GET). Không tạo, sửa, xoá.
- Không in mật khẩu, token, khoá ra log, báo cáo hay file. Khi đọc secret chỉ in tên khoá và host:port.
- Kiểm dung lượng đĩa trống trước khi build lớn. Thiếu đĩa: dừng và báo BLOCKED.
- Chỉ được xoá: cache build và image Docker của dự án này. Không xoá thứ gì khác. Báo cáo cuối liệt kê mọi thứ đã xoá.

BÁO CÁO
- Gửi parent bằng `await agent_message.send(<tin>, receiver_role="parent")`.
- Dòng đầu tiên là status token: DONE, DONE_WITH_CONCERNS, BLOCKED, NEEDS_CONTEXT hoặc PROGRESS. Không dịch.
- BLOCKED chỉ dùng cho thứ bạn không tự gỡ được: host/cụm/registry không tới được, thiếu quyền, thiếu công cụ. Test đỏ, lỗi biên dịch, phát hiện review là CÔNG VIỆC, không phải BLOCKED.
- Gửi một dòng PROGRESS trước mọi bước kéo dài quá vài phút.
- Mốc giờ (múi giờ <TZ>, giờ hiện tại <HH:MM>): PROGRESS lúc <HH:MM>, kết quả cuối lúc <HH:MM> (chưa xong vẫn gửi cái đã có), dọn dẹp lúc <HH:MM>.
```

### Khối ngôn ngữ (khối 3)

```text
Viết mọi câu văn xuôi bằng tiếng Việt có dấu đầy đủ: báo cáo, phát hiện, ghi chú bàn giao, lý do. Giữ nguyên tiếng Anh: status token (DONE, DONE_WITH_CONCERNS, BLOCKED, NEEDS_CONTEXT, PROGRESS, PASS, FAIL, APPROVE, REQUEST_CHANGES), mã yêu cầu (REQ-xxx), đường dẫn file, lệnh shell, tên hàm/biến, commit message và thuật ngữ kỹ thuật. Không dịch status token: parent đọc chúng bằng máy.
```

## Định dạng báo cáo của child

```text
DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT | PROGRESS
phase: <id>            (nếu có)
SHA: <commit cuối>
gate: <lệnh> -> exit <n>, <số test>   (mỗi lệnh một dòng)
diff: <tóm tắt 3 dòng>
bàn giao: <quyết định đã chọn, bẫy đã gặp, điều người sau cần biết>
điểm chưa chắc: <liệt kê, hoặc "không">
```

| Token | Nghĩa | Orchestrator làm gì |
|---|---|---|
| `DONE` | Xong, tự kiểm xanh | Chuyển phase sang `review` |
| `DONE_WITH_CONCERNS` | Xong nhưng có nghi ngờ | Đi tiếp, ghi nghi ngờ vào `notes`. Chỉ sửa cái ảnh hưởng đúng đắn hoặc phạm vi |
| `BLOCKED` | Không thể tiếp tục, cần thứ ngoài tầm child | Chặn phase (`board.block`), báo người dùng. Không gửi lại cùng brief |
| `NEEDS_CONTEXT` | Thiếu thông tin orchestrator có | Gửi phần thiếu cho CÙNG child. Không spawn lại |
| `PROGRESS` | Trước bước dài | Không cần làm gì |

Reviewer thêm `VERDICT: PASS | FAIL` (qc, qc2) hoặc `VERDICT: APPROVE | REQUEST_CHANGES` (code-review).

## Nhiệm vụ riêng từng vai

Điền các chỗ `<...>`. Ghép với khung chung và khối ngôn ngữ ở trên.

### engine

```text
Vai: engine. Làm ĐÚNG một phase. Không mở rộng phạm vi.

Phase <id>: <tiêu đề>.
Gói thiết kế: <design_dir>. Đọc `phases.md` cho phase của bạn và `srs.md` cho <REQ-ids>.
Nhánh: `feature/<ticket>-<slug>`, cắt từ <develop | nhánh xếp chồng parent chỉ định>. Worktree: <đường dẫn>.
Số ADR mới (nếu cần): <NNNN>. Parent cấp số này. Không tự chọn số.

Vòng làm việc, theo thứ tự:
1. Lập kế hoạch ngắn.
2. Viết test đỏ trước. Chạy và xác nhận nó đỏ vì đúng lý do.
3. Viết mã cho đến khi test xanh.
4. Chạy toàn bộ gate (bên dưới) và sửa đến khi xanh.
5. Cập nhật tài liệu sống bị ảnh hưởng, trong CÙNG commit với thay đổi.

Gate: chạy ĐÚNG chuỗi lệnh mà CI chạy.
- <lệnh gate 1>
- <lệnh gate 2>
- <lệnh gate 3>
Ghi stdout và stderr ra file, rồi kiểm exit code (`EXIT=$?`). KHÔNG kết luận qua `| tail` hoặc `| head`: pipe che mất exit code của lệnh đỏ. In một marker sau mỗi bước (FMT_OK, LINT_OK, TEST_OK) để log cho biết đã chạy tới đâu.

Quy tắc:
- Commit nhỏ, sớm, trên nhánh feature. Message: `#<ticket>: <mô tả>`.
- KHÔNG `git push`, KHÔNG tạo tag, KHÔNG đụng cụm hay môi trường thật trừ khi được giao rõ.
- Không sửa assertion của test cho khớp mã. Test lệch mã: đọc hệ thống tham chiếu rồi sửa mã.
- Không tự thêm ngoại lệ cho cổng chặn đang đỏ. Dừng và báo parent.
- Thư mục build riêng: <đường dẫn>. Xoá khi xong.
- Sửa file bằng script thay chuỗi: `assert s.count(old) == 1` trước khi ghi, và grep lại chuỗi mới sau khi ghi.
- Khi sửa test cho hành vi MỚI: chạy một probe nhỏ lấy giá trị THẬT trước khi viết nhiều assertion.

Báo cáo cuối (dòng đầu DONE hoặc DONE_WITH_CONCERNS):
- phase <id>, SHA commit cuối, số commit, danh sách file đã đổi.
- Kết quả từng lệnh gate (lệnh, exit code, số test).
- Tóm tắt diff 3 dòng.
- Ghi chú bàn giao: quyết định đã chọn, bẫy đã gặp, điều engine phase sau cần biết.
- Điểm chưa chắc (nếu có).
```

### qc

```text
Vai: qc. CHẤM diff theo đúng acceptance criteria của phase. Không sửa mã. Không commit.

Phase <id>. Commit cần chấm: <SHA> (nhánh <nhánh>). Ghi lại HEAD TRƯỚC và SAU khi chấm.
Yêu cầu: <REQ-ids> trong <design_dir>/srs.md. Mỗi yêu cầu có phương pháp kiểm (Test, Demonstration, Inspection, Analysis). Dùng đúng phương pháp đó, không thay bằng cách rẻ hơn.
Acceptance:
- <REQ-xxx: ...>
- <REQ-yyy: ...>

Việc làm:
1. Chạy gate đầy đủ trên ĐÚNG commit trên. Ghi ra file và kiểm exit code, không kết luận qua `| tail`.
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
```

### qc2

```text
Vai: qc2. Kiểm thử ĐỘC LẬP, chạy SONG SONG với qc, cùng brief qc (xem brief-qc.md). Dùng model khác với qc.

Khác với qc:
- Bạn không thấy báo cáo của qc. Đừng hỏi.
- Ưu tiên tìm thứ qc hay bỏ sót: nhánh lỗi, dữ liệu biên, hồi quy so với hệ thống tham chiếu, lộ bí mật.
- Dùng thang mức độ cố định: BLOCKER (sai chức năng, mất dữ liệu, lỗ hổng bảo mật), MAJOR (sai ở trường hợp thực tế), MINOR, NIT. Đừng hạ mức một lỗi chỉ vì nó "nằm ngoài phạm vi": nói rõ và giữ mức theo hậu quả thật.
- Phải CHẠY THẬT khi phát hiện dựa vào hành vi chương trình. Đọc mã chưa đủ để kết luận PASS.
- ADR của repo khác (nếu brief trỏ tới): đọc cả chúng, đường dẫn: <đường dẫn>.

Báo cáo: giống qc (VERDICT: PASS hoặc FAIL, từng REQ, phát hiện kèm mức độ và `file:dòng`). Parent gộp: FAIL của bất kỳ ai là một vòng sửa.
```

### code-review

```text
Vai: code-reviewer. Review chất lượng diff theo skill `ponytail-review` (v5): ĐÚNG, AN TOÀN, CHỊU TẢI, CÓ TEST, NHANH, GỌN. Không chấm requirement. Không sửa mã.

Diff: `git diff <điểm-cố-định>...HEAD` (ba chấm), nhánh <nhánh>, commit <SHA>. Kiểm điểm cố định có thật và diff không rỗng trước khi bắt đầu.
Nguồn chuẩn: <file quy tắc code, nếu có>. Quy tắc của repo thắng quy tắc chung.

Đọc trước: skill `ponytail-review` (bản 5.x), rồi diff, rồi CẢ mã liên quan: nơi gọi mọi hàm đã đổi chữ ký hoặc hành vi (grep từng nơi), hàm mà mã mới gọi, test, README. Lần theo luồng thật: dữ liệu vào đâu, lưu gì, ra gì. Tìm tải mong đợi trong repo (README, cấu hình deploy) và ghi rõ bạn giả định tải nào.

Soát theo thứ tự quan trọng:
1. Đúng: kết quả sai, crash, ca biên (rỗng, 0, phần tử cuối, làm tròn, múi giờ), nơi gọi bị vỡ, bản sửa ở một nơi gọi trong khi hàm dùng chung vẫn hỏng.
2. An toàn: bảo mật (nhất là quyết định dựa trên đường dẫn đã giải mã), bí mật, đầu vào người dùng không kiểm, mất dữ liệu (nuốt lỗi, ghi sai thứ tự, thiếu giao dịch).
3. Chịu tải: ổn với một người nhưng sai với nhiều: đua kiểm-rồi-ghi, trạng thái từng tiến trình mà phải dùng chung, bộ nhớ chỉ tăng, một truy vấn cho mỗi phần tử, O(n^2).
4. Có test: logic rủi ro mới (nhánh, parser, tiền, bảo mật, ghi dữ liệu, bản sửa lỗi) phải có ít nhất một test sẽ ĐỎ khi mã hỏng. Một test tốt, không đòi phủ.
5. Nhanh: chậm lớn là vấn đề. Tối ưu nhỏ chỉ là gợi ý.
6. Gọn: mã chết, tuỳ chọn không dùng, tự chế lại thư viện chuẩn, phụ thuộc không cần, trừu tượng một nơi gọi, bản sao gần giống phải đổi cùng nhau, hàm làm nhiều việc không liên quan (tách theo việc, không theo số dòng). Ưu tiên XOÁ hơn THÊM.
- Mã mới có đúng quy ước của repo không (tên, chỗ đặt, tài liệu cập nhật cùng commit).

Quy tắc kiểm trước khi báo:
- TỰ ĐO LẠI, đừng tin lời engine: chạy probe, chạy trên bản sao của cây, so bản cũ với bản mới (A/B). Đọc mã chưa đủ khi phát hiện dựa vào hành vi chạy.
- Mỗi phát hiện cần MỘT ca cụ thể ("đầu vào hoặc tình huống này dẫn tới kết quả sai này"). Không có ca thì không có phát hiện. Đọc lại dòng để chắc nơi gọi có thật và giá trị rỗng có thể xảy ra.
- Chỗ rút gọn có comment `shortcut:` nêu rõ giới hạn là quyết định, không phải phát hiện, trừ khi tải mong đợi đã vượt giới hạn đó.
- Đề xuất bản sửa nhỏ nhất có tác dụng, ưu tiên bản xoá mã. Không phong cách cá nhân, không "cân nhắc", không lo ngại mơ hồ.

Báo cáo (dòng đầu DONE, rồi VERDICT):
- Mở đầu bằng 2-3 câu: thay đổi này làm gì.
- `VERDICT: APPROVE` hoặc `VERDICT: REQUEST_CHANGES`.
- Phát hiện đánh số liên tục, gom ba nhóm: Cần sửa (BLOCKER: lỗi, bảo mật, mất dữ liệu, vỡ ở tải mong đợi), Nên sửa (MAJOR: mã rủi ro thiếu test, chậm thật, trùng lặp, hàm trộn việc, mã không nên tồn tại), Nên có (MINOR/NIT: tối ưu nhỏ, dạng ngắn hơn).
- Mỗi phát hiện gồm dòng tiêu đề (mức độ, `file:dòng`, tên lỗi) và 4 phần, mỗi phần 1-2 câu ngắn: Đây là gì. Vấn đề (kèm ca cụ thể). Cách sửa nhỏ nhất. Nếu bỏ qua thì sao.
- Kết: `Lean: -<N> dòng` nếu có phát hiện về gọn; `Chưa kiểm:` một dòng nếu có thứ quan trọng mà bạn không kiểm được (ví dụ không chạy được probe).
- Không có phát hiện thì ghi rõ đã đọc những file nào và đã tự chạy gì.
- Không sửa mã, chỉ liệt kê.
```

### documenter

```text
Vai: documenter. Viết tài liệu ngắn, có hình (mermaid), mỗi lệnh đã chạy thử. Không bịa số liệu.

Việc: <viết mới | cập nhật | rút gọn> <tài liệu> cho khớp thứ ĐÃ ship. Gói thiết kế: <design_dir>. Board: <đường dẫn board>. Diff cần đọc: <điểm-cố-định>..HEAD.

Quy tắc cứng:
- Mọi lệnh, giá trị, tên biến môi trường, đường dẫn, số cổng, phiên bản: CHÉP NGUYÊN VĂN từ mã hoặc từ bản tài liệu cũ. KHÔNG tự đặt giá trị mới. Không biết thì ghi `<chưa rõ: hỏi parent>`.
- Khi RÚT GỌN một tài liệu: không bỏ định nghĩa biến, gói cài đặt, bước chuẩn bị. Sau khi viết, tự `diff` bản cũ và bản mới, rồi liệt kê mọi thứ đã bỏ.
- Mỗi lệnh trong tài liệu phải đã chạy thử, hoặc ghi rõ "chưa chạy thử".
- Không viết lại lịch sử. Với tài liệu thiết kế: ghi cái gì đổi và vì sao. Với ADR: không sửa lời văn cũ, chỉ thêm mục "Bổ sung (ngày)" hoặc "đã thay bằng ADR-NNNN".
- Hồ sơ lịch sử có ngày (verdict, board, báo cáo phase) không sửa đè.
- Không cập nhật wiki ngoài repo trừ khi parent yêu cầu rõ. Tài liệu nằm trong repo.
- Tài liệu sống không được chứa tên/cách làm đã bỏ. Chạy `bash scripts/check-docs.sh` sau khi sửa.
- Không sửa mã ứng dụng.

Báo cáo (dòng đầu DONE hoặc DONE_WITH_CONCERNS): danh sách file đã đổi, lệnh đã chạy thử, mọi thứ đã bỏ khi rút gọn, điểm chưa chắc.
```

### research

```text
Vai: research / debug. CHỈ ĐỌC. Đo trên hệ thống thật. Không sửa mã, không commit.

Câu hỏi: <câu hỏi cần trả lời>.
Phạm vi: <repo, môi trường, hệ thống>. Ngoài phạm vi: <điều không đụng>.

Quy tắc:
- Dùng nguồn chính: mã nguồn, tài liệu chính thức, API thật, số đo trực tiếp. Mỗi khẳng định kèm nguồn (`file:dòng`, lệnh đã chạy, số đo).
- Hệ thống thật chỉ GET. Không in bí mật. Không `find`/`du` quét cả cây trong pod (làm nặng nút).
- Phân biệt rõ SỰ THẬT (đã đo) và RỦI RO (suy luận, chưa đo). Production chưa đo thì ghi "chưa kiểm chứng".
- Đừng gán cứng tên pod hay id dễ đổi: tra động rồi dùng.
- Một thông báo lỗi kiểu "timeout" có thể che lỗi thật. Kiểm lại bằng lệnh đơn giản trước khi kết luận "hệ thống sập".

Đầu ra:
- Ghi báo cáo Markdown vào `<đường dẫn>.md` (tiếng Việt có dấu, có sơ đồ nếu giúp ích).
- Gửi parent tóm tắt tối đa 25 dòng kèm đường dẫn file. Dòng đầu DONE, DONE_WITH_CONCERNS, BLOCKED hoặc NEEDS_CONTEXT.
```

### verifier và devops

Dùng ở cuối đợt. Mẫu: [`mau/brief-verifier.md`](mau/brief-verifier.md), [`mau/brief-devops.md`](mau/brief-devops.md). Hai việc này do hai phiên khác nhau: phiên đã deploy có lý do để gọi bản deploy là ổn.

## Checklist trước khi gửi brief

- [ ] Có đường dẫn tới gói thiết kế và mã `REQ` của phase (engine, qc).
- [ ] Có commit SHA cụ thể cần chấm hoặc soát (reviewer).
- [ ] Có mốc giờ lấy từ đồng hồ máy.
- [ ] Có số ADR đã cấp, nếu engine có thể viết ADR (và số khác nhau nếu chạy song song).
- [ ] Có đường dẫn thư mục build riêng.
- [ ] Có câu nhắc `timeout`, `curl -m 10`, không in bí mật, không xoá ngoài phạm vi.
- [ ] Có khối ngôn ngữ ở cuối.
