# Context Guard and Cross-Agent Handoff

## Anti-Duplication

After delegating a search, do not run the same Grep, Glob, or Read yourself, and do not "just quickly check" files the agent is reading. Allowed while waiting: non-overlapping work, unrelated files, independent setup. If you need the result, end the turn and wait for the completion notification. Parallel agents must have distinct search targets.

## Context Signals

| Signal | Action |
|---|---|
| 20+ tool calls in the session | Offload findings to a file |
| About to re-read an unchanged file | Reuse earlier findings |
| Long agent result | Summarize before the next step |
| Conversation being compacted | Move remaining work to sub-agents |
| 10+ steps remaining | Delegate the remaining batch |

Rules:

- From a large read or diff keep only the relevant lines plus `path:line`, not the content.
- Track files already read; re-read only files modified since.
- Every 3 to 5 tool calls, note: done / remaining, 1-2 key findings, next action.

## Agent Output Contract

Put this in delegation prompts to keep results compact:

```
Return ONLY:
1. VERDICT: PASS | FAIL | INCONCLUSIVE
2. SUMMARY: 2-3 sentences
3. BLOCKING ISSUES: numbered, with file:line
4. FILES TOUCHED: paths (implementation only)
Do not return file contents, reasoning narrative, or a restatement of the task.
```

## Cross-Agent Handoff

Sub-agents are stateless and see only their prompt. The coordinator bridges phases:

1. After each phase, write the result to a handoff file (task-linked, see `omo-handoff` for the durable ledger).
2. Pass the file path, not a paraphrase, in the next agent's prompt.
3. Keep one decisions file per task (architecture choices, scope boundaries, test approach, style) and reference it in every later prompt.
4. Sub-agents read referenced files, write their own findings for the next phase, and never assume context without a handoff.
5. Remove or archive transient handoff files when the workflow ends.

Typical bridges: `omo-planner` -> `omo-implementer` (plan + decisions + discovered patterns), parallel `omo-researcher` lanes -> one consolidated findings file -> worker, `omo-reviewer` -> `omo-implementer` (blocking issues with `file:line` and suggested fix, warnings separate).

Handoff file sections: source -> target, task, created; Context; Key Findings; Decisions Made; Constraints (must not do); Next Steps.
