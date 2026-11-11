---
name: orchestrator
description: Execute a design package across agent sessions - engine builds each phase, qc and code-reviewer grade it in parallel, a real gate command closes it, then devops deploys, verifier runs system-wide e2e and security, and documenter updates the docs - all recorded on a persistent task board. Requires a design package from the thinker skill; it does not design the work itself. Use when the user asks to execute or orchestrate a plan across agents, run a build/review/gate loop per phase, coordinate subagents, or check the status of dispatched work.
compatibility: Needs Prime Agent (rlm.spawn, agent_message, agent_observe, rlm_heartbeat), Python 3 for scripts/board.py, git, and a design package written by the thinker skill. Reads models.json for the role-to-model table.
---

# Orchestrator

You **execute a design package**. You do not design the work: the `thinker` skill wrote
`docs/design/<slug>/` - PRD, SRS with a requirement table, C4 views, and `phases.md` holding
the phase split, the requirement ids per phase, the acceptance criteria and the gate commands.
Your job is to run it, gate it on real commands, and record every transition on the board.

You do not write product code yourself.

Per phase: `engine -> (qc || qc2 || code-reviewer) -> gate -> done`. After the last phase:
`devops -> verifier -> documenter`. The next phase starts from the board, not from memory.

| Role | Owns | Runs | Ends its turn by |
|---|---|---|---|
| `engine` | One phase: draft first, then failing test, implement, run the suite | Per phase | A draft (`PROGRESS` + `DRAFT:` line), then phase id + diff summary + handoff note |
| `qc` | Grades the diff against that phase's **acceptance criteria**, one verdict per requirement | Per phase, parallel with code-reviewer | `VERDICT: PASS` or `VERDICT: FAIL`, then one line per requirement |
| `qc2` | The qc brief, same model as qc, own clean session: hunts error branches, edge data, regressions | Per phase, parallel with qc and code-reviewer | `VERDICT: PASS` or `VERDICT: FAIL`, then one line per requirement |
| `code-reviewer` | Correctness + over-engineering review of the diff, via `ponytail-review` | Per phase, parallel with qc | `VERDICT: APPROVE` or `VERDICT: REQUEST_CHANGES`, then numbered findings |
| `devops` | Deploy and infrastructure: image, manifest, rollout. No security judgement | Once, after the last phase | Message to parent with what was deployed and where |
| `verifier` | System-wide e2e + the whole security picture on the deployed build; decides ship / no-ship | Once, after devops | `PASS` or blocking findings |
| `documenter` | Updates `docs/design/<slug>/` and the repo docs to match what actually shipped | Once, last | Message to parent with the files it changed |

`qc` and `code-reviewer` are separate sessions from `engine` and from each other: an agent
reviewing its own diff is not a review, and one session asked for two different judgements gives
you the easier one twice.

`devops` deploys, `verifier` judges. Never let one session do both - the session that deployed
has a reason to call the deploy fine.

## Async contract

Everything between sessions is asynchronous. `await rlm.spawn(...)` returns a handle once the child
is *admitted*; the child's answer never comes back as a return value. It arrives later as a message
(`agent_message`) or as a file. A dispatch therefore always has the same four beats:

1. `dispatch(...)` - hand the brief over, write child + deadline on the board, `bd.save(b)`.
2. End your turn. Do not poll, sleep or `await` anything that waits for the child.
3. Wait for the message. It is your next input.
4. Read its first line (`DONE`, `DONE_WITH_CONCERNS`, `BLOCKED` or `NEEDS_CONTEXT`), advance the board, save.

Who can reach whom (`agent_message.send`: `receiver_role` is `parent`, `sibling` or `child`, and the
last two need `receiver_name`):

| From | To | Allowed |
|---|---|---|
| orchestrator | child | yes: briefs, rework, `NEEDS_CONTEXT` answers, report-now nudges |
| child | parent | yes, and only this: PROGRESS lines and the final report |
| child | sibling | no: qc and code-reviewer must not see each other's reply |
| child | its own child | no, by rule: the platform default would allow it (see Limits), so `FRAME` forbids it |

Every brief carries `FRAME` (see Role briefs): the final report starts with one of four untranslated
tokens; deadlines are absolute times from the machine clock; every command that can hang is bounded
(`timeout` on Linux, `perl -e 'alarm <s>; exec @ARGV' <cmd>` on macOS) and `curl` always has `-m 10`;
free disk is checked before a big build; a child deletes only the project's build cache and Docker
images; secrets are never printed.

## Start: read the design package

**No `phases.md` on disk means you stop.** Look for `docs/design/*/phases.md`; if the user named a
directory, use that one. Nothing there - tell the user to run `/skill:thinker` first and end your turn.
Do not brainstorm, do not invent phases, do not "just start with something obvious". A phase split
you improvise has no requirement ids behind it, so `qc` has nothing to grade and the whole pipeline
degrades to one agent marking its own homework.

With the package in hand, copy it onto the board once - goal, design dir, shared gate, and one
phase per `## Phase N` section with its requirement ids, acceptance criteria and phase gate:

