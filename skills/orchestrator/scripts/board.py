"""Task board for the orchestrator skill. Single writer: the orchestrator session."""

import json
import os
import re
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

BOARD = Path(".prime/orchestrator/board.json")  # the one and only board path
FLOW = {"pending": "engine", "engine": "review", "review": "done"}
LOG_KEEP = 200  # ponytail: flat list, move to a rotating file if a run outgrows it
SCHEMA_VERSION = 1  # bump when a key changes meaning; load() refuses a board newer than this code


def _new():
    return {"schema_version": SCHEMA_VERSION, "goal": "", "design_dir": "", "gate": [],
            "phases": [], "agents": {}, "models": {}, "deadlines": {}, "heartbeat": "",
            "adr_seq": 0, "log": []}


def load(path=BOARD):
    p = Path(path)
    if not p.exists():
        return _new()
    b = json.loads(p.read_text(encoding="utf-8"))
    v = b.get("schema_version", 0)  # a board written before versioning has none
    assert v <= SCHEMA_VERSION, f"{p}: schema_version {v} is newer than board.py ({SCHEMA_VERSION})"
    for key, default in _new().items():
        b.setdefault(key, default)
    b["schema_version"] = SCHEMA_VERSION
    return b


def save(board, path=BOARD):
    """Atomic: write a tmp file next to the board, then rename over it, so a crash mid-write
    (or a heartbeat reading at that moment) sees the old board or the new one, never half."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    board.setdefault("schema_version", SCHEMA_VERSION)
    board["log"] = board.get("log", [])[-LOG_KEEP:]
    tmp = p.with_name(p.name + ".tmp")  # same directory, so os.replace is a rename, not a copy
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(json.dumps(board, indent=2, ensure_ascii=False))
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, p)
    return p


def log(board, event):
    board.setdefault("log", []).append(
        {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "event": event}
    )


def add_phase(board, title, *, req_ids=(), acceptance=(), gate=()):
    """Add a phase, copied from one `## Phase N` section of the design's phases.md.

    req_ids/acceptance carry the traceability the QC reviewer grades against; gate is the
    phase's own extra command on top of board["gate"]. All optional so a phase can be added
    before its design is written, but a phase with no acceptance gives QC nothing to check.
    """
    phase_id = max((p["id"] for p in board.get("phases", [])), default=0) + 1
    board.setdefault("phases", []).append(
        {
            "id": phase_id,
            "title": title,
            "status": "pending",
            "notes": "",
            "round": 1,
            "req_ids": list(req_ids),
            "acceptance": list(acceptance),
            "phase_gate": list(gate),
        }
    )
    log(board, f"phase {phase_id} added: {title}" + (f" [{', '.join(req_ids)}]" if req_ids else ""))
    return phase_id


def uncovered(board, all_req_ids):
    """Requirements from srs.md that no phase claims - work nobody will do."""
    claimed = {r for p in board.get("phases", []) for r in p.get("req_ids", [])}
    return [r for r in all_req_ids if r not in claimed]


def advance(board, phase_id, *, rework=False, note="", gate=None):
    """Move one phase along pending -> engine -> review -> done.

    rework sends a reviewed phase back to the engine. Entering `done` requires
    `gate`: results of a real run, `[{"cmd": str, "exit": int, "ok": bool}, ...]`.
    A reviewer replying PASS is not a gate - only a command that ran is.
    """
    phase = next(p for p in board["phases"] if p["id"] == phase_id)
    before = phase["status"]
    assert before != "blocked", f"phase {phase_id} is blocked: {phase.get('blocked_reason', '?')}"
    if rework:
        assert before == "review", f"rework only from review, got {before!r}"
        phase["status"] = "engine"
        phase["round"] = phase.get("round", 1) + 1  # a new round gets a new reviewer name
    else:
        assert before in FLOW, f"phase {phase_id} is already {before!r}"
        after = FLOW[before]
        if after == "done":
            assert gate, f"phase {phase_id}: review -> done requires a gate run"
            failed = [g["cmd"] for g in gate if not g.get("ok")]
            assert not failed, f"phase {phase_id}: gate failed: {failed}"
            phase["gate"] = gate
        phase["status"] = after
    if note:
        phase["notes"] = note
    log(board, f"phase {phase_id}: {before} -> {phase['status']}" + (f" ({note})" if note else ""))
    return phase


def block(board, phase_id, reason):
    """Park a phase that cannot proceed. Remembers the status to return to."""
    phase = next(p for p in board["phases"] if p["id"] == phase_id)
    assert phase["status"] != "done", f"phase {phase_id} is already done"
    if phase["status"] != "blocked":
        phase["blocked_from"] = phase["status"]
    phase["status"] = "blocked"
    phase["blocked_reason"] = reason
    log(board, f"phase {phase_id}: {phase['blocked_from']} -> blocked ({reason})")
    return phase


def unblock(board, phase_id, note=""):
    """Return a phase to where it was blocked, once the blocker is actually gone."""
    phase = next(p for p in board["phases"] if p["id"] == phase_id)
    assert phase["status"] == "blocked", f"phase {phase_id} is not blocked"
    phase["status"] = phase.pop("blocked_from", "engine")
    reason = phase.pop("blocked_reason", "")
    if note:
        phase["notes"] = note
    log(board, f"phase {phase_id}: blocked -> {phase['status']} (was: {reason})")
    return phase


def next_phase(board):
    """First phase not done, or None when every phase is finished."""
    return next((p for p in board.get("phases", []) if p["status"] != "done"), None)


def set_deadline(board, child, minutes, now=None):
    """Final-report deadline for a child: absolute, from the machine clock, never a guess.

    Returns the datetime so the caller can print HH:MM for the brief's three milestones.
    """
    due = (now or datetime.now().astimezone()) + timedelta(minutes=minutes)
    board.setdefault("deadlines", {})[child] = due.isoformat(timespec="seconds")
    log(board, f"deadline {child}: {board['deadlines'][child]}")
    return due


def clear_deadline(board, child):
    """Call when the child's FINAL report arrives. The heartbeat watches whatever is left."""
    board.get("deadlines", {}).pop(child, None)


