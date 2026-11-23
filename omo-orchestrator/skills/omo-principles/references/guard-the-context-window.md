# Guard the Context Window

**Trigger:** Apply when context is filling up: large outputs, long files, repeated reads, fan-out planning. Route bulk to subagents; keep summaries in the main thread, not raw payloads.

**Why:** Context overflow degrades reasoning quality, creates compression artifacts, and halts progress.

**Pattern:**
- **Size phases and cap scope.** Limit files per phase, set turn budgets, account for mechanism costs.

In omo, the work budget for each sub-agent brief and the handoff thresholds are in the `omo-guardrails` skill's `references/context-and-handoff.md`.