```python
bd.add_phase(b, "schema + index",
             req_ids=["REQ-001", "REQ-002"],
             acceptance=["REQ-001: index exists on merchant_id", "REQ-002: ..."],
             gate=["pytest tests/test_schema.py -q"])
```

Then check nothing fell through: `bd.uncovered(b, all_req_ids_from_srs)` must come back empty.
A requirement no phase claims is work nobody will do - send the list back to the user and stop.

Two things in the package you must still verify yourself, because `thinker` read the repo but did
not run it: every gate command actually runs, and the environment it needs is reachable. A gate
that cannot run is a blocker to raise now, not a surprise in phase 4.

## Gate verification

`phases.md` already names the commands - `thinker` read the repo for them. You do not go looking
for gate commands, and you never invent one: a gate you made up for a repo with no tests passes
forever and proves nothing.

What you do at init is check they are real. Run the shared gate once on a clean tree before
dispatching phase 1. Three outcomes:

- **Green** - proceed.
- **Red on the code** - the repo was already broken before you started. Tell the user; do not send
  an engine to fix something no phase asked for.
- **Cannot run at all** - missing tool, missing credential, unreachable host. That is a blocker on
  the whole run, not on a phase. Report it with the command and its error, and stop.

If the tests cannot run without something deployed, see **When tests need a deployed environment**.

**Last init step: start the heartbeat** (see **Heartbeat and deadlines**), after the shared gate is green and
before `dispatch` is called for phase 1. `dispatch` refuses to run without it.

## Heartbeat and deadlines

A child that goes quiet is the failure this section exists to prevent. Two rules, both mandatory.

**1. Every task carries a hard deadline.** Take the time from the machine clock (`datetime.now()`),
then give the child three absolute times in the brief: a `PROGRESS:` line, the final report, and
cleanup. Record the final-report deadline with `bd.set_deadline(b, child_name, minutes)` (it reads the machine
clock and returns the datetime to print as HH:MM in the brief); `bd.clear_deadline(b, child_name)` when
that child's final report arrives, and `bd.overdue(b)` lists the late ones. Suggested budgets, tune
per repo: engine 45 min per phase, qc and code-reviewer 20 min per round, devops 20, verifier 30,
documenter 20.

- At the deadline the child MUST report: `DONE` if finished; otherwise send what it has as
  `DONE_WITH_CONCERNS` (or `BLOCKED`) plus the list of what is not done. Silence past the
  deadline is a violation, not progress.
- A child that needs more time sends `PROGRESS:` asking for it before the deadline and waits for
  the parent's reply. It never extends itself.
- Every command that may run long is bounded: `timeout <s>`, or on macOS (no `timeout`)
  `perl -e 'alarm <s>; exec @ARGV' <cmd>`. When a reviewer runs OLD code on big input for an A/B
  check, it picks a size where the old code finishes in a few seconds.

