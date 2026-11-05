# YAML Rules

A rule file holds one or more rules separated by `---`. Run with `ast-grep scan -r file.yml <paths>` or load via `ruleDirs` in `sgconfig.yml`.

## Skeleton

```yaml
id: no-console
language: TypeScript
severity: warning            # hint (default) | info | warning | error | off
message: Avoid console.* in production
note: Use the project logger.
rule:
  pattern: console.$METHOD($$$ARGS)
constraints:
  METHOD:
    not: { regex: '^(error|warn)$' }
fix: logger.$METHOD($$$ARGS)
files: ['src/**/*.ts']
ignores: ['src/**/*.test.ts']
```

Required: `id`, `language`, `rule`. Optional: `constraints`, `utils`, `transform`, `fix`, `rewriters`, `severity`, `message` (may use `$VAR`), `note`, `labels`, `files`, `ignores`, `url`, `metadata`.

Languages include Bash, C, Cpp, CSharp, Css, Elixir, Go, Haskell, Html, Java, JavaScript, Json, Kotlin, Lua, Nix, Php, Python, Ruby, Rust, Scala, Solidity, Swift, TypeScript, Tsx, Yaml.

## Atomic rules

- `pattern`: string, or `{ context, selector, strictness }` object.
- `kind`: tree-sitter node type. 0.39+ also accepts simple selectors (`a > b`, `a + b`, `a ~ b`, `a b`).
- `regex`: Rust regex over the whole node text. No look-around or backreferences. Pair with `kind`.
- `nthChild`: 1-based index among named siblings, `2n+1` form, or `{ position, reverse, ofRule }`.
- `range`: `{ start: {line, column}, end: {line, column} }`, 0-based.

## Relational rules

| Rule | Target relation |
|---|---|
| `inside` | has an ancestor matching the sub-rule |
| `has` | has a descendant matching the sub-rule |
| `precedes` | comes before a matching sibling |
| `follows` | comes after a matching sibling |

Options: `stopBy: neighbor` (default, one level), `stopBy: end` (all the way), or a rule object (stop when it matches). `field:` restricts to a named child role such as `name`, `body`, `key`, `value`.

```yaml
rule:
  pattern: this.$PROP
  inside: { kind: class_body, stopBy: end }
```

## Composite rules

| Rule | Meaning |
|---|---|
| `all` | every sub-rule matches the same node; captures merge |
| `any` | at least one matches; only that branch's captures survive |
| `not` | the node must not match |
| `matches` | reference a util by id |

Several fields in one rule object are an implicit `all` with unspecified order. Use an explicit `all:` list when capture order matters.

```yaml
rule:
  all:
    - pattern: console.log($A)
    - not:
        inside: { kind: catch_clause, stopBy: end }
```

## constraints

Filter captured single meta-variables (`$VAR` only, not `$$$VAR`) after the main rule matches.

```yaml
constraints:
  NAME:
    regex: '^[a-z][a-zA-Z0-9]*$'
```

## utils

```yaml
utils:
  is-literal:
    any: [{ kind: number }, { kind: string }]
rule:
  all:
    - pattern: $X = $Y
    - has: { matches: is-literal }
```

Project-wide utils go in `utilDirs` (each file needs `id` and `language`).

## transform

Operations: `replace`, `substring`, `convert`, `rewrite`. Later transforms may use earlier results.

```yaml
rule:
  pattern: $OLD($$$A)
constraints:
  OLD: { regex: '^debug_' }
transform:
  NEW:
    replace: { source: $OLD, replace: '^debug_', by: 'release_' }
  KEBAB:
    convert: { source: $OLD, toCase: kebabCase }   # camelCase | snakeCase | pascalCase | upperCase | lowerCase | capitalize
fix: $NEW($$$A)
```

`substring: { source, startChar, endChar }` supports negative indices. `rewrite: { source, rewriters: [id], joinBy }` applies rules from the top-level `rewriters:` list (experimental).

## fix

- String template: `fix: logger.log($$$ARGS)`. `fix: ""` deletes the match.
- Object form to absorb surrounding characters, e.g. a trailing comma when deleting a list item:

```yaml
fix:
  template: ''
  expandEnd: { regex: ',' }
```

## Testing rules

Use `ast-grep test` with `valid:` / `invalid:` snippets (see `sgconfig.md`), or try the rule on a snippet first:

```bash
echo 'console.log(1)' | ast-grep scan --inline-rules "$(cat rule.yml)" --stdin
```

Official: <https://ast-grep.github.io/reference/rule.html>, <https://ast-grep.github.io/reference/yaml.html>
