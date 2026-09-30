# Baseline Detection And Report Template

## npm Package Baseline

Read-only. `npm view` queries the registry and never publishes.

```bash
PKG_NAME=$(node -p "require('./package.json').name" 2>/dev/null)
PUBLISHED=$(npm view "$PKG_NAME" version 2>/dev/null || echo "not published")
LOCAL=$(node -p "require('./package.json').version" 2>/dev/null || echo "unknown")
LATEST_TAG=$(git tag --sort=-v:refname | head -1)

BASE="v${PUBLISHED}"
git rev-parse --verify --quiet "$BASE" >/dev/null || BASE="${PUBLISHED}"
git rev-parse --verify --quiet "$BASE" >/dev/null || BASE="$LATEST_TAG"
```

- If the published tag is missing and you fall back to `LATEST_TAG`, record that as a weaker baseline and state that the tag may not match the published artifact.
- If `PUBLISHED` is `not published` and no tag exists, there is no verified baseline. Follow Workflow step 2.
- For other ecosystems, swap the registry query: `pip index versions <pkg>`, `cargo search <crate> --limit 1`, `gh release view --json tagName`, or the `version` field in a plugin `plugin.json` at the released commit.

## Collect The Diff

```bash
git log "${BASE}"..HEAD --oneline
git diff "${BASE}"..HEAD --stat
git diff --name-only "${BASE}"..HEAD
git diff "${BASE}"..HEAD            # read this, not only the log
git status --porcelain              # dirty work to separate out
```

## Describe Real Changes

Write what the diff does, not the commit title.

| Type | Weak | Required |
|------|------|----------|
| feat | "add X feature" | "Added X that does Y" |
| fix | "fix X bug" | "Fixed X happening when Y; now Z" |
| refactor | "rename X" | "Changed X from A to B; now supports C" |

Breaking-change checklist: config schema (new required or removed fields), public API (renamed exports, changed signatures), CLI (removed commands, changed flags or defaults), dependency changes (added, removed, major bumps, peer ranges).

## Report Template

```markdown
## Unpublished Changes ({baseline} -> HEAD)

**Published:** {published} | **Local:** {local} | **Commits:** {count}
**Baseline evidence:** {why this baseline applies}

### feat | fix | refactor | docs | internal
| Scope | What Changed | Impact |
|-------|--------------|--------|

### Breaking Changes
None, or each item with migration steps.

### Excluded Dirty Work
{paths and confirmation status}

### Files Changed
{diff --stat}

### Suggested Version Bump
- Recommendation: patch | minor | major
- Justification: {cited behavior or contract change}
```