def overdue(board, now=None):
    """Children past their deadline that have not reported: step 2 of the heartbeat ladder."""
    now = now or datetime.now().astimezone()
    return [c for c, d in board.get("deadlines", {}).items() if datetime.fromisoformat(d) < now]


def set_heartbeat(board, hb_id):
    """Record the id of the one watchdog. Start it at init, before dispatching phase 1."""
    assert not board.get("heartbeat"), f"heartbeat already running: {board['heartbeat']}"
    board["heartbeat"] = hb_id
    log(board, f"heartbeat started: {hb_id}")


def clear_heartbeat(board):
    """Return the id to delete. Refuses while a phase is open or a child still owes a report."""
    assert board.get("heartbeat"), "no heartbeat to stop"
    assert next_phase(board) is None, "a phase is not done yet"
    assert not board.get("deadlines"), f"children still running: {sorted(board['deadlines'])}"
    hb, board["heartbeat"] = board["heartbeat"], ""
    log(board, f"heartbeat stopped: {hb}")
    return hb


def next_adr(board, adr_dir="docs/adr"):
    """Next ADR number, handed to ONE brief. Monotonic: never reuses a number the board already
    issued or a file in adr_dir already has, so parallel engines cannot both create 0019-*.
    The number is only reserved once the caller saves the board.
    """
    on_disk = max((int(m.group(1)) for f in Path(adr_dir).glob("*.md")
                   if (m := re.match(r"(\d{4})-", f.name))), default=0)
    board["adr_seq"] = max(board.get("adr_seq", 0), on_disk) + 1
    return f"{board['adr_seq']:04d}"


def _rejects(fn, *args, **kwargs):
    try:
        fn(*args, **kwargs)
    except AssertionError:
        return True
    return False


def _demo_storage():
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "orchestrator" / "board.json"
        b = load(p)
        assert b["schema_version"] == SCHEMA_VERSION and b["deadlines"] == {} and b["adr_seq"] == 0
        b["goal"] = "Gateway giới hạn tốc độ"
        save(b, p)
        assert not p.with_name("board.json.tmp").exists(), "save must leave no tmp file behind"
        assert load(p)["goal"] == b["goal"], "utf-8 must round-trip"

        before, real_replace = p.read_text(encoding="utf-8"), os.replace
        def boom(*_):
            raise OSError("disk full")
        os.replace = boom
        try:
            b["goal"] = "half written"
            save(b, p)
            raise AssertionError("save must propagate a failed rename")
        except OSError:
            pass
        finally:
            os.replace = real_replace
        assert p.read_text(encoding="utf-8") == before, "a failed save must leave the old board intact"

        old = Path(d) / "old.json"
        old.write_text(json.dumps({"goal": "old", "phases": []}))
        legacy = load(old)
        assert legacy["schema_version"] == SCHEMA_VERSION and legacy["adr_seq"] == 0, \
            "a board without schema_version must be backfilled"
        newer = Path(d) / "newer.json"
        newer.write_text(json.dumps({"schema_version": SCHEMA_VERSION + 1}))
        assert _rejects(load, newer), "a board from a newer board.py must be refused"

        b = {"log": [{"event": i} for i in range(LOG_KEEP + 50)]}
        save(b, p)
        assert len(load(p)["log"]) == LOG_KEEP and load(p)["log"][-1]["event"] == LOG_KEEP + 49


