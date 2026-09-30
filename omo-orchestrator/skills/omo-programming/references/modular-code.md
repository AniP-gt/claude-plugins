# Modular Code Defaults

Defaults for file and module structure. Project conventions win: if CLAUDE.md, AGENTS.md, lint config, or the established layout says otherwise, follow the project and do not restructure to match these rules. Apply them to new files and to code you are already changing; never widen scope just to enforce them.

## 1. Entry Files Stay Thin

`index.ts` (and equivalents such as `__init__.py`, `mod.rs`) should contain only:

- re-exports (`export { ... } from "./module"`)
- factory calls that compose modules
- top-level wiring or registration

Avoid business logic, helpers, non-trivial type definitions, or unrelated responsibilities there. If you need to add logic to a mixed entry file, put the new logic in its own file instead of growing the entry file. Extracting existing logic is a refactor: do it only when requested or required, via `/omo-refactor`.

## 2. No Catch-All Files

New `utils.ts`, `helpers.ts`, `common.ts`, or a `service.ts` covering several domains become gravity wells. Name the file after what it does:

| Instead of | Prefer |
|---|---|
| `utils.ts` with `formatDate()`, `slugify()`, `retry()` | `date-formatter.ts`, `slugify.ts`, `retry.ts` |
| `service.ts` for auth + billing + notifications | `auth-service.ts`, `billing-service.ts`, `notification-service.ts` |
| `helpers.ts` with 15 unrelated exports | one file per domain |

If the project already uses a `utils/` directory or similar convention, add a focused file inside it rather than fighting the layout.

Each module should be independently importable, declare its dependencies explicitly, and be nameable by purpose.

## 3. One Responsibility Per File

Self-test: describe the file in one short phrase ("parses YAML frontmatter", "matches rules against paths"). If you cannot, it does too much.

Split signals:

- two or more unrelated exported functions
- I/O mixed with pure logic
- scrolling needed to understand the file

## 4. Size Budget: About 200 LOC

A file over roughly 200 lines of logic is a smell worth flagging.

Count: imports, declarations, function / class / type definitions, control flow, expressions. Exclude: blank lines, comment-only lines, and prompt or template text inside string literals.

When a file you are editing is over budget:

1. Do not push it further past the budget. Put new responsibilities in a new focused module.
2. Flag the existing overage in the delivery report with the responsibilities you see.
3. Split it only when the task asks for it or the change cannot be made cleanly otherwise, and then lock behavior first (`/omo-refactor`).

Generated files, fixtures, tables, and files where the project accepts larger modules are exempt.

## Applying

- Before adding code, check the file you touch against these defaults.
- New file: one responsibility, purpose-based name, within budget.
- Adding to an existing file: do not add a second responsibility or push it over budget; extract the new part instead.
- Report any violation you left in place and why (project convention, out of scope).
