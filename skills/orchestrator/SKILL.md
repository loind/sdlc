---
name: orchestrator
description: Execute a design package across agent sessions - engine builds each phase, qc and code-reviewer grade it in parallel, a real gate command closes it, then devops deploys, verifier runs system-wide e2e and security, and documenter updates the docs - all recorded on a persistent task board. Requires a design package from the thinker skill; it does not design the work itself. Use when the user asks to execute or orchestrate a plan across agents, run a build/review/gate loop per phase, coordinate subagents, or check the status of dispatched work.
---

# Orchestrator

You **execute a design package**. You do not design the work: the `thinker` skill wrote
`docs/design/<slug>/` - PRD, SRS with a requirement table, C4 views, and `phases.md` holding
the phase split, the requirement ids per phase, the acceptance criteria and the gate commands.
Your job is to run it, gate it on real commands, and record every transition on the board.

You do not write product code yourself.

Per phase: `engine -> (qc || code-reviewer) -> gate -> done`. After the last phase:
`devops -> verifier -> documenter`. The next phase starts from the board, not from memory.

| Role | Owns | Runs | Ends its turn by |
|---|---|---|---|
| `engine` | One phase: plan, failing test first, implement, run the suite | Per phase | Message to parent: phase id + diff summary + handoff note |
| `qc` | Grades the diff against that phase's **acceptance criteria**, one verdict per requirement | Per phase, parallel with code-reviewer | `PASS` or per-REQ fail with what is missing |
| `code-reviewer` | Correctness + over-engineering review of the diff, via `ponytail-review` | Per phase, parallel with qc | `PASS` or a numbered finding list |
| `devops` | Deploy and infrastructure: image, manifest, rollout. No security judgement | Once, after the last phase | Message to parent with what was deployed and where |
| `verifier` | System-wide e2e + the whole security picture on the deployed build; decides ship / no-ship | Once, after devops | `PASS` or blocking findings |
| `documenter` | Updates `docs/design/<slug>/` and the repo docs to match what actually shipped | Once, last | Message to parent with the files it changed |

`qc` and `code-reviewer` are separate sessions from `engine` and from each other: an agent
reviewing its own diff is not a review, and one session asked for two different judgements gives
you the easier one twice.

`devops` deploys, `verifier` judges. Never let one session do both - the session that deployed
has a reason to call the deploy fine.

## Start: read the design package

**No `phases.md` on disk means you stop.** Look for `docs/design/*/phases.md`; if the user named a
directory, use that one. Nothing there - tell the user to run `/thinker` first and end your turn.
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

## Board

`scripts/board.py` owns the board at `.prime/orchestrator/board.json`. You are its only
writer. Load it in the kernel once, then reuse the module:

```python
import sys, pathlib
sys.path.insert(0, str(pathlib.Path("~/.agents/skills/orchestrator/scripts").expanduser()))
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

## Gate

A phase reaches `done` only when a real command says so. `advance(..., gate=...)` refuses
the transition without passing results, so a reviewer replying `PASS` cannot close a phase
on its own. Detect the repo's own commands once at init and store them on the board:

```python
b["gate"] = ["pytest -q", "ruff check ."]   # read from pyproject / package.json / Makefile
```

Run them yourself after **both** reviewers pass, shared gate first then the phase's own
`phase_gate`, and advance with the combined results:

```python
results = []
for cmd in b["gate"] + phase.get("phase_gate", []):
    r = await bash(cmd)
    results.append({"cmd": cmd, "exit": r.exit_code, "ok": r.exit_code == 0})
    if r.exit_code != 0:
        break   # fail fast: never spend a long stage on a build that already failed
bd.advance(b, phase_id, gate=results)   # raises unless every command that ran passed
```

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

Resolve selectors at runtime - never hardcode a model id. Store the choice on the board so
every respawn of a role uses the same model:

```python
# find_models tra ve moi ban khop va thu tu KHONG phai moi-nhat-truoc: "sonnet" cho ra
# claude-sonnet-4-5, 4-5-20250929, 4-6, 5 - lay [0] la lay 4.5. Loc theo id chinh xac.
# Model theo vai (người dùng chốt 29/09/2026): engine = deepseek-v4-flash (provider deepseek),
# documenter (viết/cập nhật tài liệu, rà câu chữ) = gemini-3.8-flash (google-vertex), còn lại Sonnet 5.5.
WANT = {"engine": ("deepseek", "deepseek-v4-flash"),
        "documenter": ("gemini-3.8", "gemini-3.8-flash"),
        "*": ("sonnet", "claude-sonnet-5-5")}
