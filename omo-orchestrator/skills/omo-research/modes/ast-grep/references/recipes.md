# Recipes

Starting points. Adjust names and scope, then follow the search, preview, apply order from `SKILL.md`. Rewrite lines below show the preview form; add `--update-all` only after the diff is approved.

## TypeScript / JavaScript

```text
function $NAME($$$PARAMS) { $$$BODY }
async function $NAME($$$PARAMS) { $$$BODY }
($$$PARAMS) => $BODY
import { $$$NAMES } from '$MOD'
import $DEFAULT from '$MOD'
import * as $NS from '$MOD'
console.$METHOD($$$ARGS)
<MyComponent $$$PROPS>$$$CHILDREN</MyComponent>      (use --lang tsx)
try { $$$BODY } catch ($E) { $$$HANDLER }
new $CLASS($$$ARGS)
$EXPR as any
$EXPR as unknown as $T
```

```bash
ast-grep run -p 'console.log($$$A)' -r 'logger.info($$$A)' --lang ts src/
ast-grep run -p 'oldName($$$A)' -r 'newName($$$A)' --lang ts src/
ast-grep run -p '$E as any' -r '$E' --lang ts src/          # review each hit; may break types
```

## Python

No trailing colon on block headers.

```text
def $FN($$$PARAMS)
async def $FN($$$PARAMS)
class $C($$$BASES)
print($$$ARGS)
with $CTX as $VAR: $$$BODY
[$EXPR for $VAR in $ITER]
Optional[$T]
```

```bash
ast-grep run -p 'print($$$A)' -r 'logger.info($$$A)' --lang py src/
ast-grep run -p 'Optional[$T]' -r '$T | None' --lang py src/   # needs Python 3.10+ or future annotations
```

## Go

```text
func $NAME($$$PARAMS) $$$RET { $$$BODY }
func ($RECV $TYPE) $NAME($$$PARAMS) $$$RET { $$$BODY }
if err != nil { $$$BODY }
fmt.$METHOD($$$ARGS)
defer $EXPR
go $EXPR
$EXPR.($TYPE)
```

## Rust

```text
fn $NAME($$$PARAMS) -> $RET { $$$BODY }
fn $NAME($$$PARAMS) { $$$BODY }
impl $TRAIT for $TYPE { $$$ITEMS }
match $EXPR { $$$ARMS }
$EXPR.unwrap()
$EXPR.expect($MSG)
println!($$$ARGS)
```

```bash
ast-grep run -p 'eprintln!($$$A)' -r 'log::error!($$$A)' --lang rust src/
```

Rewriting `.unwrap()` to `?` needs a `Result`-returning function around it. Find the sites, then decide per site.

## Java / C / C++

```text
System.$STREAM.println($$$ARGS)
$$$MOD $RET $NAME($$$P) { $$$BODY }
printf($$$ARGS)
malloc($SIZE)
std::make_unique<$T>($$$ARGS)
```

## YAML rules

Run with `ast-grep scan -r <file> <paths>`.

```yaml
id: no-console
language: TypeScript
severity: warning
message: Avoid console.* in production
rule:
  pattern: console.$METHOD($$$ARGS)
constraints:
  METHOD:
    not: { regex: '^(error|warn)$' }
fix: logger.$METHOD($$$ARGS)
```

```yaml
id: empty-catch
language: JavaScript
severity: error
message: Empty catch swallows errors
rule:
  kind: catch_clause
  has:
    field: body
    kind: statement_block
    not:
      has: { nthChild: 1 }
```

A catch block containing only a comment counts as non-empty here, since comments are named nodes. If a recipe rule reports nothing on code you know matches, check node kinds for the target grammar with `--debug-query=ast` (see `pitfalls.md`).

```yaml
id: no-unwrap
language: Rust
severity: warning
message: Handle or propagate the error instead of unwrap()
rule:
  pattern: $EXPR.unwrap()
```

Community rule catalog: <https://ast-grep.github.io/catalog/>
