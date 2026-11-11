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
        if calls.get("spawn_error"):
            raise RuntimeError(calls["spawn_error"])
        calls["spawn"].append(dict(prompt=prompt, name=name, model=model, thinking=thinking))


class FakeMessage:
    async def send(self, message, *, receiver_role, receiver_name):
        if calls.get("send_error"):
            raise RuntimeError(calls["send_error"])
        calls["send"].append(dict(message=message, role=receiver_role, name=receiver_name))


def test_heartbeat_snippet():
    ns = {"bd": bd, "b": bd.load(Path("/nonexistent/board.json")), "rlm_heartbeat": FakeHeartbeat()}
    run(block("WATCH_INSTRUCTION = "), ns)  # NameError nếu WATCH_INSTRUCTION không được định nghĩa
    hb = calls["heartbeat"][0]
    assert hb["interval"] == "5m" and hb["delivery_mode"] == "follow_up", hb
    for must in ("bd.load()", "bd.overdue(b)", "agent_observe.get_agent", "agent_observe.recent_messages",
                 "ps -Ao pid,etime,pcpu,command", "kill the process, never the child", "ONE message",
                 "more than 10 minutes", "bd.block(b, phase_id, reason)", "Never delete the child",
                 "bd.advisor_unavailable(b, phase_id, reason)", "Never bd.block for the advisor"):
        assert must in hb["instruction"], f"WATCH_INSTRUCTION thiếu: {must}"
    assert ns["b"]["heartbeat"] == "hb-1", "id heartbeat phải nằm trên board"
    assert bd.load()["heartbeat"] == "hb-1", "và phải được save xuống đĩa"


def test_dispatch_snippet():
    code = "\n".join(block(n) for n in ("def child_name", "FRAME = ", "async def dispatch(role"))
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


def test_advisor_snippet():
    code = "\n".join(block(n) for n in ("def child_name", "FRAME = ", "async def dispatch(role", "async def dispatch_advisor"))
    ns = {"rlm": FakeRlm(), "agent_message": FakeMessage(), "bd": bd,
          "ROLE_PROMPT": {"engine": "ROLE-ENGINE", "advisor": "ROLE-ADVISOR"}}
    exec(code, ns)
    b = bd.load(Path("/nonexistent/board.json"))
    bd.add_phase(b, "p", req_ids=["REQ-001"])
    bd.set_heartbeat(b, "hb-1")
    b["models"] = {"advisor": "xai/grok-4.7"}
    ph = b["phases"][0]
    for k in ("spawn", "send"):
        calls[k].clear()
    calls["existing"], calls["spawn_error"] = [], None

    assert ns["child_name"]("advisor", {"id": 1, "round": 2}) == "advisor-p1-draft", "advisor name has no round"
    assert ns["child_name"]("qc", {"id": 1, "round": 2}) == "qc-p1-r2"
    draft = Path("draft.md")
    draft.write_text("kế hoạch một", encoding="utf-8")

    asyncio.run(ns["dispatch_advisor"](ph, draft, "BRIEF", b))
    sp = calls["spawn"][0]
    assert sp["name"] == "advisor-p1-draft" and sp["model"] == "xai/grok-4.7" and sp["thinking"] == "xhigh", sp
    assert (ph["status"], ph["round"]) == ("pending", 1), "advisor must not move status or round"
    assert "advisor-p1-draft" in b["deadlines"]

    assert asyncio.run(ns["dispatch_advisor"](ph, draft, "BRIEF", b)) is None
    assert len(calls["spawn"]) == 1 and not calls["send"], "same draft: nothing is dispatched"
    ph["status"] = "review"
    bd.advance(b, 1, rework=True, note="qc FAIL")
    assert ph["round"] == 2
    assert asyncio.run(ns["dispatch_advisor"](ph, draft, "BRIEF", b)) is None
    assert len(calls["spawn"]) == 1 and not calls["send"], "a rework round after FAIL must not re-run the advisor"

    draft.write_text("kế hoạch hai", encoding="utf-8")
    calls["existing"] = ["advisor-p1-draft"]
    asyncio.run(ns["dispatch_advisor"](ph, draft, "BRIEF-2", b))
    assert len(calls["spawn"]) == 1 and calls["send"][0]["name"] == "advisor-p1-draft", "new draft reuses the advisor by name"

    draft.write_text("từ " * 1501, encoding="utf-8")
    try:
        asyncio.run(ns["dispatch_advisor"](ph, draft, "BRIEF-3", b))
        raise AssertionError("a draft over 1500 words must be refused")
    except AssertionError as e:
        assert "1501 words" in str(e), e

    # host từ chối xhigh: phase không bị block, ghi notes + log, bỏ deadline của advisor
    draft.write_text("kế hoạch ba", encoding="utf-8")
    calls["existing"], calls["spawn_error"] = [], "host rejects thinking=xhigh"
    ph["status"], before = "engine", dict(ph)
    assert asyncio.run(ns["dispatch_advisor"](ph, draft, "BRIEF-4", b)) is None
    assert ph["status"] == "engine" and ph["round"] == before["round"] and "blocked_reason" not in ph
    assert "advisor unavailable: RuntimeError: host rejects thinking=xhigh" in ph["notes"]
    assert "advisor-p1-draft" not in b["deadlines"], "deadline of an unavailable advisor must be gone"
    assert "advisor unavailable" in bd.load()["log"][-1]["event"], "and it must be saved to disk"

    calls["spawn_error"] = None
    asyncio.run(ns["dispatch"]("engine", ph, "BRIEF-E", b))
    assert calls["spawn"][-1]["thinking"] is None, "only the advisor forces a thinking level"


