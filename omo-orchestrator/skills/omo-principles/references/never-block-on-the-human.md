# Never Block on the Human

**Trigger:** Apply when tempted to ask 'should I do X?' on reversible work.

The human supervises asynchronously. Agents must stay unblocked. Make reasonable decisions, proceed, and let the human course-correct after the fact. Since code changes are reversible and reviewable, a wrong decision usually costs less than blocking.

- Proceed, then present. Do the work, show the result. Don't ask "should I do X?" Do X, explain why.
- Make the system self-healing. When you notice a problem, log it and fix it in the next round.
- Irreversible actions (force-push, delete production data, send external messages) still require confirmation.
- Reversible actions (write code, edit notes, split tasks) should proceed without blocking.
- Product direction comes from the human. Execution should not block.

In omo this covers execution choices only. The rules that require asking still apply, including: the `omo-plan` approval gate (approving a plan never authorizes implementation), one precise question when missing information materially changes the result (`omo-guardrails`), a user-facing limit, frequency, or value that the request or issue does not state (`omo-plan`, `omo-implement`), a declined permission or a refusal (`omo-guardrails`), and every action the user's own instructions say to confirm first.
