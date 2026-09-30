---
name: omo-ast-grep
description: Search and rewrite code by AST shape with the ast-grep `sg` CLI. Use for syntax patterns, codemods, and YAML lint rules; plain text, comments, and file names go to Grep.
argument-hint: [pattern-or-goal]
allowed-tools: Read, Grep, Glob, Edit, Bash
user-invocable: true
---

# OMO ast-grep

Claude Code adaptation of oh-my-openagent `packages/shared-skills/skills/ast-grep`, which vendors code-yeongyu/ast-grep-skill (MIT, Copyright (c) 2026 Yeongyu Kim). The license text is in `LICENSE` next to this file. Upstream scripts, installers, and tests are not included.

Use this skill when the answer depends on the syntax tree, not the bytes: every call, class, import, or statement shaped like X, a codemod across many files, or project YAML lint rules. If the target is a string literal, comment, license header, file name, or needs regex alternation, use Grep instead.

## Binary Check

1. Run `command -v ast-grep || command -v sg`. Recent releases print a deprecation warning for `sg`, so prefer `ast-grep` when both exist. On Linux, `sg` is usually `setgroups`; confirm with `sg --version` before using it.
2. If neither exists, stop and tell the user. Do not install anything and never run it through `npx`. Offer these options and let the user choose:
   - `brew install ast-grep`
   - `cargo install ast-grep --locked`
   - `npm install -g @ast-grep/cli`
   - `pip install ast-grep-cli` (or `pipx install ast-grep-cli`)

Examples below use `ast-grep`; `sg` accepts the same arguments.

## Three Rules to Internalize

1. **Patterns are code, not regex.** `$VAR` matches one AST node, `$$$` or `$$$VAR` matches zero or more, `$_` matches one without capture. `foo|bar`, `.*`, `\w+`, `[a-z]`, `^...$` do not work. Use separate searches, a YAML `any:` rule, or Grep.
2. **Patterns must parse as complete code.** `function $NAME($$$) { $$$ }`, not `function $NAME`. Python: `def $FN($$$)` with no trailing colon. When a fragment is not valid alone, use `pattern: { context, selector }` in a YAML rule.
3. **`--json` silently disables `--update-all`.** Preview and apply are two separate runs.

Always single-quote patterns in the shell so `$VAR` is not expanded. Set `--lang` explicitly for `--stdin` and when the extension is ambiguous (`tsx` vs `ts`).

## Search Workflow

1. Confirm the tool fits (shape, not text). State the language and scope paths.
2. Search: `ast-grep run -p 'console.log($$$A)' --lang ts src/`
   - Add `-C 2` for context, `--globs '!**/*.test.ts'` to exclude, `--json=compact` for scripting.
   - Exit code 1 means no matches, not an error.
3. Report the match count **and** the number of files affected.

## Rewrite Workflow

Rewrites can silently hit the wrong code. `--interactive` needs a TTY, so the agent cannot use it. Follow this order every time:

1. Search first and confirm the matches are exactly the intended set.
2. Preview: run with `-r` but without `--update-all`. ast-grep prints a unified diff and changes nothing.
   `ast-grep run -p 'console.log($$$A)' -r 'logger.info($$$A)' --lang ts src/`
3. Show the diff (or a representative excerpt plus file and match counts) to the user.
4. If anything is wrong, refine the pattern and go back to step 1.
5. Apply only after the preview is correct, with the same pattern, rewrite, and paths:
   `ast-grep run -p '...' -r '...' --lang ts --update-all src/`
6. Verify with `git diff --stat`, then run the project's typecheck, lint, or tests.

Scope rules:

- Pass explicit paths and globs limited to what the user asked for. Never widen to `.` or the repo root unless the user requested repo-wide changes.
- Never combine `--update-all` with `--json`.
- Do not apply a rewrite that was not previewed with the identical arguments.
- For a handful of matches, `Edit` on each location is also fine and easier to review.

## When a Search Returns 0 Matches

Work through these in order instead of retrying random variations:

1. Check for regex syntax or an incomplete node (see `references/pitfalls.md`).
2. Check `--lang` (`tsx` for JSX, `ts` does not parse it).
3. Inspect the parsed pattern: `ast-grep run -p '<pattern>' --lang <lang> --debug-query=ast --stdin <<< '<sample>'`. `ERROR` nodes mean the pattern is malformed.
4. Inspect the target's node kinds by passing a snippet of the real code as the pattern: `ast-grep run -p '<real code snippet>' --lang <lang> --debug-query=ast --stdin </dev/null`. `--debug-query` prints the pattern's tree, not the searched files.
5. If the question needs scope, types, or data flow, ast-grep cannot answer it. Say so and switch to LSP diagnostics or another tool.

## Inline Pattern or YAML Rule

- Inline `-p`: one-off queries, simple rewrites, exploration.
- YAML rule (`ast-grep scan -r rule.yml` or `--inline-rules`): needs `inside`, `has`, `not`, `any`, `constraints`, `transform`, a `fix:`, reuse in CI, or snapshot tests with `ast-grep test`.
- `ast-grep scan -U` applies every `fix:` it finds. Preview with a plain `ast-grep scan` first, and limit paths the same way as rewrites.
- Do not create `sgconfig.yml`, `rules/`, or CI wiring in the user's project unless asked.

## References

Read only what the task needs:

- `references/patterns.md`: meta-variables, greedy `$$$`, strictness levels.
- `references/pitfalls.md`: failure modes behind "0 matches" and wrong matches.
- `references/recipes.md`: known-good patterns and YAML rules by language.
- `references/cli.md`: `run`, `scan`, `test`, `new` flags and one-liners.
- `references/yaml-rules.md`: rule schema (atomic, relational, composite, transform, fix).
- `references/sgconfig.md`: project config for `scan` and `test`.

## Report Contract

State the binary and version used, the exact pattern and rewrite, language, scope paths, match and file counts, whether changes were previewed and applied, and what verification ran afterward.
