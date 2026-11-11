"""Engine bắt buộc dùng skill ponytail mức full ở cả ba nơi engine nhận chỉ dẫn.

Dùng: python3 tests/test_engine_ponytail.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def engine_block_in_02():
    s = read("02-vai-tro-va-brief.md")
    start = s.index("### engine")
    return s[start: s.index("\n### ", start + 1)]


def engine_prompt_in_skill():
    m = re.search(r"- \*\*engine\*\*: `\"(.*?)\"`", read("skills/orchestrator/SKILL.md"), re.S)
    assert m, "không thấy prompt vai engine trong SKILL.md"
    return m.group(1)


SOURCES = {
    "mau/brief-engine.md": lambda: read("mau/brief-engine.md"),
    "khối engine trong 02-vai-tro-va-brief.md": engine_block_in_02,
    "prompt vai engine trong skills/orchestrator/SKILL.md": engine_prompt_in_skill,
}

bad = []
for name, get in SOURCES.items():
    text = get()
    if "`ponytail`" not in text or "`full`" not in text:
        bad.append(f"{name}: thiếu yêu cầu skill `ponytail` mức `full`")
    if "thắng" not in text and "win over" not in text:
        bad.append(f"{name}: thiếu quy tắc brief thắng skill về định dạng báo cáo và ngôn ngữ")
if bad:
    sys.exit("\n".join(bad))
print("engine ponytail ok")
