"""Hợp đồng vai: verdict của reviewer và bước dự thảo của engine phải khớp ở MỌI nơi định nghĩa chúng.

Nguồn thật của verdict là bd.VERDICTS (Loop đọc bằng bd.parse_verdict). SKILL.md, brief mẫu và 02 phải dùng đúng
các token đó. Dùng: python3 tests/test_role_contracts.py
"""
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "skills/orchestrator/scripts"))
import board as bd  # noqa: E402


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


SKILL = read("skills/orchestrator/SKILL.md")
DOC02 = read("02-vai-tro-va-brief.md")


def skill_prompt(role):
    m = re.search(rf"- \*\*{re.escape(role)}\*\*: `\"(.*?)\"`", SKILL, re.S)
    assert m, f"không thấy prompt vai {role} trong SKILL.md"
    return m.group(1)


def doc02_block(heading):
    start = DOC02.index(f"### {heading}\n")
    return DOC02[start: DOC02.index("\n### ", start + 1)]


errors = []


def need(where, text, *musts):
    for must in musts:
        if must not in text:
            errors.append(f"{where}: thiếu {must!r}")


# --- verdict: mọi nơi dùng đúng token của bd.VERDICTS
SOURCES = {
    "qc": {"SKILL.md prompt": skill_prompt("qc"), "mau/brief-qc.md": read("mau/brief-qc.md"), "02 khối qc": doc02_block("qc")},
    "qc2": {"SKILL.md prompt": skill_prompt("qc2"), "mau/brief-qc2.md": read("mau/brief-qc2.md"), "02 khối qc2": doc02_block("qc2")},
    "code-reviewer": {"SKILL.md prompt": skill_prompt("code-reviewer"), "mau/brief-code-review.md": read("mau/brief-code-review.md"),
                      "02 khối code-review": doc02_block("code-review")},
}
for role, places in SOURCES.items():
    for where, text in places.items():
        need(f"{role} / {where}", text, *(f"VERDICT: {tok}" for tok in bd.VERDICTS[role]))
for where, text in (("mau/brief-code-review.md", SOURCES["code-reviewer"]["mau/brief-code-review.md"]),
                    ("02 khối code-review", SOURCES["code-reviewer"]["02 khối code-review"])):
    need(where, text, "Verdict: Ship", "bd.parse_verdict")  # brief thắng định dạng gốc của ponytail-review
if "either PASS" in skill_prompt("code-reviewer"):
    errors.append("SKILL.md: code-reviewer còn hợp đồng cũ 'either PASS'")

# --- Loop và bảng vai nói đúng token, LANG không để child dịch token reviewer
need("SKILL.md Loop", SKILL, "bd.parse_verdict", "`ValueError`",
     "qc PASS **and** qc2 PASS **and** code-reviewer APPROVE -> run the gate (shared + `phase_gate`),",
     "qc FAIL **or** qc2 FAIL **or** code-reviewer REQUEST_CHANGES -> `advance(b, id, rework=True, note=...)`",
     "dispatch `qc`, `qc2` **and** `code-reviewer` in the same turn",
     "A final report you accept** -> first `bd.clear_deadline(b, <that child's name>)`",
     "answer it with `dispatch(...)`", "`dispatch` the same child the exact format")
if "Both `PASS`" in SKILL:
    errors.append("SKILL.md Loop: còn 'Both `PASS`'")
need("SKILL.md bảng vai", SKILL, "`VERDICT: APPROVE` or `VERDICT: REQUEST_CHANGES`", "`VERDICT: PASS` or `VERDICT: FAIL`")
need("SKILL.md LANG", SKILL, "APPROVE, REQUEST_CHANGES")

# --- engine: bước dự thảo có mặt ở prompt vai, brief mẫu và 02
ENGINE = {"SKILL.md prompt": skill_prompt("engine"), "mau/brief-engine.md": read("mau/brief-engine.md"),
          "02 khối engine": doc02_block("engine")}
need("engine / SKILL.md prompt", ENGINE["SKILL.md prompt"], "first line PROGRESS, second line DRAFT: <draft path>", "1500",
     "advisor unavailable", "STOP")
for where in ("mau/brief-engine.md", "02 khối engine"):
    need(f"engine / {where}", ENGINE[where], "dòng đầu `PROGRESS`, dòng hai `DRAFT: <đường dẫn dự thảo>`", "1500", "advisor unavailable")

# --- quy tắc chung "block phase" phải có ngoại lệ advisor (ADR-0002), kể cả trong bảng token và thang heartbeat
row = next(line for line in DOC02.splitlines() if line.startswith("| `BLOCKED` |"))
need("02 bảng token, dòng BLOCKED", row, "Riêng advisor", "bd.advisor_unavailable")
need("02 bảng token, dòng PROGRESS", next(line for line in DOC02.splitlines() if line.startswith("| `PROGRESS` |")),
     "`DRAFT:", "dispatch_advisor")
need("01 thang heartbeat", next(line for line in read("01-quy-trinh.md").splitlines() if "Lần heartbeat kế tiếp vẫn im" in line),
     "Riêng advisor", "bd.advisor_unavailable")

# --- qc2 cùng model với qc: không có mục riêng trong models.json, và pick() phân giải cả hai vai
import json as _json
_models = _json.loads(read("skills/orchestrator/models.json"))
if _models["roles"].get("qc2") != _models["roles"].get("qc"):
    errors.append("models.json: qc2 phải cùng model với qc (người dùng chốt 11/11/2026)")
need("SKILL.md pick()", SKILL, '"qc", "qc2", "code-reviewer"')
need("SKILL.md BUDGET_MIN", SKILL, '"qc2": 20')

if errors:
    sys.exit("\n".join(errors))
print("role contracts ok")