def test_dispatch_failures():
    code = "\n".join(block(n) for n in ("def child_name", "FRAME = ", "async def dispatch(role"))
    ns = {"rlm": FakeRlm(), "agent_message": FakeMessage(), "ROLE_PROMPT": {"engine": "ROLE-ENGINE"}}
    exec(code, ns)
    for role in ("qc2", "research", "enginee"):
        try:
            ns["child_name"](role, {"id": 1, "round": 1})
            raise AssertionError(f"unknown role {role!r} must not fall back to the engine's name")
        except ValueError:
            pass
    assert ns["child_name"]("qc", {"id": 1}) == "qc-p1-r1", "a phase without round is round 1"

    b = bd.load(Path("/nonexistent/board.json"))
    bd.set_heartbeat(b, "hb-1")
    calls["existing"], calls["spawn_error"] = [], "provider down"
    try:
        asyncio.run(ns["dispatch"]("engine", {"id": 9, "round": 1}, "BRIEF", b))
        raise AssertionError("a failed spawn must raise")
    except RuntimeError:
        pass
    calls["spawn_error"] = None
    assert "engine-p9" not in b["deadlines"], "a child that never got the brief must not owe a report"

    bd.set_deadline(b, "engine-p9", 45)
    before = b["deadlines"]["engine-p9"]
    calls["existing"], calls["send_error"] = ["engine-p9"], "send failed"
    try:
        asyncio.run(ns["dispatch"]("engine", {"id": 9, "round": 1}, "REWORK", b))
        raise AssertionError("a failed send must raise")
    except RuntimeError:
        pass
    calls["send_error"], calls["existing"] = None, []
    assert b["deadlines"].get("engine-p9") == before, "a reused child still owes its earlier report"


def test_run_gate_snippet():
    import shutil, subprocess
    Path("scripts").mkdir(exist_ok=True)
    shutil.copy(ROOT / "scripts" / "run-gate.sh", "scripts/run-gate.sh")

    async def bash(cmd):
        return subprocess.run(["bash", "-c", cmd], capture_output=True, text=True)

    for shared, own, want in ((["true"], ["true"], "done"), (["true"], ["false"], "review"), (["false"], ["true"], "review")):
        b = bd.load(Path("/nonexistent/board.json"))
        b["gate"] = shared
        pid = bd.add_phase(b, "p", gate=own)
        bd.advance(b, pid); bd.advance(b, pid)
        ns = {"bd": bd, "b": b, "bash": bash, "phase": b["phases"][0], "phase_id": pid}
        run(block("async def run_gate"), ns)   # nguyên văn trong SKILL.md; gate đỏ không được ném lỗi
        assert b["phases"][0]["status"] == want, (shared, own, b["phases"][0]["status"])


if __name__ == "__main__":
    start = os.getcwd()
    with tempfile.TemporaryDirectory() as tmp:
        os.chdir(tmp)  # bd.save ghi .prime/orchestrator/board.json theo cwd
        try:
            test_heartbeat_snippet()
            test_dispatch_snippet()
            test_advisor_snippet()
            test_dispatch_failures()
            test_run_gate_snippet()
        finally:
            os.chdir(start)
    print("skill snippets ok")
