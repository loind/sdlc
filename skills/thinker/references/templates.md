# Design package templates

Four files in `docs/design/<slug>/`. Each fact lives in exactly one of them; the others link to it.
Write only sections you can fill. A heading with nothing under it is worse than a missing heading.

**Ngôn ngữ:** nội dung viết bằng tiếng Việt có dấu. Heading và key trong `phases.md` giữ nguyên
tiếng Anh - orchestrator dựa vào đúng chữ đó để đọc file. Giữ nguyên `REQ-xxx`, `FR`/`NFR`,
`must`/`should`/`could`, `Test`/`Demonstration`/`Inspection`/`Analysis`, path, lệnh, tên hàm.

---

## `prd.md` - why, for whom

Only what the user can tell you. If the repo already has a PRD, read that one and skip this file;
note the path in `design.md` instead.

```markdown
# <Feature> - PRD

## Vấn đề
Hôm nay cái gì đang hỏng, hỏng với ai, và nó tốn gì. Cụ thể, không nói chung chung.

## Người dùng & bên liên quan
Ai dùng, ai vận hành, ai chịu ảnh hưởng ở phía sau mà không hề yêu cầu chuyện này.

## Tiêu chí thành công
Làm sao biết là xong. Một con số, một dòng log, một alert thôi kêu.

## Ngoài phạm vi
Cái này KHÔNG làm gì. Section đáng giá nhất ở đây - nó là thứ chặn scope creep ở phase thứ ba.

## Câu hỏi còn treo
Cái gì đang park chưa có câu trả lời, và ai là người trả lời được.
```

---

## `srs.md` - what, and how each part is proven

C4 Level 1 plus the requirement table. Two things, one file, because the context diagram *is* the
SRS product perspective - splitting them means writing the same truth twice.

Requirement attributes follow ISO/IEC/IEEE 29148:2018, trimmed to what the pipeline consumes.
`Verify` is the one that matters most: it is where every acceptance criterion downstream comes from.

```markdown
# <Feature> - SRS

## Bối cảnh hệ thống (C4 L1)

\`\`\`mermaid
C4Context
  Person(user, "Merchant admin", "…")
  System(sys, "<this system>", "…")
  System_Ext(ext, "<external>", "…")
  Rel(user, sys, "…")
  Rel(sys, ext, "…", "HTTPS")
\`\`\`

Một đoạn: cái gì nằm trong biên, cái gì ngoài biên, và cái gì đi xuyên qua biên.

## Yêu cầu

| Id | Type | Pri | Yêu cầu | Lý do | Verify |
|---|---|---|---|---|---|
| REQ-001 | FR | must | Hệ thống phải … | Vì sao cần | Test |
| REQ-002 | NFR | should | p95 latency phải dưới … | … | Analysis |

- **Type**: `FR` functional, `NFR` non-functional.
- **Pri**: `must` / `should` / `could`. Nothing is `must` by default.
- **Yêu cầu**: một câu, một ý kiểm chứng được. Hai ý là hai dòng.
- **Verify**: `Test` (automated, a command), `Demonstration` (observe running system),
  `Inspection` (read code, config or output), `Analysis` (measure, compute, compare).
  Cannot pick one? It is not a requirement yet - go back and ask.

## Ràng buộc & giả định
Mọi thứ thiết kế buộc phải sống chung, và mỗi giả định kèm tên người đã xác nhận nó.
Giả định không có chủ là risk - ghi rõ như vậy.
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

Mỗi container: nó làm gì, nó nói chuyện với ai, lần này nó đổi cái gì.

## Quyết định

### D1 - <quyết định>
**Chọn:** … **Vì:** …
**Loại:** <phương án B> - <lý do nó thua>. <phương án C> - <lý do>.
**Đánh đổi:** chọn thế này thì sau khó ở chỗ nào.

## Vấn đề thiết kế
Những thứ sẽ đánh chìm việc này nếu không ai gọi tên. Mỗi cái một dòng, nguy hiểm nhất lên trước:
requirement mơ hồ, tài nguyên dùng chung mà hai phase cùng cần, giả định không ai đứng tên,
thứ mà cách chia phase không diễn đạt nổi.

## Level 3
Chỉ khi một phase đụng từ ba module trở lên. Không thì bỏ - diagram L3 lỗi thời ngay sau
refactor đầu tiên và không ai cập nhật.
```

---

## `phases.md` - the contract

Orchestrator đọc file này rồi copy lên board. **Giữ nguyên các heading và key tiếng Anh bên dưới** -
`Goal`, `Gate`, `Phase N`, `Requirements`, `Acceptance`, `Depends on`, `Notes`. Đó là contract, không
phải văn xuôi; dịch chúng là làm orchestrator đọc trượt. Phần nội dung viết tiếng Việt.

```markdown
# <Feature> - Phases

**Goal:** một câu tiếng Việt. Câu này thành `board["goal"]`.

**Gate (every phase):** lệnh chạy cho mọi phase, rẻ nhất trước.
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
