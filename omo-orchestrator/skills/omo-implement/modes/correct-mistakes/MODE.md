# OMO Correct

Find the mistakes agents keep repeating in this repository and make each one impossible: architecture first, then types, then a lint or check whose error names the fix, then a test, and written rules last. Run it only when the user asks for it (`/omo-implement correct-mistakes`, "make this mistake impossible", "stop agents repeating this"). When the user corrects the same kind of mistake a second time, offer it rather than entering it.

Ported from the pstack `correct` skill (cursor/plugins `pstack`, commit `7a58391`, MIT, Copyright (c) 2026 Lauren Tan; license in the `omo-principles` skill's `LICENSE.pstack`). It applies the `omo-principles` reference `encode-lessons-in-structure`; read it first.

This mode replaces the default `omo-implement` steps for finding what to change. Planning, the `LOAD_SKILLS` line on every dispatch, the review gate, and the user's commit rules still apply. Main context only: a sub-agent returns the request to its caller.

Assume every contributor is an agent that sees only the files it opened, copies the nearest example, and takes the shortest path that compiles. Design the repository so a change that looks right from one file is right for the whole repository.

## 1. Find the mistake classes

Dispatch `omo-researcher` (`LOAD_SKILLS: [omo-principles]`; it preloads `omo-research`) to read recent commits, reverts, review comments, `CLAUDE.md`, `AGENTS.md`, `.claude/rules/`, and comments that explain workarounds, plus the corrections the user made in this session. Group the mistakes into classes. A class counts once it has happened twice; cite each occurrence (commit SHA, PR comment, `file:line`, or the user's message).

## 2. Pick the highest level that works for each class

1. **Eliminate it with architecture.** Give each piece of state one owner and each task one supported way. Hide internals so the wrong import fails. Replace hand-synced lists with one source of truth. Delete old ways and dead code an agent would copy.
2. **Enforce it with types** so the bad state cannot be written. If bad code still compiles, add a lint or CI check whose error names the file, type, or function to use instead (the `omo-research` mode `ast-grep` writes YAML rules). If the pattern is already common, fail only when a change adds more.
3. **Test the behavior.** Fix or delete any test that still passes when the behavior it checks breaks, or fails when only the internals change (`test-behavior-not-implementation`).
4. **Write a rule last, only for judgment calls.** Nothing fails when an agent skips it. Put it where the project keeps rules (`.claude/rules/`, `CLAUDE.md`, `AGENTS.md`); `omo-init-deep` maintains a generated rule set.

Present the classes, the level picked for each, and why a higher level did not work, as part of the `omo-plan` approval brief.

## 3. Fix and prove

Fix the most frequent classes through the default `omo-implement` flow, one commit per class. Prove each new check fails on a real past mistake: check out or reconstruct that mistake, run the check, and record the failing output before the fix lands. Run the same command locally that CI runs. An exception goes on the offending line with a reason, an expiry date, and the user's approval.

## 4. Keep the rule table

Keep a table in the project's agent instruction file that pairs each rule with what enforces it (the lint, type, test, or "judgment: written rule only"). When the user corrects you again, fix the mistake and add the row. If the rule was already there and nothing enforces it, that is a repeat: fix it at the highest level in the same change. Drop a row once its mistake can no longer happen.

## Reply

Each class with its evidence, the level picked and why a higher level did not work, the check's failing output on the past mistake, and the commit for each fix.