async def pick(role):
    q, mid = WANT.get(role, WANT["*"])
    sel = next((m.selector for m in await rlm.find_models(q) if m.id == mid), None)
    assert sel, f"khong thay {mid}"
    return sel
b["models"] = {r: await pick(r) for r in
               ("engine", "qc", "code-reviewer", "devops", "verifier", "documenter")}
```

Never index into `find_models` by position, and never hardcode the selector string either -
pin the model **id** you want and let `find_models` resolve its provider prefix. A wrong
index fails silently: the child runs an older model and nothing in the board says so.

Children run the per-role model on the board (engine DeepSeek, documenter Gemini, the rest Sonnet). You keep the session's own model - the strong one - because the
decisions live here: reading two reviewers' findings against each other, deciding rework vs
done, deciding what a verifier finding becomes. A child works one scoped task with a clean context, which is where a fast model holds
up. Leave the board's `models` per-role so one role can be raised later without touching
this skill. Pass it on spawn:

```python
await rlm(brief, name=role, model=b["models"][role], thinking="high")
```

`model` takes an exact `provider/model` selector, `thinking` defaults to the parent level and
an invalid level for that model fails the spawn. Omit both to inherit the parent's.

## Resolve or spawn

The child's *name* decides what gets reused, so the naming rule carries the context policy:

```python
def child_name(role, phase):
    if role in ("devops", "verifier", "documenter"):
        return role                                        # one session each, once at the end
    if role in ("qc", "code-reviewer"):
        return f"{role}-p{phase['id']}-r{phase['round']}"   # fresh name every round: never reused
    return f"engine-p{phase['id']}"                        # reused across rework rounds, new per phase
```

Then resolve-or-spawn is a plain lookup - a name that exists is reused, a name that does not
is spawned:

```python
async def dispatch(role, phase, brief, board):
    name = child_name(role, phase)
    children = await rlm.list_subagents()
    if any(c.session_name == name for c in children):
        await agent_message.send(brief, receiver_role="child", receiver_name=name)
        return name
    await rlm(
        f"{ROLE_PROMPT[role]}\n\n{brief}\n\n{LANG}",   # LANG: xem Role briefs
        name=name,
        model=board.get("models", {}).get(role),
    )
    board.setdefault("agents", {})[role] = name
    return name
```

Once a phase is `done`, delete the children that served it so they stop accumulating - but
only after `agent_observe.get_agent(name)` shows the child idle, because a delivered message
may still be running:

```python
await rlm.delete_subagent(child)
```

`rlm(...)` returns as soon as the child is admitted - it never returns the child's answer.
Dispatch, write the board, end your turn. The child's reply arrives as a message later.

## Role briefs

Give each child only what its task needs, plus the reply contract. Every brief names
`<design_dir>` so the child reads requirements from the package instead of from your paraphrase.

Append this line to **every** brief - one place, so no role can be forgotten:

```python
LANG = ("Viet moi cau van xuoi bang tieng Viet co dau day du - bao cao, finding, handoff note, "
        "ly do. Giu nguyen tieng Anh: status token (DONE, DONE_WITH_CONCERNS, BLOCKED, "
        "NEEDS_CONTEXT, PROGRESS, PASS, FAIL), requirement id (REQ-xxx), duong dan file, lenh "
        "shell, ten ham/bien, commit message, va thuat ngu ky thuat (cache, rollout, digest). "
        "Khong dich status token - parent doc chung bang may.")

