"""board.py không được chạy âm thầm sai: gõ nhầm lệnh hay python -O phải dừng. Dùng: python3 tests/test_board_cli.py"""
import subprocess
import sys
from pathlib import Path

BOARD = str(Path(__file__).resolve().parent.parent / "skills/orchestrator/scripts/board.py")
CASES = [  # (mô tả, đối số python, đối số board, exit 0 hay không, chuỗi phải có)
    ("demo xanh", [], ["demo"], True, "ok"),
    ("gõ nhầm tên lệnh", [], ["demoo"], False, "dùng: board.py"),
    ("python -O gỡ assert", ["-O"], ["demo"], False, "không chạy với python -O"),
]
bad = []
for what, py, args, ok, must in CASES:
    r = subprocess.run([sys.executable, "-B", *py, BOARD, *args], capture_output=True, text=True)
    if (r.returncode == 0) != ok or must not in r.stdout + r.stderr:
        bad.append(f"{what}: exit {r.returncode}, output {(r.stdout + r.stderr).strip()[-160:]!r}")
if bad:
    sys.exit("\n".join(bad))
print("board cli ok")