**2. A heartbeat checks every child every 5 minutes**, from init until the last child has
reported. Use the agent-internal `rlm-heartbeat` skill (not the user's `/heartbeat`). Start it at
init, before dispatching phase 1, and keep its id on the board. `dispatch` refuses to run until it
is there:

```python
WATCH_INSTRUCTION = """\
Orchestrator watchdog. Run this check once, then stay silent unless something changed.
1. Reload the board from disk: b = bd.load() (`import board as bd` from .agents/skills/orchestrator/scripts if it is not loaded).
2. For every child dispatched and not finally reported - the names in b["deadlines"]; bd.overdue(b) lists the late ones:
   call agent_observe.get_agent(name) and agent_observe.recent_messages(name, limit=6), and compare the age of its last message with its deadline.
3. List processes at >= 90% CPU for more than 5 minutes: ps -Ao pid,etime,pcpu,command
Then act, per child, in this order:
 a. A runaway process of the child (match it to the child's worktree: lsof -p <pid> | grep cwd): kill the process, never the child. Tell the child what was killed and why, and remind it to bound its commands.
 b. Past its deadline, or silent for more than 10 minutes: send ONE message asking for its report now, with what it has.
 c. Still silent at the next heartbeat: bd.block(b, phase_id, reason), bd.save(b), and tell the user. Never delete the child.
    The advisor child (name ends in -draft) is the exception: bd.advisor_unavailable(b, phase_id, reason), bd.save(b), tell the engine to go on. Never bd.block for the advisor.
 d. An engine that sent a DRAFT and waits for the advisor is waiting on the parent, not silent: judge the advisor child instead.
Do not stop this heartbeat while any phase is open or any child owes a report.
Report to the user in Vietnamese with full diacritics, naming the child, the phase and the command or error. Keep status tokens, paths and commands in English.
"""
hb = await rlm_heartbeat.create(WATCH_INSTRUCTION, interval="5m",
                                label="orchestration-watch", delivery_mode="follow_up")
bd.set_heartbeat(b, hb["heartbeat"]["id"])
bd.save(b)
```

`delivery_mode="follow_up"` makes a heartbeat wait for the orchestrator's current turn to finish; the
default, `"steer"`, would interrupt it. `WATCH_INSTRUCTION` is the whole ladder, so a heartbeat turn
needs nothing else in context: a runaway process of the child is killed (never the child), a late or
silent child gets one nudge, a child still silent at the next heartbeat blocks its phase. Children are
kept until the run ends.

The heartbeat stays silent when nothing changed. Stop it only when every phase is `done` and no
child is `running` - devops, verifier and documenter are children too, so it outlives the last
phase:

```python
await rlm_heartbeat.delete(bd.clear_heartbeat(b))   # refuses while a phase is open or a child owes a report
bd.save(b)
```

## Board

`scripts/board.py` owns the board at `.prime/orchestrator/board.json`. You are its only
writer. Load it in the kernel once, then reuse the module:

```python
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(".agents/skills/orchestrator/scripts").resolve()))  # repo-local, cwd = repo root
import board as bd

b = bd.load()
b["goal"] = "..."                       # the Goal line from phases.md
b["design_dir"] = "docs/design/<slug>"  # every child reads the package from here
b["gate"] = ["ruff check .", "pytest -q"]   # the shared Gate block from phases.md
bd.add_phase(b, "schema + index", req_ids=["REQ-001"],
             acceptance=["REQ-001: unique index on (merchant_id, key)"],
             gate=["pytest tests/test_schema.py -q"])
bd.save(b)
```

`req_ids` and `acceptance` are what `qc` grades against - a phase added without them turns qc into
a second code reviewer. `bd.uncovered(b, all_reqs)` lists requirements no phase claims.

Phase flow is `pending -> engine -> review -> done`, with `advance(b, id, rework=True)`
sending a reviewed phase back to the engine. `bd.next_phase(b)` gives the phase to work on.
Save after every transition - the board is the record, your context is not.

`bd.block(b, id, reason)` parks a phase that cannot proceed and remembers where it was;
`bd.unblock(b, id)` returns it there. `advance` refuses a blocked phase, so a parked phase
cannot be closed by accident while the blocker is still there.

The board carries `schema_version`: `load()` backfills keys an older board lacks and refuses a board
written by a newer `board.py`. `save()` is atomic (tmp file, then rename), so a heartbeat reading the
board never sees half a write. `bd.next_adr(b)` hands out the next ADR number and never reuses one the
board issued or `docs/adr/` already holds: give each brief a different number and `bd.save(b)` at once
to reserve it.

## Gate

A phase reaches `done` only when a real command says so. `advance(..., gate=...)` refuses
the transition without passing results, so a reviewer replying `PASS` cannot close a phase
on its own. Detect the repo's own commands once at init and store them on the board:

```python
b["gate"] = ["pytest -q", "ruff check ."]   # read from pyproject / package.json / Makefile
```

Run them yourself after **both** reviewers pass, shared gate first then the phase's own
`phase_gate`, and advance with the combined results:

Every gate command goes through `scripts/run-gate.sh` - never a raw `bash(cmd)`. The runner takes
one simple command per argument and rejects `|`, `&&`, `;` and `&` with exit 2 (a pipe hides the red
command's exit code), bounds each command with `TIMEOUT_SEC` (default 600), writes stdout+stderr to
`GATE_LOG`, and prints `[gate n] EXIT=<code>: <cmd>`. You read that `EXIT=` line, not the shell
status. The script is copied into the target repo (root `README.md`, section Gate).

```python
import re, shlex
from pathlib import Path

async def run_gate(cmd, n):
    log = Path(f".prime/orchestrator/gate-{n}.log")
    log.unlink(missing_ok=True)              # a stale log must never read as a fresh green
    await bash(f"GATE_LOG={log} scripts/run-gate.sh {shlex.quote(cmd)}")
    exits = re.findall(r"^\[gate \d+\] EXIT=(\d+):", log.read_text(), re.M)
    code = int(exits[-1]) if exits else 2    # no EXIT= line (REJECT, crash) is red
    return {"cmd": cmd, "exit": code, "ok": code == 0}

results = []
for n, cmd in enumerate(b["gate"] + phase.get("phase_gate", []), 1):
    results.append(await run_gate(cmd, n))
    if not results[-1]["ok"]:
        break   # fail fast: never spend a long stage on a build that already failed
if results and all(r["ok"] for r in results):
    bd.advance(b, phase_id, gate=results)   # done; raises if a configured command did not run
# else: gate red - send results[-1]["cmd"] and its log to the engine; the phase stays in `review`
```

A phase with no gate command at all can never close: every phase in `phases.md` carries one.

Order the gate cheapest-first so the expensive stage only runs on something already proven.
`advance(..., gate=...)` refuses without passing results, so neither reviewer can close a phase on
its own - and two reviewers passing is still not a gate.
When the sequence needs real logic - parsing a build tag, editing a manifest, waiting on a
rollout - put it in one script the repo owns and make the gate a single command.

A failing gate is engine work, not a review finding: send the failing command and its
output to `engine` and leave the phase in `review` until the rerun is green.

## When tests need a deployed environment

Some projects have nothing meaningful to test locally: the unit of work is an image, a
manifest, a proxy config, and every real test runs against something deployed. There the
deploy belongs *inside* the gate, before the test commands - not in a separate role after
the phase closes. Three invariants, each one a way for a green gate to be a lie:

| Invariant | Why | What a violation looks like |
|---|---|---|
| Pin the exact build, never a floating tag | You must know which build produced a number | Perf numbers that cannot be traced to a build |
| Wait for the rollout before testing | `apply` returns before the new pod serves | Tests pass against the **old** image |
| One deploy at a time | A shared node or port is a single resource | Two phases overwrite each other mid-test |

A gate that deploys is a gate that changes a shared environment, so it stays sequential even
if everything else could run in parallel. Say which environment it targets in the phase notes.

## Model routing

`models.json` (next to `scripts/`) holds the role-to-model table. Resolve the selector at runtime
and store the choice on the board, so every respawn of a role uses the same model:

```python
import json
from pathlib import Path

# find_models returns every match, newest NOT first: "sonnet" gives 4-5, 4-5-20250929, 4-6, 5, so
# taking [0] silently picks 4.5. Match the exact id (and provider when pinned) and demand exactly one.
# models.json (user decision 29/09/2026): engine = deepseek-v4-flash, documenter = gemini-3.8-flash,
# advisor = grok-4.7, every other role = claude-sonnet-5-5. qc2 has no entry on purpose: same model as qc
# (user decision 11/11/2026).
TABLE = json.loads((Path(bd.__file__).parents[1] / "models.json").read_text(encoding="utf-8"))

async def pick(role):
    want = {**TABLE["default"], **TABLE["roles"].get(role, {})}
    hits = [m for m in await rlm.find_models(want["query"], limit=50)   # default limit is 8
            if m.id == want["id"] and m.provider == want.get("provider", m.provider)]
    assert len(hits) == 1, (f"{role}: cần đúng 1 model id={want['id']} provider={want.get('provider', '*')}, "
                            f"thấy {[m.selector for m in hits]}. Ghim `provider` trong models.json")
    return hits[0].selector

b["models"] = {r: await pick(r) for r in
               ("engine", "advisor", "qc", "qc2", "code-reviewer", "devops", "verifier", "documenter")}
```

Never index into `find_models` by position, and never hardcode the selector string either -
pin the model **id** in `models.json` and let `find_models` resolve its provider prefix. A wrong
index fails silently: the child runs an older model and nothing in the board says so. `rlm.spawn`
does not fall back either: an unavailable exact selector fails the spawn.

Children run the per-role model on the board (engine DeepSeek, documenter Gemini, advisor Grok, the rest Sonnet). You keep the session's own model - the strong one - because the
decisions live here: reading two reviewers' findings against each other, deciding rework vs
done, deciding what a verifier finding becomes. A child works one scoped task with a clean context, which is where a fast model holds
up. Leave the board's `models` per-role so one role can be raised later without touching
this skill. `dispatch` (see Resolve or spawn) passes it as `model=b["models"][role]`.

`model` takes an exact `provider/model` selector. `thinking` defaults to the parent level and an
invalid level for that model fails the spawn, so `dispatch` leaves it out and every child
inherits the parent's. The one exception is the advisor (`THINKING`): its skill demands `xhigh`.

## Resolve or spawn

The child's *name* decides what gets reused, so the naming rule carries the context policy:

```python
def child_name(role, phase):
    if role in ("devops", "verifier", "documenter"):
        return role                                        # one session each, once at the end
    if role in ("qc", "qc2", "code-reviewer"):
        return f"{role}-p{phase['id']}-r{phase.get('round', 1)}"   # fresh name every round: never reused
    if role == "advisor":
        return f"advisor-p{phase['id']}-draft"             # no round: advice on a draft, not a review round
    if role == "engine":
        return f"engine-p{phase['id']}"                    # reused across rework rounds, new per phase
    raise ValueError(f"unknown role {role!r}: add it to child_name, BUDGET_MIN and models.json first")
```

Then resolve-or-spawn is a plain lookup - a name that exists is reused, a name that does not
is spawned. `dispatch` is fire-and-forget: it records the child and its deadline, saves the board,
and returns. It never waits for the child.

```python
from datetime import timedelta
import board as bd

BUDGET_MIN = {"engine": 45, "advisor": 20, "qc": 20, "qc2": 20, "code-reviewer": 20, "devops": 20, "verifier": 30,
              "documenter": 20}
THINKING = {"advisor": "xhigh"}   # the advisor skill demands it; every other child inherits the parent level

async def dispatch(role, phase, brief, board):
    assert board.get("heartbeat"), "start the heartbeat first (see Heartbeat and deadlines)"
    name = child_name(role, phase)
    prev = board.get("deadlines", {}).get(name)                 # a reused child may still owe an earlier report
    due = bd.set_deadline(board, name, BUDGET_MIN[role])        # absolute, from the machine clock
    mid, tail = due - timedelta(minutes=BUDGET_MIN[role] / 2), due + timedelta(minutes=5)
    frame = FRAME.format(tz=due.tzname(), progress=f"{mid:%H:%M}",     # FRAME, LANG: see Role briefs
                         final=f"{due:%H:%M}", cleanup=f"{tail:%H:%M}")
    try:
        if any(c.session_name == name for c in await rlm.list_subagents()):
            await agent_message.send(f"{brief}\n\n{frame}", receiver_role="child", receiver_name=name)
        else:
            await rlm.spawn(f"{ROLE_PROMPT[role]}\n\n{brief}\n\n{frame}\n\n{LANG}",
                            name=name, model=board.get("models", {}).get(role),
                            thinking=THINKING.get(role))
    except Exception:
        if prev is None:
            bd.clear_deadline(board, name)   # a child that never got the brief owes no report
        else:
            board["deadlines"][name] = prev  # it still owes the report it had before this failed message
        raise
    board.setdefault("agents", {})[role] = name
    bd.save(board)       # the board is the record, your context is not
    return name          # no child answer exists yet: it arrives later as a message
```

`dispatch` refuses to run until the heartbeat is on the board, so no child is ever dispatched unwatched.
A reused child gets the new deadline in the same message, so the board and the child never disagree.
`rlm.spawn(...)` returns a handle once the child is admitted, never its answer. After `dispatch`,
**end your turn** and wait for the message. Do not poll, do not sleep, do not treat a return value as
the child's result.

**Keep every child until the run ends.** Do not call `rlm.delete_subagent` when a phase is `done`:
the user wants to see every agent that took part, and the trace is in the verdict files and the
ticket. Names are unique per phase and round, so idle children never collide.

**The advisor is advice, not a board state.** The board stays `pending -> engine -> review -> done`. The
advisor scores the engine's draft while the phase is `engine`, before any code is written. It has no round
(its name ends in `-draft`, never `-r<n>`), it never moves `status` or `round`, and it does not count toward the
3-round review limit. A failed advisor never blocks a phase:

```python
async def dispatch_advisor(phase, draft_path, brief, board):
    if not bd.advisor_draft(board, phase["id"], draft_path):   # refuses a draft over 1500 words (AssertionError)
        return None                                            # same draft already sent: nothing to do
    try:
        return await dispatch("advisor", phase, brief, board)
    except Exception as e:                                     # host refuses xhigh, provider down
        bd.advisor_unavailable(board, phase["id"], f"{type(e).__name__}: {e}")
        bd.save(board)
        return None                                            # tell the engine to go on without it
```

`bd.advisor_draft` is what keeps the advisor to one run per draft: a rework round after a qc or
code-review FAIL hands the engine the same draft, so nothing is dispatched.

## Role briefs

Give each child only what its task needs, plus the reply contract. Every brief names
`<design_dir>` so the child reads requirements from the package instead of from your paraphrase.

Append `FRAME` and `LANG` to **every** brief - one place each, so no role can be forgotten.
`dispatch` does it. `FRAME` is the shared safety and reporting contract; the deadline times in it
come from the machine clock through `bd.set_deadline`:

```python
FRAME = """\
BẮT BUỘC TRƯỚC KHI LÀM
- Đọc `CONTEXT.md`, mọi file trong `docs/adr/` và mục "Quy tắc cho agent" trong `CLAUDE.md` hoặc `AGENTS.md`. Việc được giao mâu thuẫn với một ADR: DỪNG, báo parent bằng NEEDS_CONTEXT.

AN TOÀN
- Bọc mọi lệnh có thể treo bằng giới hạn giờ: Linux dùng `timeout <giây> <lệnh>`; macOS không có `timeout`, dùng `perl -e 'alarm <giây>; exec @ARGV' <lệnh>`. `curl` luôn có `-m 10`. Service chạy bằng `docker run -d`. Gate chạy qua `scripts/run-gate.sh` (script đã tự bọc giới hạn giờ).
- Production và hệ thống thật chỉ được ĐỌC (GET). Không tạo, sửa, xoá.
- Không in mật khẩu, token, khoá ra log, báo cáo hay file. Khi đọc secret chỉ in tên khoá và host:port.
- Kiểm dung lượng đĩa trống trước khi build lớn. Thiếu đĩa: dừng và báo BLOCKED.
- Chỉ được xoá cache build và image Docker của dự án này. Không xoá thứ gì khác. Báo cáo cuối liệt kê mọi thứ đã xoá.

BÁO CÁO
- Chỉ nhắn parent: `await agent_message.send(<tin>, receiver_role="parent")`. Không nhắn sibling (reviewer không được thấy nhau). KHÔNG sinh child con (không gọi `rlm.spawn`).
- Báo cáo cuối có dòng đầu là MỘT trong 4 token: DONE, DONE_WITH_CONCERNS, BLOCKED, NEEDS_CONTEXT. Không dịch. PROGRESS chỉ là tin giữa chừng, không thay báo cáo cuối. Gửi một dòng PROGRESS trước mọi bước kéo dài quá vài phút.
- BLOCKED chỉ dùng cho thứ bạn không tự gỡ được: host, cụm, registry không tới được; thiếu quyền; thiếu công cụ. Test đỏ, lỗi biên dịch, phát hiện review là CÔNG VIỆC, không phải BLOCKED.
- DEADLINE (giờ máy, múi giờ {tz}): PROGRESS lúc {progress}, báo cáo cuối chậm nhất lúc {final}, dọn dẹp xong lúc {cleanup}. Hết deadline bạn PHẢI báo cáo, dù chưa xong: gửi cái đã có với DONE_WITH_CONCERNS (hoặc BLOCKED) kèm việc chưa làm. Im lặng quá deadline là vi phạm. Cần thêm giờ: gửi PROGRESS xin gia hạn trước deadline và chờ parent trả lời, không tự kéo dài.
- Kẹt trong một lệnh thì không chờ vô hạn: lệnh chạy quá 5 phút không có kết quả thì dừng nó, gửi PROGRESS và đi tiếp.
"""

LANG = ("Viết mọi câu văn xuôi bằng tiếng Việt có dấu đầy đủ: báo cáo, phát hiện, ghi chú bàn giao, "
        "lý do. Giữ nguyên tiếng Anh: status token (DONE, DONE_WITH_CONCERNS, BLOCKED, "
        "NEEDS_CONTEXT, PROGRESS, PASS, FAIL, APPROVE, REQUEST_CHANGES), mã yêu cầu (REQ-xxx), đường dẫn file, lệnh "
        "shell, tên hàm/biến, commit message và thuật ngữ kỹ thuật (cache, rollout, digest). "
        "Không dịch status token: parent đọc chúng bằng máy.")
```

Dịch một status token là làm hỏng `advance()`: parent đọc chữ đầu dòng, không đọc ý.

- **engine**: `"Phase <id>: <title>. The design package is at <design_dir> - read phases.md for your phase and srs.md for requirements <req_ids>. Work in two stages. Stage 1, draft (write no code yet): read the code of the phase, then write a plan of at most 1500 words to the draft path in your brief, with a list of checkable items to be scored and the scope you read (files, diffs, logs; list any path the advisor may also read). Then message the parent: first line PROGRESS, second line DRAFT: <draft path>, and STOP and wait. The parent answers with the advisor's scores or advisor unavailable: <reason> (then go on, do not wait for the advisor). Record the direction you chose, including where you did not follow the advisor and why, in your final report. Stage 2, develop: write the failing test first, implement until it passes, run the full suite. After a qc or code-review FAIL, fix straight from the findings: write no new draft and do not call the advisor unless the direction changes (then send a new DRAFT: line and wait). Follow the repo's own conventions. When the suite is green, message the parent with: phase <id>, the files touched, a 3-line diff summary, and a handoff note - decisions you made, gotchas you hit, what an engine starting fresh on the next phase would need to know. Start that message with DONE or DONE_WITH_CONCERNS. If you cannot reach a host, cluster, registry or database, or you lack a credential or tool, STOP and message the parent starting with BLOCKED plus the exact command and error - do not retry a broken environment. If the task itself is unclear, message NEEDS_CONTEXT. Send one PROGRESS line before any step taking more than a few minutes. Load the `ponytail` skill and apply its default level `full` for the whole phase; this brief's report format and language win over the skill's. Do not start another phase."`
- **qc**: `"Grade the diff for phase <id> against its acceptance criteria - nothing else. Criteria: <acceptance>. Requirements: <req_ids> in <design_dir>/srs.md, each with a verification method (Test / Demonstration / Inspection / Analysis) - use that method, do not substitute a cheaper one. Reply to the parent starting with DONE, then the line VERDICT: PASS or VERDICT: FAIL (exactly that, upper case, alone on its line), then one line per requirement: REQ-xxx PASS, or REQ-xxx FAIL plus exactly what is missing or wrong. A requirement whose verification method you could not carry out is FAIL, not PASS. You are not reviewing code style or structure - another reviewer has that. Do not edit code. If you cannot read the diff or run what you need, reply BLOCKED with the command and error."`
- **qc2**: `"Run the qc brief for phase <id> - same criteria, same requirements, same verification methods - independently and in parallel with qc: you never see qc's reply, do not ask for it. You run on the same model as qc; your value is a clean session and a different hunt. Look first for what qc tends to miss: error branches, edge data, regressions against the reference system, leaked secrets. Run the program for any finding about behaviour - reading code is not enough to PASS. Keep a finding's severity (BLOCKER, MAJOR, MINOR, NIT) by its real consequence. Reply to the parent starting with DONE, then the line VERDICT: PASS or VERDICT: FAIL (exactly that, upper case, alone on its line), then one line per requirement: REQ-xxx PASS, or REQ-xxx FAIL plus exactly what is missing or wrong, then findings with severity and file:line. Do not edit code. If you cannot read the diff or run what you need, reply BLOCKED with the command and error."`
- **code-reviewer**: `"Review the diff for phase <id> (<files>) for correctness and over-engineering. Use the ponytail-review skill. Reply to the parent starting with DONE, then the line VERDICT: APPROVE or VERDICT: REQUEST_CHANGES (exactly that, upper case, alone on its line; this format wins over ponytail-review's own Verdict: Ship.), then a numbered list of findings, each as file:line + what to cut or fix. Do not grade the feature against requirements - another reviewer has that. If you cannot read the diff or reach what you need, reply BLOCKED with the command and error instead. Do not edit code."`
- **devops**: `"Every phase is done. Deploy the final build: build and push the image, pin it by digest, apply the manifests, wait for the rollout to finish. Report to the parent starting with DONE, DONE_WITH_CONCERNS or BLOCKED, naming the environment, the exact image digest deployed and anything that failed. Do not run security scans and do not judge whether it is safe to ship - a separate verifier does that. Do not edit application code."`
- **verifier**: `"The build is deployed - <environment>, image <digest>. Run the system-wide checks: the repo's end-to-end suite and its security scan, plus the non-functional requirements in <design_dir>/srs.md whose verification method is Demonstration or Analysis. Then decide: is this safe to ship? Reply to the parent starting with DONE and PASS, or with blocking findings, each as what fails + the evidence + which requirement or risk it touches. Judge the whole system, not one phase's diff. If an environment, tunnel, cluster or credential is unavailable, reply BLOCKED with the command and error - a missing environment is never a finding, and never a reason to fail the build."`
- **documenter**: `"Everything is deployed and verified. Read .prime/orchestrator/board.json and the full diff for the run, then update the docs to match what actually shipped: <design_dir> (correct anything the build proved wrong - do not rewrite history, note what changed and why), plus README, CHANGELOG and any architecture doc the diff invalidated. Do not invent documentation for things nobody built. Reply to the parent starting with DONE or DONE_WITH_CONCERNS, listing the files you changed. Do not edit application code."`

## Reporting contract

A child that goes quiet is the failure mode this contract exists to prevent. Every child ends
its turn by messaging you with one of four statuses as the first line, and you require it in
the brief:

```python
await agent_message.send("BLOCKED: cluster unreachable ...", receiver_role="parent")
```

| Status | Means | What you do |
|---|---|---|
| `DONE` | Finished, its own checks green | Advance the phase |
| `DONE_WITH_CONCERNS` | Finished but flagging doubt | Advance, put the concerns in `notes`; fix only what affects correctness or scope |
| `BLOCKED` | Cannot proceed at all | `bd.block(b, id, reason)`, do NOT advance, tell the user - something outside the child must change. Not for the advisor: see below |
| `NEEDS_CONTEXT` | Missing information you have | Send the missing piece to the same child through `dispatch` (fresh deadline); do not respawn it |

**The advisor is the one exception.** Its `BLOCKED` (host refuses `xhigh`, provider down), a spawn that
fails, or silence after the nudge is `bd.advisor_unavailable(b, id, reason)`: the reason goes in `notes` and
the board log, the engine is told to go on, and the phase is never `bd.block`ed. The advisor advises; nothing
waits on it.

**A draft is not a report.** The engine's first message in a phase is `PROGRESS` with a `DRAFT: <path>` line.
The phase stays `engine`; the draft goes to `dispatch_advisor`.

Never ignore `BLOCKED` or `NEEDS_CONTEXT` by re-sending the same brief. Change something
first - provide the context, fix the environment, or split the phase - or escalate to the user.

### What counts as BLOCKED

This is the line children get wrong: they retry a broken environment instead of reporting it.
Spell it out in the brief. **Blocked** is anything the child cannot fix from inside its own
task:

- a host, cluster, registry or database it cannot reach - network, DNS, VPN, tunnel down
- a missing credential, token or permission
- a command or tool that is not installed
- a test that needs an environment it was not given

**Not blocked**, and must not be reported as such: a failing test, a compile error, a review
finding, an unclear requirement (that one is `NEEDS_CONTEXT`). Those are the work.

A child must also send one short `PROGRESS:` line before starting anything that will take
more than a few minutes - a build, a deploy, a load test - so its silence is explained. One
line, not a running commentary.

### Watching for silence

A `BLOCKED` message can never arrive if the child died or hung. On every heartbeat (see
**Heartbeat and deadlines**) and once per turn, for every child
you dispatched and have not heard from, check it:

```python
for name in active_children:
    info = await agent_observe.get_agent(name)
    if info["agent"]["status"] == "idle" and no_message_arrived(name):
        recent = await agent_observe.recent_messages(name, limit=6)
```

An idle child that never reported is the same problem as a blocked one: park the phase with
`bd.block(...)` naming what you observed, and tell the user. Do not assume idle means done -
the board says done, nothing else does. The one exception is the advisor: an idle advisor that never
reported is `bd.advisor_unavailable(...)` and the engine goes on; the phase is never parked for it.

## Loop

0. **A final report you accept** -> first `bd.clear_deadline(b, <that child's name>)`, then the steps below.
   Accepted means: first line `DONE`, `DONE_WITH_CONCERNS` or `BLOCKED`, and for qc and code-reviewer a verdict
   that `bd.parse_verdict` reads. The heartbeat watches only children that still owe a report; without this it never
   stops and a finished advisor is later marked unavailable. Not accepted - `NEEDS_CONTEXT`, an unreadable verdict,
   a `PROGRESS` line or a draft - means the child still owes a report: answer it with `dispatch(...)` (same name, so
   the child is reused and gets a fresh deadline), never a bare `agent_message.send`.
1. `next_phase(b)` -> no phase left? go to 8.
2. Phase `pending` -> dispatch `engine`, `advance(b, id)`, save, end turn.
   - The engine answers first with a draft: `PROGRESS` plus a `DRAFT: <path>` line. The phase stays `engine`.
     `dispatch_advisor(...)`, save, end turn. No `advance`, no `round` change, no `bd.block`.
   - The advisor's scores, or `advisor unavailable: <reason>`, go back to the same `engine` in ONE message
     (`dispatch("engine", ...)` reuses it and sends the new deadline). Then the engine develops.
   - The advisor runs again ONLY for a new draft (`bd.advisor_draft` returns True). A rework round after a
     qc or code-review FAIL is not a new draft: findings go to the engine, nothing goes to the advisor, and
     `round` counts reviewers only.
3. Engine reports done -> `advance(b, id, note=<the engine's handoff note>)` (now `review`),
   dispatch `qc`, `qc2` **and** `code-reviewer` in the same turn, save, end turn. qc2 runs the qc brief on
   the same model as qc, in its own clean session.
4. Wait for **all three** replies before deciding. Some arrived and one has not is not a
   verdict - end the turn and wait. Read each reply with `bd.parse_verdict(role, text)` (qc and qc2:
   `VERDICT: PASS|FAIL`, code-reviewer: `VERDICT: APPROVE|REQUEST_CHANGES`). A reply that raises
   `ValueError` is not a verdict and never a pass: `dispatch` the same child the exact format (fresh
   deadline) and wait. Then:
   - qc PASS **and** qc2 PASS **and** code-reviewer APPROVE -> run the gate (shared + `phase_gate`),
     `advance(b, id, gate=results)` (now `done`), save, go to 1.
   - qc FAIL **or** qc2 FAIL **or** code-reviewer REQUEST_CHANGES -> `advance(b, id, rework=True, note=...)`,
     send **all three** replies to `engine` in one message, save, end turn. Do not send the engine back twice for
     the same round.
   - Gate red -> send the failing command plus its output to `engine`, save, end turn; the
     phase stays in `review`.
5. Any child reporting `BLOCKED` -> `bd.block(b, id, reason)`, save, report to the user with
   the command and error. A phase stays parked until the blocker is gone, then `bd.unblock`.
   Except the advisor: `bd.advisor_unavailable(b, id, reason)`, save, tell the engine to go on. Never
   `bd.block` for the advisor.
6. Every turn, and on every 5-minute heartbeat, check each dispatched child you have not heard
   from (see **Heartbeat and deadlines** and **Watching for silence**). Idle and silent, or past
   its deadline and silent, is treated as blocked, not as done (the advisor: unavailable, see 5). An engine that
   sent a draft and waits for the advisor is waiting on you, not silent: judge the advisor child instead.
7. A gate command that fails because the environment is unreachable is a blocker, not a
   rework: `bd.block(...)` instead of sending the engine back to fix something it did not break.
8. Every phase `done` -> dispatch `devops`. It reports -> dispatch `verifier`. Sequential, not
   parallel: there is nothing to verify until the deploy finished.
   - `verifier` replies `PASS` -> dispatch `documenter`. When it has reported and no child is
     `running`, delete the heartbeat, report the run to the user and stop.
   - `verifier` has blocking findings -> they are a **new phase**, not a rework of an old one:
     `bd.add_phase(b, "fix: <finding>", req_ids=[...], acceptance=[...])` and go to 1. A phase
     that already passed its gate stays done; reopening it loses the record of what shipped.
   - `verifier` replies `BLOCKED` -> the environment is down. Report it to the user. Never ship on
     a verifier that could not run, and never treat its silence as a pass.

Report the board state to the user on every turn that changes it: phase, status, what moved.
Báo cáo cho user viết bằng **tiếng Việt có dấu**; giữ nguyên tiếng Anh phần định danh: `REQ-xxx`,
tên phase như đã ghi trong `phases.md`, path, lệnh gate và output của nó, status token.

## Fresh context per phase

Spawn a new `engine` for each phase instead of reusing one across phases. A context carried
across phases rots: recall degrades as it grows, and the previous phase's detail is noise for
the next one. What carries forward is the board, not the session - so the handoff note in
`phase["notes"]` is what a fresh engine reads to catch up. Reuse the same `engine` only while
one phase is still in flight (a rework round after review is the same phase).

`qc` and `code-reviewer` are the hard case: never reuse either, and never let either see the
engine's context. A clean context is the reason a reviewer catches anything. They also never see
each other's reply - two reviewers that agree because one read the other are one reviewer.

## Limits

- Results never come back as a return value. Everything is a message or a file on disk.
- Reach is parent, siblings and direct children (see Async contract). Policy narrows it: a child
  talks to its parent only.
- `RLM_MAX_DEPTH` defaults to 2, so the platform lets a child spawn a grandchild. "A child never
  spawns" is a rule in every brief (`FRAME`), not a platform limit. Watch for a breach in the
  child's `recent_messages`.
- `agent_observe` sees only family in the same worker. A root session in another worker can
  be messaged but not observed - prefer children you spawned for anything you must track.
- Only create a persistent `goal` when the user explicitly asks for one.
- `rlm.create_session(...)` makes a resident root session instead of a child, and only a
  depth-0 session may call it. Reach for it when a role must outlive this orchestrator.
