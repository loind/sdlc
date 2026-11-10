# Quy tắc cho agent

## Gate

- Mọi gate chạy qua `scripts/run-gate.sh`, mỗi lệnh gate là một đối số: `GATE_LOG=<file log> scripts/run-gate.sh "<lệnh 1>" "<lệnh 2>"`.
- Mỗi gate là một lệnh đơn. Cấm `|`, `&&`, `;` và `&` trong lệnh gate. Pipe che exit code của lệnh đỏ. Script từ chối với exit 2.
- Đỏ thì dừng. Gửi parent lệnh và output trong log. Không kết luận qua `| tail` hay `| head`.
