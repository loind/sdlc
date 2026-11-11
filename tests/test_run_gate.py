"""run-gate.sh không được báo xanh giả. Dùng: python3 tests/test_run_gate.py"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

GATE = str(Path(__file__).resolve().parent.parent / "scripts" / "run-gate.sh")


def run(*cmds, timeout="600"):
    with tempfile.TemporaryDirectory() as d:
        env = {**os.environ, "GATE_LOG": str(Path(d) / "g.log"), "TIMEOUT_SEC": timeout}
        r = subprocess.run(["bash", GATE, *cmds], capture_output=True, text=True, env=env)
        return r.returncode, r.stdout + r.stderr


CASES = [  # (mô tả, đối số, TIMEOUT_SEC, exit mong đợi, chuỗi phải có)
    ("xanh", ("true", "true"), "600", 0, "GATE_GREEN all 2"),
    ("đỏ dừng ở lệnh đầu", ("false", "true"), "600", 1, "GATE_RED at [1]"),
    ("pipe bị từ chối", ("false | tail -5",), "600", 2, "REJECT"),
    ("&& bị từ chối", ("true && false",), "600", 2, "REJECT"),
    ("không có lệnh nào", (), "600", 2, "không có lệnh gate"),
    ("lệnh rỗng", ("",), "600", 2, "lệnh gate rỗng"),
    ("lệnh toàn khoảng trắng", ("   ",), "600", 2, "lệnh gate rỗng"),
    ("xuống dòng che exit code", ("false\ntrue",), "600", 2, "REJECT"),
    ("gate bị comment mất", ("# pytest -q",), "600", 2, "chỉ là comment"),
    ("gate bị comment mất, có khoảng trắng đầu", ("   # pytest -q",), "600", 2, "chỉ là comment"),
    ("lệnh có # ở giữa vẫn chạy", ("echo a#b",), "600", 0, "GATE_GREEN"),
    ("TIMEOUT_SEC không phải số", ("true",), "abc", 2, "TIMEOUT_SEC"),
    ("TIMEOUT_SEC bằng 0", ("true",), "0", 2, "TIMEOUT_SEC"),
    ("hết giờ là đỏ", ("sleep 5",), "1", None, "GATE_RED at [1]"),
]
bad = []
for what, cmds, t, want, must in CASES:
    rc, out = run(*cmds, timeout=t)
    ok = (rc != 0 if want is None else rc == want) and must in out
    if not ok:
        bad.append(f"{what}: cần exit {want} có {must!r}, nhận exit {rc}: {out.strip()[-200:]}")
if bad:
    sys.exit("\n".join(bad))
print("run-gate ok")
