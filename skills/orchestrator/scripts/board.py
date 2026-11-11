"""Task board for the orchestrator skill. Single writer: the orchestrator session."""

import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

if not __debug__:  # mọi kiểm tra của board là assert; python -O gỡ hết chúng và board nhận mọi chuyển trạng thái
    raise RuntimeError("board.py cần assert: không chạy với python -O hay PYTHONOPTIMIZE")

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
    # Same directory, so os.replace is a rename. A unique name per write: two writers never share a tmp file.
    fd, tmp = tempfile.mkstemp(dir=p.parent, prefix=p.name + ".", suffix=".tmp")
    try:
        os.chmod(tmp, (p.stat().st_mode & 0o777) if p.exists() else 0o644)  # mkstemp makes 0600; keep the board's mode
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(json.dumps(board, indent=2, ensure_ascii=False))
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, p)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
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
            # Trust the command's exit code, not the caller's `ok`, and demand the whole configured gate ran.
            failed = [g["cmd"] for g in gate if g.get("exit") != 0]
            assert not failed, f"phase {phase_id}: gate failed: {failed}"
            ran = {g["cmd"] for g in gate}
            missing = [c for c in board.get("gate", []) + phase.get("phase_gate", []) if c not in ran]
            assert not missing, f"phase {phase_id}: gate not run: {missing}"
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


def advisor_draft(board, phase_id, draft_path, max_words=1500):
    """True when this draft has not gone to the advisor yet (and records it), False for one already sent.

    The advisor is advice, not a board state: this never touches status or round, so a rework round after a
    qc/code-review FAIL (same draft) can never re-dispatch it. A draft over max_words is refused.
    """
    text = Path(draft_path).read_text(encoding="utf-8")
    words = len(text.split())
    assert words <= max_words, f"draft {draft_path} has {words} words, limit {max_words}: send it back to be cut"
    phase = next(p for p in board["phases"] if p["id"] == phase_id)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    if phase.get("advisor_draft") == digest:
        return False
    phase["advisor_draft"] = digest
    log(board, f"phase {phase_id}: advisor draft {digest} ({words} words)")
    return True


def advisor_unavailable(board, phase_id, reason):
    """The advisor could not run (host refuses xhigh, provider down, silent): note it and let the engine go on.

    Never blocks the phase: no status change, no block(). Also drops the advisor's deadline so the heartbeat
    stops watching it.
    """
    phase = next(p for p in board["phases"] if p["id"] == phase_id)
    note = f"advisor unavailable: {reason}"
    phase["notes"] = f"{phase['notes']}; {note}" if phase.get("notes") else note
    clear_deadline(board, f"advisor-p{phase_id}-draft")  # same name as child_name("advisor", phase) in SKILL.md
    log(board, f"phase {phase_id}: {note}")


VERDICTS = {"qc": {"PASS": True, "FAIL": False},
            "code-reviewer": {"APPROVE": True, "REQUEST_CHANGES": False}}


