# Pitfalls

Most "0 matches" and "matched the wrong thing" cases come from this list.

## 1. Regex syntax does not work

| Bad | Use instead |
|---|---|
| `foo\|bar` | two searches, YAML `any:`, or Grep |
| `foo.*bar` | `$$$` if the gap is a node list, otherwise Grep |
| `\w+`, `\d+`, `\s` | `$VAR`; for numbers use `kind: number` (name varies by grammar) |
| `[a-z]+` | Grep |
| `^foo$` | relational rules (`inside`, `not has`) |

When regex over node text is genuinely needed, use the YAML `regex` field. It must match the whole node text and should be combined with `kind` or `pattern`:

```yaml
rule:
  all:
    - kind: identifier
    - regex: '^[A-Z][a-z]+$'
```

## 2. Incomplete nodes

See the table in `patterns.md`. If a correct-looking pattern finds nothing, run it with `--debug-query=ast --stdin` and look for `ERROR` nodes.

## 3. Pattern parses as the wrong kind

`a = 123` parses as an assignment expression, even with `kind: field_definition` alongside it. `kind` and `pattern` are independent constraints; `kind` does not change how the pattern parses. Use `context` + `selector`.

## 4. Bare `|` is bitwise-or

`pattern: foo | bar` matches `x | y` expressions. For alternation use `any:`. In TypeScript types, `A | B` is a union type and does match unions.

## 5. `kind` names depend on the grammar

JS `function_declaration`, Python `function_definition`, Rust `function_item`, Go `function_declaration`. Find the right name with:

```bash
ast-grep run -p 'def foo(x): return x' --lang py --debug-query=ast --stdin </dev/null
```

`--debug-query` prints the pattern's tree, so use a snippet of the real code as the pattern.

Abstract supertypes such as `statement` are not matchable kinds in every grammar. A rule using `kind: statement` can silently match nothing or everything; use concrete kinds or `nthChild`.

## 6. `inside` and `has` default to `stopBy: neighbor`

Without `stopBy: end`, `inside` checks only the direct parent and `has` checks only direct children.

```yaml
has:
  kind: return_statement
  stopBy: end
```

## 7. `--json` silently disables `--update-all`

`ast-grep run -p P -r R --json=compact --update-all .` prints JSON and changes nothing (confirmed on 0.45.3). Preview with `-r` alone (prints a diff) or with `--json`, then apply in a separate run with `--update-all` and no `--json`.

## 8. Composite rules apply to one node

```yaml
# Wrong: one node cannot be both kinds
has:
  all: [{ kind: number }, { kind: string }]

# Right
all:
  - has: { kind: number }
  - has: { kind: string }
```

## 9. Capture order in implicit `all`

A rule object with several fields is an implicit `all`, but evaluation order is not guaranteed. If `transform` or `fix` depends on which sub-rule captured a variable, use an explicit `all:` list.

## 10. `regex` alone is slow

It tests every node in every file. Pair it with `kind`, e.g. `kind: comment` + `regex: '^//\s*TODO'`.

## 11. No scope, type, or data-flow analysis

ast-grep does not know whether two `foo` references are the same binding, whether a variable is shadowed or unused, what a function returns, or how values flow. Use LSP diagnostics, the type checker, or a dataflow tool for those questions, and say so in the report.

## 12. Shell quoting

Double quotes let the shell expand `$VAR` to an empty string. Always single-quote patterns and rewrites.
