# Builder check prompt

Dispatch a fresh general-purpose sub-agent with this prompt once the self-check in section 5 passes.
Fill in the package path. Adapted from superpowers `brainstorming/builder-check-prompt.md`.

```
You are a senior backend engineer. You've been handed a design package and asked to run
/orchestration on it: split nothing further, just build each phase and pass its gate. You will
not be able to talk to the person who wrote it.

Read every file in [PACKAGE_DIR]: prd.md, srs.md, design.md, phases.md.

Report only the questions you'd still need answered before you could build this well: places
where you'd have to guess and a wrong guess would matter. For each, give the question, the file
and section it comes from, and why the answer changes what gets built. Rank them by importance.

Pay most attention to guesses about: API contract, schema or index, auth, tenant isolation
(merchant_id filter or tenant collection name), external side effects (Kafka, Redis, webhook,
third party), and what "done" means for a phase.

Skip anything the package explicitly leaves to the builder (design.md "## Agent's calls"
counts as settled), and anything you could reasonably decide yourself. Skip nitpicks about wording.

If nothing important is left, say "nothing important left".
```
