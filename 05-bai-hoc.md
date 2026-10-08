# 05 - Bài học

Mỗi bài rút từ một sự cố hoặc một lần review bắt lỗi thật. Ví dụ đã tổng quát hoá. Mỗi bài: **luật** và **lý do**.

## A. Điều phối

1. **Mọi child chạy dài đều có mốc giờ, và giờ lấy từ đồng hồ máy.**
   Không có mốc thì không ai biết child treo hay đang làm. Có lần orchestrator đoán giờ lệch hơn một tiếng và phải gửi lại brief.

2. **Orchestrator không sửa mã, kể cả "chỉ một dòng fixture".**
   Nó chỉ merge, chạy gate, review, điều phối. Sửa "nhỏ" tự làm thì không qua review và là lý do người dùng phàn nàn. Tạo nhánh sửa cũng giao cho engine.

3. **Trước khi tiếp tục board, kiểm có orchestrator khác đang giữ nó.**
   Board không ghi ai đang ghi. Hai phiên cùng spawn engine cho một phase thì ghi đè worktree và dữ liệu golden của nhau. Thấy phiên khác đang chạy: chỉ báo, không ghi.

4. **Không bao giờ tắt watchdog khi còn child `running`.**
   Child trông treo có thể kẹt trong một lệnh và không đọc được tin nhắc. Xem CPU của kernel child, SIGTERM nó, nó thường tỉnh lại và gửi kết quả.

5. **Child thoát rỗng ngay lập tức = nhà cung cấp model có vấn đề, không phải lỗi của brief.**
   Kiểm bằng lệnh gọi trực tiếp (`curl -m 10`) trước khi spawn lại. Nguyên nhân gặp: mất mạng tới nhà cung cấp, cài đặt riêng tư của model bị chặn.

6. **Cấp số ADR khác nhau trong từng brief khi chạy engine song song.**
   Hai engine song song cùng tạo `0019-*`. Mất thêm một commit đổi tên.

7. **Merge bằng một hàm an toàn, không nối chuỗi `cd X && merge && push`.**
   Worktree tạm có thể biến mất. `cd` lỗi làm lệnh sau chạy sai thư mục, đẩy bị từ chối, CI chạy trên commit cũ. Hàm đúng: `set -e`, dựng lại worktree từ `origin/<nhánh>`, dừng khi xung đột, chỉ báo thành công khi `origin/<nhánh>` bằng SHA đã đẩy. Kích CI sau đó và kiểm log có đúng SHA. Nhánh đã chứa sẵn merge của nhánh khác thì merge nó trước.

## B. Gate và kiểm thử

8. **Gate chạy đúng chuỗi lệnh của CI, ghi ra file, kiểm exit code.**
   `lint ... | tail -25` trả exit code của `tail` (0). Lint đỏ mà gate cục bộ báo xanh, và CI đỏ ở bước build. In marker sau mỗi bước.

9. **Thư mục build dùng chung giữa nhiều checkout làm test chạy nhầm bản build cũ.**
    Biểu hiện: lỗi "không tìm thấy file ở đường dẫn khác" hoặc đỏ giả mà thư mục build riêng thì xanh. Gate cuối trước merge dùng thư mục build RIÊNG và xoá sau. Nếu buộc dùng chung: `touch` file nguồn trước khi chạy.

10. **Fixture cần "bản cũ" của mã phải ghim SHA lịch sử, đừng dùng `origin/develop` hay `HEAD^`.**
    Sau khi bản sửa vào `develop`, "bản cũ" chính là bản mới và fixture đỏ vĩnh viễn. Cho ghi đè SHA bằng biến môi trường.

11. **Chứng minh fixture bắt được lỗi: chạy BẢN CŨ của cổng trên đúng dữ liệu fixture.**
    Nó phải ra kết quả SAI như mô tả lỗi. Thêm đối chứng âm (đổi ref thành bản mới thì ca phải FAIL). Với cổng kiểu "khối giữa hai dấu mốc": phá luật vừa thêm, cổng phải đỏ.

12. **Không khẳng định thời gian tuyệt đối trong test mặc định.**
    CI chạy bản debug trên máy chậm hơn máy dev hàng chục lần: `< 1 s` đo được 70 ms ở máy dev nhưng 1,5 s ở CI. Đếm công việc thật (số byte đã đọc, số lần gọi) thay vì đo đồng hồ.

13. **Docker daemon của agent CI có thể không chung filesystem.**
    Bind mount ra thư mục rỗng. Đưa file vào container qua STDIN (`tar -cf - . | docker run -i ...`). Máy dev chia sẻ filesystem nên lỗi này không tái hiện được ở máy dev: kiểm tĩnh (grep dòng `docker run` không có `-v`).

