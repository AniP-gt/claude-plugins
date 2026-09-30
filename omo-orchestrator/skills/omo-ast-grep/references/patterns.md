# Pattern Syntax

Patterns are written in the target language's own syntax and matched against each file's AST. The wildcards are meta-variables.

## Meta-variables

| Syntax | Matches | Captured |
|---|---|---|
| `$VAR` | exactly one AST node | yes, by name |
| `$$$` | zero or more nodes | no |
| `$$$VAR` | zero or more nodes | yes, by name |
| `$_` | one node | no |

- A meta-variable replaces a whole node, never part of an identifier.
- Names: `$` then uppercase letters, digits, or underscores (`$X`, `$VAR_1`, `$_VAR`). `$lower`, `$1`, `$kebab-case` are invalid.
- Same name means same text: `$X === $X` matches `a === a`, not `a === b`. Use `$X = $Y` for independent captures.

## `$$$` is greedy and does not backtrack

`foo($$$A, b, $$$C)` on `foo(a, c, b, b, c)` gives `$$$A = [a, c]`, `$$$C = [b, c]`.

- Exactly one argument: `foo($X)`.
- At least one argument: `foo($X, $$$REST)`.
- `foo($$$X)` also matches `foo()`.

## Patterns must be valid code

| Bad | Fix |
|---|---|
| `function $NAME` | `function $NAME($$$) { $$$ }` |
| `def $FN($$$):` | `def $FN($$$)` |
| `class Foo:` | `class $C($$$)` |
| `fn $NAME` | `fn $NAME($$$) { $$$ }` |
| `func foo` | `func $NAME($$$) { $$$ }` |
| `public void foo` | `public void $NAME($$$) { $$$ }` |
| `"key": "$VAL"` (JSON) | `pattern: { context: '{"key": "$VAL"}', selector: pair }` |

When the fragment is only valid inside a larger construct, parse the larger construct and select the sub-node:

```yaml
pattern:
  context: 'class A { $FIELD = $INIT }'
  selector: field_definition
```

## Strictness

`--strictness <level>` on the CLI or `strictness:` in a pattern object.

| Level | Compares |
|---|---|
| `cst` | every node, including punctuation |
| `smart` (default) | all nodes except unnamed target nodes absent from the pattern |
| `ast` | named nodes only |
| `relaxed` | named nodes, ignoring comments |
| `signature` | node kinds only, text ignored |

`smart` is almost always right.

## Checking what a pattern parses to

```bash
ast-grep run -p 'console.log($MSG)' --lang ts --debug-query=ast --stdin <<< 'console.log(1)'
# Node kinds of real code: paste a snippet of it as the pattern
ast-grep run -p 'try { a() } catch (e) {}' --lang js --debug-query=ast --stdin </dev/null
```

`--debug-query` prints the tree of the pattern, not of the searched files. `ast` shows named nodes with field names (`body:`, `handler:`), `cst` adds punctuation. Output goes to stderr. Playground: <https://ast-grep.github.io/playground.html>. Official guide: <https://ast-grep.github.io/guide/pattern-syntax.html>.
