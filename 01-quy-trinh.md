# 01 - Quy trình từng bước

Mỗi bước có **đầu vào**, **việc làm**, **DoD** (Definition of Done: điều kiện để coi bước là xong).

## Ba bên và ranh giới

| Bên | Làm | KHÔNG làm |
|---|---|---|
| **Người dùng** | Trả lời câu hỏi thiết kế. Duyệt gói thiết kế. Quyết định khi có đánh đổi. Thông báo "đã ổn" để vào `develop`. Quyết định phát hành. Quyết định ngoại lệ cho cổng chặn. | Không phải đọc diff từng dòng. Không phải tìm thông tin agent tự tra được. |
| **Orchestrator** (phiên điều phối) | Đọc gói thiết kế. Ghi board. Giao việc cho child kèm deadline. Gộp verdict. Chạy gate. Merge. Kích CI. Deploy. Kiểm. Ghi ticket. Báo người dùng. | **Không tự sửa mã, test, fixture, kể cả sửa "nhỏ".** Mọi sửa mã đi qua một engine được giao. Không tự nới cổng chặn. Không tự phát hành. |
| **Child** (engine, qc, qc2, code-review, documenter, research, verifier...) | Làm đúng một việc được giao, trong ngữ cảnh sạch. Báo cáo với dòng trạng thái đầu tiên. | Không mở rộng phạm vi. Không tự `push`/tag. Không sinh child con. Không đụng việc của vai khác. |

Lý do orchestrator không sửa mã: nó giữ ngữ cảnh của cả dự án và đóng vai người quyết định. Nếu nó tự sửa, nó vừa viết vừa chấm bài của chính mình, và bản sửa "nhỏ" không đi qua review.

## Sơ đồ trạng thái của một phase

```mermaid
stateDiagram-v2
  [*] --> pending
  pending --> engine: giao engine
  engine --> review: engine báo DONE
  review --> engine: có FAIL/REQUEST_CHANGES (round + 1)
  review --> done: mọi reviewer PASS và gate xanh
  pending --> blocked: BLOCKED
  engine --> blocked: BLOCKED
  review --> blocked: BLOCKED
  blocked --> engine: gỡ chặn
  done --> [*]
```

`blocked` nhớ trạng thái trước nó và quay lại đúng chỗ đó. Phase `blocked` không thể bị đóng nhầm.

## Các bước

### Bước 0 - Tiếp nhận

- **Việc:** nhận ý tưởng hoặc ticket. Mở ticket theo dõi (nếu chưa có). Kiểm không có phiên điều phối khác đang giữ cùng board (xem mục "Một người ghi board" bên dưới).
- **DoD:** có ticket, có nhánh `feature/<ticket>-<slug>` cắt từ `develop`.

### Bước 1 - Thiết kế (skill `thinker`)

- **Đầu vào:** ý tưởng thô.
- **Việc:** đọc repo trước (README, quy tắc agent, PRD cũ, mã liên quan, lệnh test và CI). Chỉ hỏi người dùng điều không có trong repo, theo cây quyết định (skill `grilling`). Gọi tên các vấn đề thiết kế. Cân 2-3 phương án và ghi phương án bị loại. Viết `docs/design/<slug>/{prd,srs,design,phases}.md`. **Chạy thử lệnh gate trước khi ghi vào `phases.md`.**
- **Builder check:** sau khi gói qua phần tự kiểm, giao gói cho một sub-agent mới (prompt: [`skills/thinker/references/builder-check.md`](skills/thinker/references/builder-check.md)). Sub-agent đóng vai kỹ sư phải chạy orchestrator theo gói mà không được hỏi người dùng. Nó chỉ báo những chỗ phải đoán mà đoán sai thì build sai, xếp theo mức quan trọng. Thinker chia câu hỏi thành ba nhóm:
  - **Đã có câu trả lời** trong cuộc trò chuyện hoặc trong repo: ghi câu trả lời vào gói.
  - **Nhỏ:** một kỹ sư hợp lý tự quyết được mà không đổi thứ được build. Thinker tự quyết và ghi vào `## Agent's calls` trong `design.md`.
  - **Của người dùng:** chỉ người dùng trả lời được, và câu trả lời đổi thứ được build. Gộp cả nhóm vào **một** tin nhắn, câu quan trọng nhất trước.

  Chỉ chạy một vòng. Khi bắt đầu viết gói, báo trước cho người dùng là sẽ có một người đọc gói và thinker có thể quay lại một lần với vài câu hỏi. Lý do: phần tự kiểm chỉ chứng minh gói đúng hình dạng; nó không thấy điều thinker chưa từng hỏi. Ví dụ: acceptance có thể pass hết trong khi lỗ hổng mà requirement muốn chặn vẫn còn.
