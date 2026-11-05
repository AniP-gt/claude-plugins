# Delegation Prompt

Sub-agents are stateless. Every prompt carries all six sections (plus section 0 for gated workers), one atomic goal, and the context the worker cannot see. A prompt that leaves scope, verification, or forbidden actions implicit is not ready to send.

Every dispatch to a gated worker (`omo-implementer`, `omo-researcher`, `omo-reviewer`, `omo-planner`) also carries a `LOAD_SKILLS` line (section 0). A PreToolUse hook (`hooks/load-skills-gate.mjs`) denies a dispatch without it.

```markdown
## 0. LOAD_SKILLS
LOAD_SKILLS: [omo-test-design, omo-ast-grep]
(Or `none`. Choose per [skill-catalog.md](skill-catalog.md).)

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
- For acknowledged background delivery, missing output, or a late result, apply **Pending delivery and late results** below. Keep the original task/attempt identity and write ownership until termination is established; a follow-up timeout does not authorize resending or replacement. Reconcile late failures before reusing dependent claims or evidence.
- Put the project rules that apply to the target paths into CONTEXT, found and filtered per [project-rules.md](project-rules.md).

## Pending delivery and late results

- An acknowledgement, queued delivery, or background continuation is not a completed task. Record the task/agent ID, attempt, owned write paths, and the available result channel in the ledger. Use only status, output, notification, or messaging capabilities the current tools actually provide.
- Exhausting the one bounded missing-output follow-up marks evidence unavailable, not execution terminated. Keep a live task `running` with that annotation; its consumers remain pending until their prerequisites are verified. Continue independent authorized work when safe, and report a critical missing result as a blocker.
- Do not resend an acknowledged instruction or dispatch a replacement over the same write paths while the original execution may still run. Before retrying, establish terminal failure or confirmed cancellation and release of its write ownership. Evidence is a terminal tool status or an explicit owner report that execution and any spawned writers have stopped; an acknowledgement of a cancellation request is insufficient. If detached writers exist, verify their termination separately. If the available tools cannot establish that, leave replacement work blocked; elapsed time is not proof of termination. Apply this condition to all stalled/no-output recovery rules.
- Reconcile a late success or failure with its original task and attempt before using it. Record the outcome and evidence; verify a late success normally. A late failure corrects any provisional claims based on that attempt and invalidates only dependent evidence. Preserve unrelated verified results. A result from a superseded attempt cannot complete the current attempt; conflicting writes require inspection and revalidation before consumers resume.
- Correct already-shared claims in the next user update and ledger. For an external destination, prepare the correction and send it only within existing explicit authorization. Choose the available result channel and a finite follow-up window suited to the session; record both before waiting rather than inventing a runtime default.

## Auto-continue

Once a verified step passes, dispatch the next ready step without asking "should I continue?". Ask the user only when the plan needs a decision, an external dependency blocks progress, or a critical failure stops all independent work. If one task stays blocked after its retry budget, record it and move to the next independent task.

## Anti-patterns

| Violation | Severity |
|---|---|
| Missing any of the six sections (or section 0 for a gated worker) | HIGH |
| Asking to continue between verified steps | HIGH |
| Not passing prior context | HIGH |
| Starting the next task before verifying the current one | MEDIUM |
| Wrong owner for the task type | MEDIUM |
