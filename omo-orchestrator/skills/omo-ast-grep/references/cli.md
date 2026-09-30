# CLI Reference

`ast-grep` and `sg` are the same binary. Recent releases print a deprecation warning for `sg`, and on Linux `sg` often resolves to `setgroups`, so prefer `ast-grep`.

## `ast-grep run`

`ast-grep -p 'foo'` is shorthand for `ast-grep run -p 'foo'`.

| Flag | Purpose |
|---|---|
| `-p, --pattern <P>` | AST pattern. Single-quote it. |
| `-r, --rewrite <R>` | Replacement. Without `-U` it only prints a diff. |
| `-l, --lang <LANG>` | Language. Inferred from the extension if omitted; required with `--stdin`. |
| `--selector <KIND>` | Use only this sub-node of the parsed pattern. |
| `--strictness <S>` | `cst`, `smart` (default), `ast`, `relaxed`, `signature` |
| `--debug-query[=F]` | Print the parsed pattern: `pattern`, `ast`, `cst`, `sexp` |
| `--stdin` | Read code from stdin. |
| `--globs <G>` | Include or exclude (`!` prefix). Repeatable. |
| `-A, -B, -C <N>` | Context lines. |
| `--json[=S]` | `pretty`, `stream`, `compact`. Disables `--update-all` silently. |
| `-U, --update-all` | Apply every rewrite. |
| `-i, --interactive` | Per-match confirmation. Needs a TTY, not usable by the agent. |

Exit code is 1 when nothing matched.

```bash
# Search
ast-grep run -p 'eval($CODE)' --lang js -C 3 src/

# Limit files
ast-grep run -p 'foo()' --lang ts --globs 'src/**/*.ts' --globs '!**/*.test.ts' .

# Preview a rewrite as a diff (no changes)
ast-grep run -p 'console.log($$$A)' -r 'logger.info($$$A)' --lang ts src/

# Apply the same rewrite after the preview is approved
ast-grep run -p 'console.log($$$A)' -r 'logger.info($$$A)' --lang ts --update-all src/

# Try a pattern on a snippet
echo 'console.log("x")' | ast-grep run -p 'console.log($MSG)' --lang js --stdin
```

## `ast-grep scan`

Runs YAML rules.

| Flag | Purpose |
|---|---|
| `-c, --config <C>` | `sgconfig.yml` path (default: search upward from cwd). |
| `-r, --rule <F>` | Run one rule file. No `sgconfig.yml` needed. |
| `--inline-rules <Y>` | Rule YAML as a string; separate rules with `---`. |
| `--filter <RE>` | Only rules whose `id` matches. |
| `-U, --update-all` | Apply every `fix:`. |
| `--report-style <S>` | `rich`, `medium`, `short` |
| `--format <F>` | `github`, `sarif` |
| `--error[=ID]` etc. | Override severity (`--warning`, `--info`, `--hint`, `--off`). |
| `--json[=S]` | JSON output. |

```bash
ast-grep scan -r rules/no-console.yml src/

ast-grep scan --inline-rules '
id: no-as-any
language: TypeScript
rule: { pattern: $E as any }' src/
```

## `ast-grep test`

Snapshot tests for rules. Flags: `-c` config, `-t` test dir, `--snapshot-dir`, `--skip-snapshot-tests`, `-U` update snapshots, `-f` filter by rule id. Test file format is in `sgconfig.md`.

## `ast-grep new`

Scaffolds `project`, `rule`, `test`, or `util`. It writes files into the project, so run it only when the user asked for rule setup.

## One-liners

```bash
# Matches per file
ast-grep run -p 'console.log($$$)' --lang ts --json=compact . \
  | jq -r '.[].file' | sort | uniq -c | sort -rn

# Node kinds of a code snippet (debug output is the pattern's tree)
ast-grep run -p 'const x = foo(1)' --lang ts --debug-query=ast --stdin </dev/null
```

Official: <https://ast-grep.github.io/reference/cli.html>