- **DoD:**
  - [ ] Mỗi `REQ-xxx` có phương pháp kiểm: `Test`, `Demonstration`, `Inspection` hoặc `Analysis`.
  - [ ] Mỗi `REQ` nằm trong đúng một phase.
  - [ ] 3-7 phase. Không phase nào giữ hơn khoảng một phần ba số yêu cầu.
  - [ ] Gate chung xanh trên cây hiện tại. Gate riêng của mỗi phase đỏ (hoặc chưa chạy được). Gate riêng đã xanh nghĩa là việc đó đã xong rồi.
  - [ ] Mỗi dòng gate là một lệnh, không nối bằng `&&`.
  - [ ] Builder check đã chạy đúng một vòng. Nhóm câu hỏi "của người dùng" đã được trả lời và ghi vào gói.
  - [ ] Người dùng duyệt gói.
- **Đầu ra:** thư mục gói thiết kế. Mẫu: [`mau/goi-thiet-ke/`](mau/goi-thiet-ke/).

### Bước 2 - Khởi tạo orchestrator

- **Việc:** copy từng `## Phase N` lên board (`board.add_phase`). Kiểm `board.uncovered` rỗng. Chạy gate chung **một lần trên cây sạch**. Chọn model theo vai và ghi vào board.
- **Bật heartbeat watchdog 5 phút/lần** trước khi giao phase đầu tiên (xem mục [Deadline và watchdog](#deadline-và-watchdog)). Ghi id heartbeat vào board.
- **Kết quả gate chung:**
  - Xanh: đi tiếp.
  - Đỏ vì mã: repo hỏng từ trước. Báo người dùng. Không giao engine sửa thứ chưa ai yêu cầu.
  - Không chạy được (thiếu công cụ, thiếu quyền, không tới được host): chặn cả đợt. Báo lệnh và lỗi, dừng.
- **DoD:** board có đủ phase, mỗi phase có `req_ids`, `acceptance`, gate. Gate chung đã chạy. Heartbeat đã bật.

### Bước 3 - Lặp cho từng phase

```mermaid
sequenceDiagram
  participant O as orchestrator
  participant E as engine
  participant A as advisor
  participant Q as qc / qc2
  participant C as code-review
  O->>E: brief + deadline (phase N)
  E-->>O: dự thảo + đầu mục cần chấm
  O->>A: brief advisor, grok-4.7 thinking xhigh
  A-->>O: comment điểm theo đầu mục + nâng cấp ngắn
  O->>E: gửi điểm, engine tự đánh giá rồi phát triển
  E-->>O: DONE + SHA + gate + điểm chưa chắc
  par kiểm song song, không thấy nhau
    O->>Q: brief qc + commit SHA
    O->>C: brief review + commit SHA
  end
  Q-->>O: PASS hoặc FAIL kèm file:dòng
  C-->>O: APPROVE hoặc REQUEST_CHANGES
  alt có FAIL hoặc REQUEST_CHANGES
    O->>E: gửi CẢ HAI phản hồi trong MỘT tin (round + 1)
    E-->>O: DONE + SHA mới
    O->>Q: reviewer mới (tên mới, ngữ cảnh sạch)
    O->>C: reviewer mới
  else tất cả PASS
    O->>O: chạy gate chung rồi gate của phase
    O->>O: advance(phase, gate) -> done
  end
```

1. **engine** kiểm code của phase và viết **dự thảo**: kế hoạch ngắn, đầu mục cần chấm, bằng chứng đã đọc. Chưa coi phase là xong.
2. **advisor** chỉ chấm đúng các đầu mục engine đưa, điểm 0–5 kèm nhận xét, rồi tối đa ba gạch nâng cấp ngắn. Model `xai/grok-4.7`, thinking `xhigh`. Không sửa mã, không thêm đầu mục. Điểm advisor **không** đóng phase và **không** tự thành vòng sửa: orchestrator gửi điểm về engine.
3. **engine** đọc điểm, ghi hướng đã chọn (kể cả chỗ không theo advisor, kèm lý do), rồi mới phát triển: test đỏ trước, viết mã, chạy test. Commit sớm, từng bước nhỏ, trên nhánh feature. Không `push`. Vòng sửa sau qc hoặc code-review không bắt buộc gửi advisor lại, trừ khi engine viết dự thảo mới.
4. **qc** chấm diff **theo acceptance của phase**, từng `REQ` một: PASS hoặc FAIL kèm thứ còn thiếu. Dùng đúng phương pháp kiểm ghi trong SRS. Không kiểm được thì là FAIL, không phải PASS.
5. **qc2** (nếu dùng) chấm cùng brief nhưng model khác, độc lập. Mục đích: bắt thứ qc bỏ sót (nhánh lỗi, dữ liệu biên, lộ bí mật).
6. **code-review** đọc và áp dụng skill `ponytail-review` (v5). Đây là review **chất lượng đầy đủ**, không chỉ tìm mã thừa. Thứ tự quan trọng: **đúng, an toàn, chịu tải, có test, nhanh, gọn** (xoá hơn thêm). Reviewer đọc **cả mã liên quan** (nơi gọi hàm đã đổi, hàm được gọi, test, README), không chỉ diff, và ước tải mong đợi từ repo. Không chấm requirement (việc của qc). Trả `APPROVE` hoặc `REQUEST_CHANGES`. Mỗi phát hiện có mức độ (`BLOCKER`, `MAJOR`, `MINOR`, `NIT`), `file:dòng`, ca cụ thể làm hỏng, cách sửa nhỏ nhất và hậu quả nếu bỏ qua. Chi tiết ở [`02`](02-vai-tro-va-brief.md#code-review).
7. Orchestrator **chờ đủ** các reviewer rồi mới quyết. Mới có một phản hồi chưa phải verdict.
8. Quy tắc gộp: **FAIL hoặc REQUEST_CHANGES của bất kỳ ai** là một vòng sửa. Khác biệt giữa các reviewer ghi vào báo cáo (đó là dữ liệu để chọn lại model).
9. Tất cả PASS: orchestrator tự chạy gate (chung trước, riêng sau, lệnh rẻ nhất trước, dừng ở lệnh đỏ đầu tiên).
10. Gate đỏ là việc của engine, không phải phát hiện của reviewer. Gửi lệnh và output cho engine. Phase ở lại `review`.

**DoD của phase:** mọi reviewer PASS **và** mọi lệnh gate thoát 0 **và** các lệnh đó do orchestrator chạy, ghi vào board bằng `advance(..., gate=results)`.

### Bước 4 - Merge vào nhánh test, CI, deploy cụm test

- **Việc:** merge `feature/*` vào `test` (xem [`03`](03-gitflow-va-release.md)). Kích CI **sau khi** merge đã đẩy xong và đã kiểm SHA. CI build, chạy gate, gắn tag `TEST-<n>` (nếu repo dùng), deploy cụm test.
- **Một build CI một lúc.** Môi trường test và agent CI là tài nguyên dùng chung. Hai build chồng nhau ghi đè nhau hoặc làm hết đĩa.
- **Kiểm đúng bản:** log build phải có dòng checkout đúng SHA đã merge. Đã có lần CI chạy trên SHA cũ vì merge chưa đẩy kịp.
- **Chờ rollout xong** rồi mới kiểm. Lệnh apply trả về trước khi pod mới phục vụ.
- **DoD:** CI xanh, tag có thật, image ghim bằng digest hoặc tag bất biến, pod mới phục vụ.

### Bước 5 - Verifier

- **Việc:** một phiên **khác với phiên deploy** chạy e2e và quét bảo mật trên bản đã deploy, cộng các yêu cầu phi chức năng kiểu `Demonstration` hoặc `Analysis`. Quyết định ship hay không.
- **Kết quả:**
  - `PASS`: sang bước 6.
  - Lỗi chặn: mỗi lỗi thành một **phase mới** (`fix: ...`). Phase đã `done` không mở lại, để giữ hồ sơ cái đã ship.
  - `BLOCKED` (môi trường hỏng): báo người dùng. Không ship khi verifier chưa chạy được. Không coi im lặng là PASS.
- **DoD:** có verdict viết ra, kèm bằng chứng (lệnh và output).

### Bước 6 - Documenter

- **Việc:** cập nhật `docs/design/<slug>/` và tài liệu sống của repo cho khớp **cái đã ship**. Không viết lại lịch sử: ghi cái gì đổi và vì sao. Không bịa tài liệu cho thứ chưa ai làm.
- **DoD:** cổng tài liệu (`scripts/check-docs.sh`) xanh. Diff tài liệu được review (xem bài học về tài liệu gọn ở [`05`](05-bai-hoc.md)).
- **Tắt heartbeat** khi documenter đã báo xong, mọi phase đã `done` và không còn child nào `running`. Devops, verifier và documenter cũng là child, nên heartbeat chạy đến lúc này, không dừng ngay sau phase cuối.

### Bước 7 - Vào develop và phát hành

- **Vào `develop`:** CHỈ khi người dùng thông báo tính năng đã ổn trên cụm test. MR từ `feature/*`.
- **Phát hành:** cắt `release/<YYYY.MM.DD>` từ `develop`, MR vào `master`, CI gắn tag `MASTER-<n>`, merge ngược `master` về `develop`. Chi tiết và checklist ở [`03`](03-gitflow-va-release.md).
- **DoD:** tag `MASTER-<n>` có thật, `develop` không tụt so với `master`, ticket được đóng kèm comment tổng kết.

## Nhật ký ticket (mỗi mốc một comment)

Board là bản đầy đủ. Ticket là bản trace công khai. Orchestrator ghi comment ở **mỗi mốc**:

| # | Mốc | Nội dung tối thiểu |
|---|---|---|
| 1 | Mở việc | ticket, nhánh, worktree, model từng vai |
| 2 | engine DONE | HEAD, số commit, số test trước và sau |
| 3 | Mỗi vòng review | verdict **từng** reviewer, phát hiện chính (BLOCKER/MAJOR) kèm `file:dòng` |
| 4 | Sửa (rework) | gửi gì, HEAD mới |
| 5 | Gate | lệnh, exit code, số test |
| 6 | Phát hành | MR, commit merge, số build CI, tag |
| 7 | Chặn hoặc quyết định của người dùng | nội dung và ngày giờ |

- Dòng đầu: `**Nhật ký phase N (orchestrator, dd/mm/yyyy)**`. Có giờ. Không chứa bí mật. Liên kết chéo giữa các repo.
- Đóng ticket chỉ khi đã phát hành và có comment tổng kết. Việc `MINOR`/`NIT` không chặn thì mở ticket phụ.
- Mẫu: [`mau/ticket-mau.md`](mau/ticket-mau.md).

## Deadline và watchdog

Child chạy mà không có hạn thì không ai biết nó treo hay đang làm. Hai thứ đi cùng nhau: **mọi task có deadline**, và **một heartbeat kiểm từng child mỗi 5 phút**.

### Deadline

- **Không brief nào đi mà thiếu deadline.** Gồm cả reviewer, verifier, documenter, không chỉ engine.
- **Deadline là giờ tuyệt đối, lấy bằng đồng hồ máy** (`datetime.now()`) trước khi đặt. Đã có lần đoán giờ lệch hơn một tiếng và phải gửi lại brief. Ba mốc: PROGRESS giữa chừng, báo cáo cuối chậm nhất, dọn dẹp xong.
- **Hạn gợi ý** (chỉnh theo dự án): engine 45 phút mỗi phase. qc và code-review 20 phút mỗi vòng. devops 20, verifier 30, documenter 20. Việc dài hơn: chia nhỏ, hoặc đặt mốc PROGRESS dày hơn.
- **Hết deadline, child bắt buộc báo cáo.** Xong thì `DONE`. Chưa xong thì gửi **cái đã có** với `DONE_WITH_CONCERNS` (hoặc `BLOCKED` nếu bị chặn), kèm danh sách việc chưa làm. Im lặng quá deadline là vi phạm, không phải "đang làm".
- **Gia hạn chỉ bằng tin của orchestrator.** Child cần thêm giờ thì gửi `PROGRESS` xin gia hạn trước deadline, rồi chờ trả lời. Không tự kéo dài.
- **Ghi deadline của từng child lên board**, để heartbeat đối chiếu.
- **Bọc mọi lệnh có thể chạy lâu bằng giới hạn giờ.** macOS không có `timeout`: dùng `perl -e 'alarm 60; exec @ARGV' <lệnh>`. Khi chạy mã cũ trên đầu vào lớn để so A/B, chọn cỡ đầu vào sao cho mã cũ xong trong vài giây. Thêm: service trong container chạy bằng `docker run -d`, và `curl -m 10`.

### Heartbeat watchdog

- **Bật** ở Bước 2, trước khi giao phase đầu tiên. **Tắt** ở Bước 6, khi mọi phase đã `done` và không còn child nào `running`.
- **Chu kỳ 5 phút**, chờ lượt hiện tại của orchestrator xong rồi mới chạy (không ngắt giữa chừng).
- **Mỗi lần chạy, với từng child đã giao mà chưa báo cáo cuối:** xem trạng thái, số tin nhắn, tuổi của tin cuối; so với deadline trên board; xem tiến trình dùng nhiều CPU (`ps -Ao pid,etime,pcpu,command`).
- **Thang xử lý:**
  1. Tiến trình của child dùng ≥ 90% CPU hơn 5 phút: kill **tiến trình đó** (không kill child), báo child đã kill gì và vì sao, nhắc bọc lệnh bằng giới hạn giờ.
  2. Quá deadline, hoặc im hơn 10 phút: gửi MỘT tin yêu cầu báo cáo ngay, kèm cái đã có.
  3. Lần heartbeat kế tiếp vẫn im: `board.block` phase và báo người dùng. Không xoá child khi chưa báo người dùng.
- **Im lặng khi không có gì thay đổi.** Chỉ báo người dùng khi có thay đổi hoặc có child treo.
- **Không tắt heartbeat khi còn child `running`**, dù child đó trông đã treo (bài 4 ở [`05`](05-bai-hoc.md)).
- **Child treo trong lệnh:** xem CPU của kernel child (`ps -Ao pid,etime,pcpu,command`), nối tiến trình với worktree của nó (`lsof -p <pid> | grep cwd`), loại tiến trình của chính mình. SIGINT thường bị bỏ qua, SIGTERM trên kernel của child thường đưa nó về trạng thái rỗi và nó gửi nốt kết quả.
- **Child báo rỗng ngay lập tức** (`no-reply`): thường là nhà cung cấp model không tới được. Chạy `curl -m 10` tới nhà cung cấp trước khi spawn lại. Không spawn lại mù trên cùng nhà cung cấp.

## Quy tắc review nhiều vòng

1. Vòng 1: engine DONE, các reviewer chạy song song, mỗi reviewer là **phiên mới** (tên có số vòng, ví dụ `qc-p3-r1`).
2. Có `REQUEST_CHANGES` hoặc `FAIL`: orchestrator gửi **tất cả** phản hồi cho engine trong **một** tin. Không gửi engine hai lần cho cùng một vòng.
3. Engine sửa, báo SHA mới. Vòng 2 dùng reviewer mới (`qc-p3-r2`). Reviewer cũ không được dùng lại: ngữ cảnh sạch là lý do review bắt được lỗi.
4. Lặp đến khi tất cả PASS. Mỗi vòng ghi board và ticket.
5. Orchestrator kiểm diff cuối bằng mắt: phản hồi "đã sửa" của engine không phải bằng chứng. Với bản sửa nhỏ chỉ chạm tài liệu, có thể bỏ review đầy đủ nhưng phải kiểm diff không đụng `src/`, test, hay file khoá phụ thuộc.
6. Reviewer không thấy phản hồi của nhau. Hai reviewer đồng ý vì một người đọc người kia chỉ là một reviewer.
7. Phát hiện chưa chặn (`MINOR`/`NIT`): ghi vào ticket phụ, không chặn phase.
8. Thường cần **2 vòng**. Tối đa **3 vòng**. Sang vòng 4 mà còn phát hiện chặn thì orchestrator dừng, xem lại thiết kế hoặc phạm vi phase rồi mới quyết (không tự mở vòng 4 mù).
9. Reviewer **tự đo lại**, không tin lời engine: chạy probe, chạy trên bản sao của cây, so bản cũ với bản mới (A/B). Câu "đã sửa", "test xanh" của engine chỉ là điểm xuất phát (bài học 26 và 27 ở [`05`](05-bai-hoc.md)).
10. Với thay đổi chạm quyết định bảo mật, chạy **review bảo mật** (code-review) và **QC fuzz vi sai với hệ thống chuẩn** (qc, qc2) **song song**. Hai bên tìm hai loại lỗi khác nhau (bài học 28).

## Khi nào hỏi người dùng

**Hỏi:**
- Ngoại lệ cho một cổng chặn đang đỏ (ví dụ cho phép hạ phiên bản một thư viện).
- Thay đổi hành vi đã được chốt là chuẩn (lệch khỏi hệ thống tham chiếu).
- Bất cứ thứ gì nới bảo mật: tắt xác thực, bỏ kiểm quyền, xoá bản ghi.
- Kích CI khi người dùng có thể đang chạy một luồng khác trên cùng agent.
- Quyết định phát hành, deploy production, đổi DNS hoặc proxy.
- Mâu thuẫn với một ADR. **Dừng và báo, không tự lách ADR.**
- Child báo `BLOCKED` mà orchestrator không tự gỡ được.
- Phát hiện lỗi nặng ngoài phạm vi phase (tạo ticket và hỏi có làm ngay không).

**Không hỏi:**
- Thứ agent tra được trong repo hoặc đo được trên hệ thống thật.
- Quyết định cục bộ, rủi ro thấp: chọn cách đơn giản nhất, nói một lần.
- Việc đã có luật trong repo (gitflow, tên nhánh, cách ghim phụ thuộc).

Khi hỏi: nêu phương án khuyến nghị, hậu quả mỗi phương án, và cái gì dừng lại nếu chưa có trả lời.

## Một người ghi board

Board không ghi ai đang giữ nó. Trước khi một orchestrator **mới** tiếp tục phase từ board:

- [ ] Liệt kê phiên đang chạy (lệnh liệt kê của công cụ agent) và tìm phiên điều phối khác cùng thư mục, cũng như child trùng tên (ví dụ `engine-p4`).
- [ ] Đọc tin đầu và các tin gần nhất của từng phiên. Đừng đoán theo trạng thái "đang chạy".
- [ ] Thấy phiên khác đang làm: **chỉ báo người dùng hoặc nhắn phiên đó.** Không ghi board, worktree hay ticket.

Một sự cố thật: phiên thứ hai thấy phase ở trạng thái FAIL, mở vòng 3 và spawn engine thứ hai trong khi phiên thứ nhất đang có engine sửa cùng worktree. Kết quả là hai engine ghi đè file của nhau.

## Quy tắc vận hành khác

- **Giữ child tới cuối run, không xoá sau khi xong phase.** Người dùng muốn thấy mọi agent đã tham gia; vết nằm ở file verdict và ticket. Skill `orchestrator` trong repo này đã theo luật đó (không gọi `rlm.delete_subagent`). Đội muốn dọn sớm thì đổi ở cả hai nơi và ghi vào quy tắc agent.
- **Brief của việc build/deploy** phải nói rõ: chỉ được dọn cache build và xoá image Docker của dự án này. Cấm xoá file ngoài Docker (cache của home, dự án khác). Thiếu đĩa thì dừng và báo `BLOCKED`. Brief phải yêu cầu liệt kê chính xác mọi thứ đã xoá.
- **Production chỉ được đọc** trong mọi brief nghiên cứu và kiểm: chỉ `GET`, không tạo, sửa, xoá.
- **Không in bí mật** (mật khẩu, token, khoá) ra log, báo cáo hay file.
- **Ghim số ADR trong brief** khi chạy nhiều engine song song (xem [`05`](05-bai-hoc.md)).
