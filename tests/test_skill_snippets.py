"""Chạy nguyên văn các đoạn code trong skills/orchestrator/SKILL.md với kernel giả.

Test là tài liệu: đoạn code trong skill hỏng hoặc lệch hành vi thì test đỏ.
Dùng: python3 tests/test_skill_snippets.py
"""
import ast
import asyncio
import os
import re
import sys
import tempfile
import types
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "skills/orchestrator/scripts"))
import board as bd  # noqa: E402

SKILL = (ROOT / "skills/orchestrator/SKILL.md").read_text(encoding="utf-8")
BLOCKS = re.findall(r"```python\n(.*?)```", SKILL, re.S)


def block(needle):
    hits = [b for b in BLOCKS if needle in b]
    assert len(hits) == 1, f"cần đúng 1 khối python chứa {needle!r}, có {len(hits)}"
    return hits[0]


def run(src, ns):
    """exec cho phép top-level await, như kernel của Prime Agent."""
    result = eval(compile(src, "<SKILL.md>", "exec", flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT), ns)
    if result is not None:
        asyncio.run(result)


calls = {"heartbeat": [], "spawn": [], "send": [], "existing": []}


class FakeHeartbeat:
    async def create(self, instruction, interval=None, label=None, delivery_mode=None):
        calls["heartbeat"].append(dict(instruction=instruction, interval=interval, label=label,
                                       delivery_mode=delivery_mode))
        return {"heartbeat": {"id": "hb-1"}}


class FakeRlm:
    async def list_subagents(self):
        return [types.SimpleNamespace(session_name=n) for n in calls["existing"]]

    async def spawn(self, prompt, *, name, model=None, thinking=None):
        calls["spawn"].append(dict(prompt=prompt, name=name, model=model, thinking=thinking))


class FakeMessage:
    async def send(self, message, *, receiver_role, receiver_name):
        calls["send"].append(dict(message=message, role=receiver_role, name=receiver_name))


def test_heartbeat_snippet():
    ns = {"bd": bd, "b": bd.load(Path("/nonexistent/board.json")), "rlm_heartbeat": FakeHeartbeat()}
    run(block("WATCH_INSTRUCTION = "), ns)  # NameError nếu WATCH_INSTRUCTION không được định nghĩa
    hb = calls["heartbeat"][0]
    assert hb["interval"] == "5m" and hb["delivery_mode"] == "follow_up", hb
    for must in ("bd.load()", "bd.overdue(b)", "agent_observe.get_agent", "agent_observe.recent_messages",
                 "ps -Ao pid,etime,pcpu,command", "kill the process, never the child", "ONE message",
                 "more than 10 minutes", "bd.block(b, phase_id, reason)", "Never delete the child"):
        assert must in hb["instruction"], f"WATCH_INSTRUCTION thiếu: {must}"
    assert ns["b"]["heartbeat"] == "hb-1", "id heartbeat phải nằm trên board"
    assert bd.load()["heartbeat"] == "hb-1", "và phải được save xuống đĩa"


def test_dispatch_snippet():
    code = "\n".join(block(n) for n in ("def child_name", "FRAME = ", "async def dispatch"))
    ns = {"rlm": FakeRlm(), "agent_message": FakeMessage(), "ROLE_PROMPT": {"engine": "ROLE-ENGINE"}}
    exec(code, ns)
    b, phase = bd.load(Path("/nonexistent/board.json")), {"id": 3, "round": 1}

    try:
        asyncio.run(ns["dispatch"]("engine", phase, "BRIEF", b))
        raise AssertionError("dispatch phải từ chối khi chưa có heartbeat")
    except AssertionError as e:
        assert "heartbeat" in str(e), e
    assert not calls["spawn"] and not b["deadlines"] and not b["agents"], "bị từ chối thì không được ghi gì"

    bd.set_heartbeat(b, "hb-1")
    assert asyncio.run(ns["dispatch"]("engine", phase, "BRIEF", b)) == "engine-p3"
    sp = calls["spawn"][0]
    for must in ("ROLE-ENGINE", "BRIEF", "DEADLINE (giờ máy", "perl -e 'alarm", "-m 10", "KHÔNG sinh child con"):
        assert must in sp["prompt"], f"thiếu trong brief: {must}"
    assert "{tz}" not in sp["prompt"], "placeholder của FRAME chưa được điền"
    saved = bd.load()
    assert saved["agents"]["engine"] == "engine-p3" and "engine-p3" in saved["deadlines"]
    hhmm = re.search(r"báo cáo cuối chậm nhất lúc (\d\d:\d\d)", sp["prompt"]).group(1)
    assert saved["deadlines"]["engine-p3"][11:16] == hhmm, "giờ trong brief phải khớp giờ trên board"

    calls["existing"] = ["engine-p3"]  # vòng sửa: dùng lại child, gửi deadline mới
    asyncio.run(ns["dispatch"]("engine", phase, "REWORK", b))
    assert len(calls["spawn"]) == 1 and calls["send"][0]["role"] == "child"
    assert "DEADLINE (giờ máy" in calls["send"][0]["message"]


if __name__ == "__main__":
    start = os.getcwd()
    with tempfile.TemporaryDirectory() as tmp:
        os.chdir(tmp)  # bd.save ghi .prime/orchestrator/board.json theo cwd
        try:
            test_heartbeat_snippet()
            test_dispatch_snippet()
        finally:
            os.chdir(start)
    print("skill snippets ok")