def parse_verdict(role, text):
    """Read a reviewer's reply by machine: True = passes the phase, False = asks for changes.

    The reply must carry exactly one line `VERDICT: <TOKEN>` (upper case, nothing after the token), and the token
    must belong to the role: qc PASS|FAIL, code-reviewer APPROVE|REQUEST_CHANGES. Anything else raises
    ValueError - that reply is NOT a pass: send the same child the format and wait. ponytail-review's own
    `Verdict: Ship.` is deliberately not accepted.
    """
    allowed = VERDICTS[role]
    text = text.replace("\r\n", "\n").replace("\r", "\n").lstrip("\ufeff")  # CRLF, BOM from other tools
    first = next((line.strip().strip("*`").strip() for line in text.splitlines() if line.strip()), "")
    if not re.match(r"(DONE|DONE_WITH_CONCERNS)(?=$|[\s:.,])", first):
        raise ValueError(f"{role}: a verdict needs a final report starting with DONE or DONE_WITH_CONCERNS, got {first[:40]!r}")
    body = re.sub(r"^(```|~~~).*?^\1", "", text, flags=re.M | re.S)  # a VERDICT line inside a code fence is not one
    found = {m.group(1) for m in re.finditer(r"^VERDICT: (\S+)[ \t]*$", body, re.M)}
    if len(found) != 1 or next(iter(found)) not in allowed:
        raise ValueError(f"{role}: need exactly one `VERDICT: {'|'.join(allowed)}` line, got {sorted(found) or 'none'}")
    return allowed[found.pop()]


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
        assert not list(p.parent.glob("*.tmp")), "save must leave no tmp file behind"
        assert load(p)["goal"] == b["goal"], "utf-8 must round-trip"
        assert p.stat().st_mode & 0o777 == 0o644, "a new board is 0644, not mkstemp's 0600"
        p.chmod(0o640)
        save(b, p)
        assert p.stat().st_mode & 0o777 == 0o640, "saving keeps the board's existing mode"

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
        assert not list(p.parent.glob("*.tmp")), "a failed save must not leave its tmp file"

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

    b2 = _new()
    b2["gate"] = ["a"]
    pg = add_phase(b2, "p", gate=["b"])
    advance(b2, pg); advance(b2, pg)
    assert _rejects(advance, b2, pg, gate=[{"cmd": "a", "exit": 0, "ok": True}]), "the phase gate must run too"
    advance(b2, pg, gate=[{"cmd": "a", "exit": 0, "ok": True}, {"cmd": "b", "exit": 0, "ok": True}])
    assert b2["phases"][0]["status"] == "done"

    with tempfile.TemporaryDirectory() as d:
        for name in ("0001-a.md", "0007-b.md", "README.md"):
            (Path(d) / name).write_text("x")
        assert next_adr(b, d) == "0008", "must continue after the highest ADR on disk"
        assert next_adr(b, d) == "0009", "the same number must never be issued twice"
        b["adr_seq"] = 20
        assert next_adr(b, d) == "0021", "the board counter wins when it is ahead of the disk"
    assert next_adr(_new(), "/nonexistent/adr") == "0001", "a missing adr_dir means no ADR yet"


def _demo_advisor():
    b = _new()
    one = add_phase(b, "p", req_ids=["REQ-001"])
    with tempfile.TemporaryDirectory() as d:
        draft = Path(d) / "draft.md"
        draft.write_text("kế hoạch một", encoding="utf-8")
        assert advisor_draft(b, one, draft) is True, "first draft goes to the advisor"
        assert advisor_draft(b, one, draft) is False, "the same draft must not be sent twice"
        advance(b, one); advance(b, one)  # engine -> review
        advance(b, one, rework=True, note="qc FAIL")
        assert advisor_draft(b, one, draft) is False, "a rework round after a FAIL is not a new draft"
        assert b["phases"][0]["round"] == 2 and b["phases"][0]["status"] == "engine", \
            "advisor_draft must leave status and round to the reviewers"
        draft.write_text("kế hoạch hai", encoding="utf-8")
        assert advisor_draft(b, one, draft) is True, "a rewritten draft is new"
        draft.write_text("từ " * 1501, encoding="utf-8")
        assert _rejects(advisor_draft, b, one, draft), "a draft over 1500 words must be refused"
        assert advisor_draft(b, one, draft, max_words=2000) is True, "the ceiling is a parameter"

    set_deadline(b, "advisor-p1-draft", 20)
    ph = b["phases"][0]
    before = (ph["status"], ph["round"])
    advisor_unavailable(b, one, "host rejects xhigh")
    assert (ph["status"], ph["round"]) == before, "advisor unavailable must not move or block the phase"
    assert "blocked_reason" not in ph and ph["notes"].endswith("advisor unavailable: host rejects xhigh")
    assert "advisor-p1-draft" not in b["deadlines"], "the heartbeat must stop watching a dead advisor"
    assert "advisor unavailable" in b["log"][-1]["event"]
    advisor_unavailable(b, one, "provider down")
    assert ph["notes"].count("advisor unavailable") == 2, "notes accumulate, never overwrite"


