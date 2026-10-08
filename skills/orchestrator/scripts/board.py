"""Task board for the orchestrator skill. Single writer: the orchestrator session."""

import json
from datetime import datetime, timezone
from pathlib import Path

BOARD = Path(".prime/orchestrator/board.json")
FLOW = {"pending": "engine", "engine": "review", "review": "done"}
LOG_KEEP = 200  # ponytail: flat list, move to a rotating file if a run outgrows it


def load(path=BOARD):
    p = Path(path)
    if not p.exists():
        return {"goal": "", "design_dir": "", "gate": [], "phases": [],
                "agents": {}, "models": {}, "log": []}
    return json.loads(p.read_text())


def save(board, path=BOARD):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    board["log"] = board.get("log", [])[-LOG_KEEP:]
    p.write_text(json.dumps(board, indent=2, ensure_ascii=False))
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


def _rejects(fn, *args, **kwargs):
    try:
        fn(*args, **kwargs)
    except AssertionError:
        return True
    return False


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
    print("ok")


if __name__ == "__main__":
    demo()
