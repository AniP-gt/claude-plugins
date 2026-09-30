# Delegation Prompt

Sub-agents are stateless. Every prompt carries all six sections, one atomic goal, and the context the worker cannot see. A prompt that leaves scope, verification, or forbidden actions implicit is not ready to send.

```markdown
## 1. TASK
<Quote the exact task item. One action per delegation.>

## 2. EXPECTED OUTCOME
- Files created or modified: <exact paths>
- Behavior: <exact observable result>
- Verification: `<command>` passes

## 3. REQUIRED TOOLS
- <tool>: <what to search, read, or run>

## 4. MUST DO
- Follow the pattern in <file:lines>
- Test <specific cases>

## 5. MUST NOT DO
- Do not modify files outside <scope>
- Do not add dependencies
- Do not skip verification
- Report out-of-scope findings instead of fixing them

## 6. CONTEXT
- Prior findings and decisions: <from earlier phases or the ledger>
- Conventions: <style, naming, patterns>
- Constraints: <original user constraints>
```

## Before and after each delegation

- Before: collect findings, decisions, and artifacts from earlier phases and put them in CONTEXT.
- After: check the result against EXPECTED OUTCOME, existing patterns, and the MUST DO / MUST NOT DO lists. Record what changed or was decided, then mark the task done. Do not start a dependent task before this check passes.

## Auto-continue

Once a verified step passes, dispatch the next ready step without asking "should I continue?". Ask the user only when the plan needs a decision, an external dependency blocks progress, or a critical failure stops all independent work. If one task stays blocked after its retry budget, record it and move to the next independent task.

## Anti-patterns

| Violation | Severity |
|---|---|
| Missing any of the six sections | HIGH |
| Asking to continue between verified steps | HIGH |
| Not passing prior context | HIGH |
| Starting the next task before verifying the current one | MEDIUM |
| Wrong owner for the task type | MEDIUM |