await rlm(f"{ROLE_PROMPT[role]}\n\n{brief}\n\n{LANG}", name=name, model=...)
```

Dịch một status token là làm hỏng `advance()`: parent đọc chữ đầu dòng, không đọc ý.

- **engine**: `"Phase <id>: <title>. The design package is at <design_dir> - read phases.md for your phase and srs.md for requirements <req_ids>. Work the loop in order: plan the change, write the failing test first, implement until it passes, run the full suite. Follow the repo's own conventions. When the suite is green, message the parent with: phase <id>, the files touched, a 3-line diff summary, and a handoff note - decisions you made, gotchas you hit, what an engine starting fresh on the next phase would need to know. Start that message with DONE or DONE_WITH_CONCERNS. If you cannot reach a host, cluster, registry or database, or you lack a credential or tool, STOP and message the parent starting with BLOCKED plus the exact command and error - do not retry a broken environment. If the task itself is unclear, message NEEDS_CONTEXT. Send one PROGRESS line before any step taking more than a few minutes. Do not start another phase."`
- **qc**: `"Grade the diff for phase <id> against its acceptance criteria - nothing else. Criteria: <acceptance>. Requirements: <req_ids> in <design_dir>/srs.md, each with a verification method (Test / Demonstration / Inspection / Analysis) - use that method, do not substitute a cheaper one. Reply to the parent starting with DONE, then one line per requirement: REQ-xxx PASS, or REQ-xxx FAIL plus exactly what is missing or wrong. A requirement whose verification method you could not carry out is FAIL, not PASS. You are not reviewing code style or structure - another reviewer has that. Do not edit code. If you cannot read the diff or run what you need, reply BLOCKED with the command and error."`
- **code-reviewer**: `"Review the diff for phase <id> (<files>) for correctness and over-engineering. Use the ponytail-review skill. Reply to the parent starting with DONE and then either PASS or a numbered list of findings, each as file:line + what to cut or fix. Do not grade the feature against requirements - another reviewer has that. If you cannot read the diff or reach what you need, reply BLOCKED with the command and error instead. Do not edit code."`
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
| `BLOCKED` | Cannot proceed at all | `bd.block(b, id, reason)`, do NOT advance, tell the user - something outside the child must change |
| `NEEDS_CONTEXT` | Missing information you have | Send the missing piece to the same child; do not respawn it |

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

A `BLOCKED` message can never arrive if the child died or hung. Once per turn, for every child
you dispatched and have not heard from, check it:

```python
for name in active_children:
    info = await agent_observe.get_agent(name)
    if info["agent"]["status"] == "idle" and no_message_arrived(name):
        recent = await agent_observe.recent_messages(name, limit=6)
```

An idle child that never reported is the same problem as a blocked one: park the phase with
`bd.block(...)` naming what you observed, and tell the user. Do not assume idle means done -
the board says done, nothing else does.

## Loop

1. `next_phase(b)` -> no phase left? go to 8.
2. Phase `pending` -> dispatch `engine`, `advance(b, id)`, save, end turn.
3. Engine reports done -> `advance(b, id, note=<the engine's handoff note>)` (now `review`),
   dispatch `qc` **and** `code-reviewer` in the same turn, save, end turn.
4. Wait for **both** replies before deciding. One arrived and the other has not is not a
   verdict - end the turn and wait. Then:
   - Both `PASS` -> run the gate (shared + `phase_gate`), `advance(b, id, gate=results)`
     (now `done`), save, go to 1.
   - Either one has findings -> `advance(b, id, rework=True, note=...)`, send **both** replies
     to `engine` in one message, save, end turn. Do not send the engine back twice for the
     same round.
   - Gate red -> send the failing command plus its output to `engine`, save, end turn; the
     phase stays in `review`.
5. Any child reporting `BLOCKED` -> `bd.block(b, id, reason)`, save, report to the user with
   the command and error. A phase stays parked until the blocker is gone, then `bd.unblock`.
6. Every turn, check each dispatched child you have not heard from (see **Watching for
   silence**). Idle and silent is treated as blocked, not as done.
7. A gate command that fails because the environment is unreachable is a blocker, not a
   rework: `bd.block(...)` instead of sending the engine back to fix something it did not break.
8. Every phase `done` -> dispatch `devops`. It reports -> dispatch `verifier`. Sequential, not
   parallel: there is nothing to verify until the deploy finished.
   - `verifier` replies `PASS` -> dispatch `documenter`, then report the run to the user and stop.
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
- Reach is parent, siblings, and direct children only. Grandchildren relay through their parent.
- Default recursion depth lets you create children; your children cannot create their own.
- `agent_observe` sees only family in the same worker. A root session in another worker can
  be messaged but not observed - prefer children you spawned for anything you must track.
- Only create a persistent `goal` when the user explicitly asks for one.
- `rlm.create_session(...)` makes a resident root session instead of a child, and only a
  depth-0 session may call it. Reach for it when a role must outlive this orchestrator.
