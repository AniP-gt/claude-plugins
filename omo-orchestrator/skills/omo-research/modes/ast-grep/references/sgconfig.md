# sgconfig.yml

`ast-grep scan` and `ast-grep test` look for `sgconfig.yml` by walking up from the current directory, or use `-c <path>`. Create or edit it only when the user asked for project rule setup; one-off work needs only `scan -r` or `--inline-rules`.

## Layout

```text
project/
  sgconfig.yml
  rules/        no-console.yml, no-as-any.yml
  utils/        is-literal.yml
  tests/        no-console.yml
    __snapshots__/
```

```yaml
ruleDirs: [rules]              # required, relative to sgconfig.yml
utilDirs: [utils]              # global utils usable via `matches: <id>`
testConfigs:
  - testDir: tests
    snapshotDir: __snapshots__ # default
languageGlobs:                 # override extension mapping
  html: ['*.vue', '*.svelte']
  tsx: ['*.ts']                # parse all .ts as TSX
```

Experimental, rarely needed: `customLanguages` (load an extra tree-sitter grammar) and `languageInjections` (e.g. CSS inside styled-components template literals).

## Test files

```yaml
id: no-console
valid:
  - 'logger.info("hi")'
invalid:
  - 'console.log("hi")'
```

`ast-grep test` compares matches against snapshots. `ast-grep test -U` creates or updates snapshots, so review the snapshot diff before accepting it.

## Monorepo

A package-level `sgconfig.yml` can include shared rules:

```yaml
ruleDirs:
  - rules
  - ../../shared-rules
```

## Editor schema hint

```yaml
# yaml-language-server: $schema=https://raw.githubusercontent.com/ast-grep/ast-grep/main/schemas/rule.json
```

Official: <https://ast-grep.github.io/reference/sgconfig.html>
