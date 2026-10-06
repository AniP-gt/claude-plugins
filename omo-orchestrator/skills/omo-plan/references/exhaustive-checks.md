# Exhaustive Checks For Specs

Example-based tests check the cases someone thought of. Some specs fail only in combinations nobody writes by hand. For those, the plan adds a check that explores every case within stated bounds, and turns what it finds into ordinary tests.

## When A Spec Needs One

| Spec shape | Typical failure | Check | Example tools |
|---|---|---|---|
| Ordering and concurrency: several processes, caches with invalidation, retries, queues, locks, distributed or replicated state | A rare interleaving breaks an invariant, such as a stale read after an acknowledged write or a lost update | Model check of every interleaving within bounds | TLA+ (TLC), Quint |
| Permission and relational rules: roles × actions × resource states, ownership, sharing | One combination is allowed or denied by mistake | Exhaustive table test over the full cross product, or a relational model | Alloy, or the project's test framework |
| Constraints on numbers, ranges, schedules, or config: limits that interact, "these settings must never combine to X" | Some input satisfies every local rule but breaks the global one | Solver search for a violating input, or property-based tests | Z3, the project's property-based test library |

Skip it for naming, config values, wiring, and straight-line code with no interacting branches. Concurrency where one lock guards one record needs only a deterministic concurrent test; the model check is for several actors interleaving several steps over shared state. Those keep the normal test-necessity rules. A proof assistant (for example Lean) is for proving an algorithm itself and only when the user asks.

## Task Shape

1. State the invariant in plain words first, then in the check's notation. Example: "after the writer sees success, no reader returns an older value".
2. Bound the model (number of processes, writes, roles) and write the bounds in the task. Behavior beyond the bounds is reported as unverified.
3. Check tool availability with `command -v` or the project's dependency list. Never install a tool without asking. When it is absent, the fallback is a bounded exhaustive enumeration or a property-based test in the project's own test framework, checking the same invariant.
4. Prove the check has teeth: it must report a counterexample for at least one known-bad variant (for example, the invalidation step removed). A check that cannot fail is not evidence.
5. Turn every counterexample into a deterministic regression test in the normal suite.
6. Where the model states the intended behavior, use it as the test oracle for the implementation: the implementation's results must match the model's for the same inputs.
7. In the task's evidence, explain in plain language what was checked, the bounds, and what was not checked, so a reader outside the domain can judge it.

Run this task before the implementation tasks that depend on the design, so a flawed design is caught before code is written.