def _demo_verdict():
    assert parse_verdict("qc", "DONE\nVERDICT: PASS\nREQ-001 PASS") is True
    assert parse_verdict("qc", "DONE\nVERDICT: FAIL\nREQ-001 FAIL thiếu index") is False
    assert parse_verdict("code-reviewer", "DONE\nMở đầu.\nVERDICT: APPROVE\n") is True
    assert parse_verdict("code-reviewer", "DONE\nVERDICT: REQUEST_CHANGES  \n1. Lỗi") is False
    assert parse_verdict("qc", "DONE\nVERDICT: PASS\nVERDICT: PASS") is True, "the same line twice is one verdict"
    assert parse_verdict("qc", "DONE_WITH_CONCERNS\nVERDICT: PASS") is True
    for lead in ("  DONE", "\ufeffDONE", "**DONE**", "`DONE`", "DONE: xong phase 2", "\nDONE"):
        assert parse_verdict("qc", lead + "\nVERDICT: PASS") is True, f"a real reviewer may start with {lead!r}"
    assert parse_verdict("qc", "DONE\r\nVERDICT: PASS\r\n") is True, "CRLF line endings"
    assert parse_verdict("qc", "DONE\nVERDICT: FAIL\n```\nVERDICT: PASS\n```") is False, "a fenced line does not count"
    for role, text, why in (
        ("code-reviewer", "DONE\nVERDICT: PASS", "PASS is not a code-reviewer token"),
        ("qc", "DONE\nVERDICT: APPROVE", "APPROVE is not a qc token"),
        ("code-reviewer", "DONE\nVerdict: Ship.", "ponytail-review's native verdict is not accepted"),
        ("qc", "DONE\nREQ-001 PASS", "per-REQ lines are not a verdict"),
        ("qc", "DONE\nVERDICT: PASS\nVERDICT: FAIL", "two different verdicts"),
        ("qc", "DONE\nVERDICT: PASS.", "trailing text after the token"),
        ("qc", "DONE\n- `VERDICT: PASS` hoặc `VERDICT: FAIL`", "an echoed instruction is not a verdict"),
        ("qc", "", "empty reply"),
        ("qc", "BLOCKED\nVERDICT: PASS", "a BLOCKED report is not a verdict"),
        ("qc", "PROGRESS\nVERDICT: PASS", "a PROGRESS line is not a final report"),
        ("qc", "DONE\n```\nVERDICT: PASS\n```\nREQ-1 FAIL", "the only VERDICT line is inside a code fence"),
        ("qc", "DONE\n~~~\nVERDICT: PASS\n~~~\nREQ-1 FAIL", "a ~~~ fence is a code fence too"),
        ("qc", "DONE-ish\nVERDICT: PASS", "DONE-ish is not DONE"),
        ("qc", "DONE\nReviewer nói VERDICT: PASS", "a mention in the middle of a line is not a verdict"),
        ("qc", "DONE\nVERDICT: PASS kèm ghi chú", "words after the token"),
        ("qc", "DONE\nverdict: PASS", "lower case keyword"),
        ("qc", "DONE\nVerdict: PASS", "mixed case keyword"),
    ):
        assert _rejects_value(parse_verdict, role, text), why


def _rejects_value(fn, *args):
    try:
        fn(*args)
    except ValueError:
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

    lying = [{"cmd": "pytest -q", "exit": 1, "ok": True}]
    assert _rejects(advance, b, one, gate=lying), "the exit code wins over a caller's ok=True"
    assert _rejects(advance, b, one, gate=[{"cmd": "true", "exit": 0, "ok": True}]), \
        "a gate that skipped the configured commands must fail"
    green = [{"cmd": "pytest -q", "exit": 0, "ok": True}]
    advance(b, one, gate=green)                      # review  -> done
    assert b["phases"][0]["gate"] == green
    assert next_phase(b)["id"] == two
    assert _rejects(advance, b, one, gate=green), "advancing a done phase must fail"
    assert _rejects(advance, b, two, rework=True), "rework from pending must fail"
    _demo_storage()
    _demo_ops()
    _demo_advisor()
    _demo_verdict()
    print("ok")


if __name__ == "__main__":
    import sys
    if sys.argv[1:] not in ([], ["demo"]):
        sys.exit("dùng: board.py [demo]")
    demo()
