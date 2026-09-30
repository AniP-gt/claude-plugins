# Comment Patterns

Comments explain WHY, not WHAT. Use this to classify comments added in the diff under review.

## How To Check

1. List changed files: `git diff --name-only` (or the files from recent edits).
2. Extract added comment lines (`//`, `#`, `/* */`, `/** */`, `<!-- -->`).
3. Classify each against the patterns below. Anything not matching a REMOVE pattern stays.

## REMOVE Patterns

### Restatement (worst offender)

Signals: the comment repeats words from the next line, starts with Get / Set / Return / Check / Create / Update / Delete plus a noun from the code, or is shorter than the code it describes.

```typescript
const userId = getUserId()  // Get the user ID
const items = list.filter(x => x.active)  // Filter active items
return result  // Return the result
```

Fix: delete the comment.

### Obvious JSDoc / docstrings

Signals: `@param id - The id`, `@returns The user`, or the name plus signature already say everything.

```typescript
/**
 * Gets the user by ID
 * @param id - The user ID
 * @returns The user
 */
function getUserById(id: string): User { ... }
```

Keep doc comments that state non-obvious contracts:

```typescript
/**
 * Retries up to 3 times with exponential backoff.
 * Returns null instead of throwing on permanent failures.
 */
function fetchWithRetry(url: string): Promise<Response | null> { ... }
```

### AI-sounding openers and generic verbs

Signals: "This function / method / class ...", "Handle / Process / Manage" plus a generic noun, or a comment on every line of a block.

### Section dividers

```typescript
// ==========================================
// Helper Functions
// ==========================================
// --- Validation ---
// *** IMPORTANT ***
```

Fix: delete. Organize code by structure instead.

### Change markers and AI attribution

```typescript
// Added by AI assistant
// Updated: now handles edge case
// Refactored for clarity
// Previously: old implementation was here
```

Fix: delete. Git history tracks changes.

### Over-explaining simple logic

```typescript
// Check if the array is empty, and if so, return early
// because we don't want to process empty arrays
if (items.length === 0) return
```

Fix: delete, or reduce to the real reason: `// downstream aggregation crashes on empty input`.

### Commented-out code

Signals: `//` followed by valid code, or `/* */` blocks containing code.

Fix: this is a deletion candidate. Follow `/omo-remove-deadcode` if it may still be referenced (feature flags, docs, copy-paste templates); otherwise delete. Git has the history.

## KEEP Patterns

```typescript
// Regulation requires a 30-day buffer for expiration checks
const bufferDays = 30

// NOTE: This API returns dates in JST, not UTC
const createdAt = parseJSTDate(response.created_at)

// Safari doesn't support lookbehind regex, using split instead
const parts = input.split(delimiter).filter(Boolean)

// See: https://github.com/org/repo/issues/123
```

Also keep: BDD comments (given / when / then), license headers, directives (`eslint-disable`, `noqa`, `type: ignore` with reason), and public API docs the project requires.

## Report Format

```text
| # | File:Line | Pattern | Comment | Action |
|---|-----------|---------|---------|--------|
| 1 | src/auth.ts:42 | Restatement | `// Get user` | Remove |
| 2 | src/api.ts:15 | Obvious JSDoc | `@param id - The id` | Remove block |
| 3 | src/old.ts:88 | Commented-out code | `// const x = ...` | Delete |

Summary: removed N restatements, N doc blocks, N commented-out blocks; kept N WHY comments.
```

## Project Rule Snippet

Suggest this for the project's CLAUDE.md / AGENTS.md when the user wants ongoing enforcement:

```markdown
## Comment Rules
- Do not add comments that restate what the code does
- Do not add JSDoc to functions whose name and signature are self-documenting
- Comment WHY, not WHAT
- Delete commented-out code (git has history)
- No section divider comments
```
