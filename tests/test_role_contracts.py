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
need("SKILL.md Loop", SKILL, "bd.parse_verdict", "`ValueError`", "qc PASS **and** code-reviewer APPROVE",
     "qc FAIL **or** code-reviewer REQUEST_CHANGES")
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

if errors:
    sys.exit("\n".join(errors))
print("role contracts ok")
