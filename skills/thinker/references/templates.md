# Design package templates

Four files in `docs/design/<slug>/`. Each fact lives in exactly one of them; the others link to it.
Write only sections you can fill. A heading with nothing under it is worse than a missing heading.

**Language:** content is written in Vietnamese with full diacritics. Every heading and key below
stays in English exactly as written - in `phases.md` the orchestrator reads by those exact words.
Keep `REQ-xxx`, `FR`/`NFR`, `must`/`should`/`could`, `Test`/`Demonstration`/`Inspection`/`Analysis`,
paths, commands and function names as they are.

---

## `prd.md` - why, for whom

Only what the user can tell you. If the repo already has a PRD, read that one and skip this file;
note the path in `design.md` instead.

```markdown
# <Feature> - PRD

## Problem
What is broken today, for whom, and what it costs. Specific, never generic.

## Users & stakeholders
Who uses it, who operates it, and who is affected downstream without having asked for this.

## Success criteria
How we know it is done. A number, a log line, an alert that stops firing.

## Out of scope
What this does NOT do. The most valuable section here - it is what stops scope creep in phase three.

## Anti-goals
What would make this a failure even if it works correctly. E.g. "the consumer gets slower than
today", "merchants have to reconfigure".

## Open questions
What is parked without an answer, and who can answer it.
```

---

## `srs.md` - what, and how each part is proven

C4 Level 1 plus the requirement table. Two things, one file, because the context diagram *is* the
SRS product perspective - splitting them means writing the same truth twice.

Requirement attributes follow ISO/IEC/IEEE 29148:2018, trimmed to what the pipeline consumes.
`Verify` is the one that matters most: it is where every acceptance criterion downstream comes from.

```markdown
# <Feature> - SRS

## System context (C4 L1)

\`\`\`mermaid
C4Context
  Person(user, "Merchant admin", "…")
  System(sys, "<this system>", "…")
  System_Ext(ext, "<external>", "…")
  Rel(user, sys, "…")
  Rel(sys, ext, "…", "HTTPS")
\`\`\`

One paragraph: what is inside the boundary, what is outside, and what crosses it.

## Requirements

| Id | Type | Pri | Requirement | Rationale | Verify |
|---|---|---|---|---|---|
| REQ-001 | FR | must | The system shall … | Why it is needed | Test |
| REQ-002 | NFR | should | p95 latency shall be under … | … | Analysis |

- **Type**: `FR` functional, `NFR` non-functional.
- **Pri**: `must` / `should` / `could`. Nothing is `must` by default.
- **Requirement**: one sentence, one verifiable idea. Two ideas are two rows.
- **Verify**: `Test` (automated, a command), `Demonstration` (observe running system),
  `Inspection` (read code, config or output), `Analysis` (measure, compute, compare).
  Cannot pick one? It is not a requirement yet - go back and ask.

## Constraints & assumptions
Everything the design has to live with, and each assumption with the name of who confirmed it.
An assumption with no owner is a risk - say so.
```

---

## `design.md` - how, and what we chose not to do

```markdown
# <Feature> - Design

## Containers (C4 L2)

\`\`\`mermaid
C4Container
  Container(api, "API", "Python/FastAPI", "…")
  ContainerDb(db, "MongoDB", "…", "…")
  Rel(api, db, "reads/writes")
\`\`\`

For each container: what it does, who it talks to, what changes in it this time.

## Decisions

### D1 - <decision>
**Chosen:** … **Because:** …
**Rejected:** <option B> - <why it loses>. <option C> - <why>.
**Trade-off:** what choosing this makes hard later.

## Agent's calls
Every default the user never heard or never explicitly confirmed, and every "minor" builder-check
question the agent settled. One line each: decision - reason. The user reads this section first
when approving. Never holds a hard-gate decision (API contract, schema, auth, tenant isolation,
external side effect) - those need the user's confirmation and live under `## Decisions`.

## Design problems
What will sink this if nobody names it. One line each, most dangerous first: ambiguous
requirements, a shared resource two phases both need, an assumption nobody owns, something the
phase split cannot express.

## Level 3
Only when a phase touches three or more modules. Otherwise drop it - an L3 diagram is stale after
the first refactor and nobody updates it.
```

---

## `phases.md` - the contract

The orchestrator reads this file and copies it onto the board. **Keep the English headings and keys
below exactly** - `Goal`, `Gate`, `Phase N`, `Requirements`, `Acceptance`, `Depends on`, `Notes`.
This is a contract, not prose; translating them makes the orchestrator misread it. The content is
written in Vietnamese.

```markdown
# <Feature> - Phases

**Goal:** one sentence. This becomes `board["goal"]`.

**Gate (every phase):** commands run for every phase, cheapest first.
\`\`\`
ruff check .
pytest -q
\`\`\`

## Phase 1 - <one change that can be proven on its own>
- **Requirements:** REQ-001, REQ-002
- **Acceptance:**
  - REQ-001: <what a QC reviewer checks to call it satisfied, from the Verify method>
  - REQ-002: <…>
- **Gate:** `pytest tests/test_x.py -q`  ← extra command for this phase, on top of the shared gate
- **Depends on:** none
- **Notes:** shared resources, environment needed, anything that forces this phase to run alone

## Phase 2 - …
```

Rules the orchestrator relies on:

- Phases ordered by dependency, not by size. A phase that unblocks two others goes first.
- 3 to 7 phases.
- Every `REQ-` id appears in exactly one phase. Every requirement in `srs.md` appears somewhere.
- Every acceptance line is checkable by reading the diff or running something - never "works correctly".
- A phase needing a deployed environment says so in **Notes**; its gate deploys before it tests,
  and it never runs in parallel with another phase touching the same environment.