14. **Sửa file bằng script thay chuỗi phải `assert s.count(old) == 1` trước khi ghi.**
    Một bản sửa không áp dụng vì mẫu không khớp, test vẫn xanh trên mã cũ, engine báo DONE cho thứ diff không chạm tới. Reviewer bắt được. Ưu tiên công cụ sửa file báo lỗi khi không khớp.

15. **Số test: phase mặc định đã gồm test `#[ignore]`.**
    Chạy thêm phase `--ignored` là chạy lại chính chúng. Cộng hai phase là đếm hai lần (báo cáo từng lệch 547 và 526).

## C. Đúng đắn và bảo mật

16. **Quyết định bảo mật dùng đúng đường dẫn mà bộ định tuyến dùng: giải mã một lần, đã chuẩn hoá.**
    Mọi nhánh (pass-through, allowlist, kiểm quyền) quyết định trên đường dẫn đó, và byte gửi lên upstream phải khớp nó, nếu không có khoảng hở TOCTOU (`%2F`). Fuzz với hệ thống chuẩn thật, soi chiều fail-open (ta cho qua, chuẩn chặn).

17. **Đọc Secret: chỉ xử lý khoá khớp chính xác hậu tố, không bao giờ in giá trị.**
    Lọc theo một chuỗi tên dịch vụ làm cả các khoá mật khẩu cùng tiền tố cũng khớp và bị in ra. In tên khoá và `host:port`. Lỡ in: báo ngay.

18. **Golden của hệ thống chuẩn phụ thuộc môi trường và trôi theo thời gian.**
    Đo trong môi trường giống chạy thật (bảng MIME khác nhau giữa image đầy đủ và slim). Ghi mốc chuẩn ở MỘT file tham số. Fixture giữ **đầu vào** từng ca để mọi ca sinh lại được (replay), và chuẩn hoá phần ngẫu nhiên để golden không đổi mỗi lần chạy.

19. **Script tự sửa dữ liệu rồi đi gitflow: năm lỗi review hay bắt.**
    (a) Đọc dữ liệu gốc từ `origin/<nền>` sau `git fetch`, không đọc file sót trong cây. (b) Vòng lặp bỏ qua ticket đang chờ người trả lời. (c) Lỗi giữa đường: comment đúng trạng thái thật, dọn cây, không force-push. (d) Probe chỉ GET. (e) Mẫu ticket để chỗ trống ở giá trị KHÔNG hợp lệ (`<GET|POST>`) để ticket chưa điền bị hỏi lại.

## D. Tài liệu và nâng phụ thuộc

20. **Tài liệu viết gọn dễ bịa giá trị: bắt chép nguyên văn và review bằng diff.**
    Xem [`04`](04-tai-lieu-cho-agent.md). Rút gọn hai runbook sinh ra URL, tên biến, cổng sai và làm mất bước cài đặt.

21. **Cổng tài liệu bằng `git grep` không thấy file chưa commit và cấm tên cũ xuất hiện ngay cả để nói "đã bỏ".**
    Thử trên bản đã commit. Viết vòng, để tên cũ ở ADR. Chứng minh cổng không rỗng bằng cách thêm tạm một tên đã bỏ.

22. **Hai thư viện chung một cây phụ thuộc thì nâng cùng lúc, và báo repo kia trước.**
    Đổi tag thư viện lõi ở một repo, repo kia chưa nâng, thì build của repo kia đỏ vì hai nguồn cho cùng một thư viện.

23. **Cập nhật phụ thuộc có thể âm thầm hạ phiên bản package khác.**
    Luôn đọc diff file khoá và chạy cổng chống hạ. Phân biệt XOÁ (package biến mất vì không ai dùng nữa) với HẠ. Ngoại lệ cho cổng chặn là quyết định của người dùng, không phải của agent.

## E. Hạ tầng dùng chung

24. **Agent CI dùng chung một ổ đĩa: mỗi job chỉ dọn thứ nó tạo ra, và có trần thời gian.**
    Job không có timeout đã treo hàng chục giờ khi hết đĩa vì bước dọn không chạy được. Dọn sau build: xoá image vừa build, xoá image phụ thuộc cũ, prune cache cũ hơn vài giờ, dọn workspace. Phần còn lại (ngưỡng đĩa, cron prune, retention registry) là việc của quản trị CI. Đừng thêm bước đo hoặc chặn đĩa vào pipeline nếu nó làm chậm hoặc làm lỗi build.

25. **Brief cho build/deploy phải cấm xoá ngoài Docker.**
    Một devops child xoá hàng chục GB cache của thư mục home để lấy chỗ vì brief chỉ nói "dọn cache và image cũ". Giờ brief nói: chỉ cache build và image của dự án; thiếu đĩa thì BLOCKED; liệt kê mọi thứ đã xoá.
