# Task File Format

An optional output format for one task whose research is already done. It turns existing findings into a checklist that an implementer can start without more research. Use the full plan format instead when research is still open, the work spans several concerns, or it needs parallel waves.

The planning boundary, approval gate, and final plan requirements in `SKILL.md` still apply. The task file replaces only the output layout.

## Inputs

1. Existing findings: `docs/issues/{id}/{id}.md` or another research note when present, otherwise the user's request text.
2. Policy or scope limits from the request, such as "tasks 1 and 2 only" or "use a Redis cache with a 5 minute TTL".
3. Test, lint, and build commands from project rules. When the rules do not name them, find them in the repository and write them into the file.

## Path

- `docs/issues/{id}/task.md` when the repository already has `docs/issues/`. `{id}` is the issue number or the existing directory name.
- Otherwise `.claude/omo/plans/<task-slug>-task.md`.

Write the file only after approval. Create the directory when missing and state the path.

## Required Sections

```markdown
# Task: {title}

## Issue
- Issue: #{id} (omit when none)
- Findings: {path to the research note, or "request text only"}

## Overview
{What to implement, 1 to 3 lines}

## Policy
{Chosen approach. When options existed, which one was picked and why}

## Related Files
- `path/to/file` : {role}

## Tasks

### 1. {Concern, e.g. "SQL query fix"}
- [ ] 1-1. {exact action} (`path`, symbol or line)
- [ ] 1-2. Test: {behavior asserted} (`test path`)
- [ ] 1-3. Run `{test command}` and confirm it passes

### N. Final Verification
- [ ] N-1. Run the full test suite: `{command}`
- [ ] N-2. Run lint and format checks: `{command}`

## Acceptance Criteria
- {measurable condition}

## Notes
- {pitfalls, out-of-scope items, owner decisions already made}
```

## Checklist Rules

- One item is one action whose completion can be judged on its own.
- Each item names the target path and, where useful, the symbol or line.
- Pair every change item with its test item under the same concern, then a run item.
- Order items top to bottom by dependency so they run sequentially.
- Reject vague items such as `Fix the SQL` or `Write tests`. Good: `Change master_products.packing_unit_unit to master_drugs.unit_after_conversion at line 37 of master_codes.sql`.

## Handoff

Name the file path and the options the user may start. Approval of the task file does not start any of them.

- `omo-orchestrator:omo-implementer` via `Agent(subagent_type="omo-orchestrator:omo-implementer", prompt="Implement per <path>")`.
- `omo-review-loop <path>` for implementation with a review-fix loop. With the `docs` layout it finds `task.md` in the issue directory.
- `omo-ulw-execute <path>` to run it with an evidence ledger.