def _demo_ops():
    b = _new()
    t0 = datetime(2026, 11, 10, 15, 0).astimezone()
    assert set_deadline(b, "engine-p1", 45, now=t0) == t0 + timedelta(minutes=45)
    assert overdue(b, now=t0 + timedelta(minutes=44)) == []
    assert overdue(b, now=t0 + timedelta(minutes=46)) == ["engine-p1"]
    clear_deadline(b, "engine-p1")
    assert overdue(b, now=t0 + timedelta(hours=9)) == [], "a child that reported is no longer watched"

    assert _rejects(clear_heartbeat, b), "no heartbeat to stop"
    set_heartbeat(b, "hb-1")
    assert _rejects(set_heartbeat, b, "hb-2"), "only one heartbeat"
    ph = add_phase(b, "p", req_ids=["REQ-001"])
    assert _rejects(clear_heartbeat, b), "must not stop while a phase is open"
    advance(b, ph); advance(b, ph)
    advance(b, ph, gate=[{"cmd": "x", "exit": 0, "ok": True}])
    set_deadline(b, "documenter", 20, now=t0)
    assert _rejects(clear_heartbeat, b), "must not stop while a child still owes a report"
    clear_deadline(b, "documenter")
    assert clear_heartbeat(b) == "hb-1" and b["heartbeat"] == ""

    with tempfile.TemporaryDirectory() as d:
        for name in ("0001-a.md", "0007-b.md", "README.md"):
            (Path(d) / name).write_text("x")
        assert next_adr(b, d) == "0008", "must continue after the highest ADR on disk"
        assert next_adr(b, d) == "0009", "the same number must never be issued twice"
        b["adr_seq"] = 20
        assert next_adr(b, d) == "0021", "the board counter wins when it is ahead of the disk"
    assert next_adr(_new(), "/nonexistent/adr") == "0001", "a missing adr_dir means no ADR yet"


def demo():
    b = {"goal": "g", "design_dir": "docs/design/x", "gate": ["pytest -q"], "phases": [],
         "agents": {}, "models": {}, "log": []}
    one = add_phase(b, "schema", req_ids=["REQ-001"], acceptance=["index exists on merchant_id"])
    two = add_phase(b, "api", req_ids=["REQ-002"])
    assert b["phases"][0]["req_ids"] == ["REQ-001"]
    assert uncovered(b, ["REQ-001", "REQ-002", "REQ-003"]) == ["REQ-003"], \
        "a requirement no phase claims must be reported"
    assert next_phase(b)["id"] == one
    advance(b, one)                                  # pending -> engine
    advance(b, one)                                  # engine  -> review
    advance(b, one, rework=True, note="2 findings")  # review  -> engine
    assert b["phases"][0]["notes"] == "2 findings"
    assert b["phases"][0]["round"] == 2, "a rework round must bump the round counter"
    advance(b, one)                                  # engine  -> review

    assert _rejects(advance, b, one), "done without a gate must fail"
    red = [{"cmd": "pytest -q", "exit": 1, "ok": False}]
    assert _rejects(advance, b, one, gate=red), "done with a failing gate must fail"
    assert b["phases"][0]["status"] == "review", "a rejected advance must not move the phase"

    block(b, one, "cluster unreachable")
    assert b["phases"][0]["status"] == "blocked"
    assert b["phases"][0]["blocked_from"] == "review"
    assert _rejects(advance, b, one, gate=[{"cmd": "x", "exit": 0, "ok": True}]), \
        "a blocked phase must not advance"
    unblock(b, one, note="VPN len lai")
    assert b["phases"][0]["status"] == "review", "unblock must restore the prior status"
    assert "blocked_reason" not in b["phases"][0]
    assert _rejects(unblock, b, one), "unblock on a non-blocked phase must fail"

    green = [{"cmd": "pytest -q", "exit": 0, "ok": True}]
    advance(b, one, gate=green)                      # review  -> done
    assert b["phases"][0]["gate"] == green
    assert next_phase(b)["id"] == two
    assert _rejects(advance, b, one, gate=green), "advancing a done phase must fail"
    assert _rejects(advance, b, two, rework=True), "rework from pending must fail"
    _demo_storage()
    _demo_ops()
    print("ok")


if __name__ == "__main__":
    demo()
