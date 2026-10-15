# Test Design Techniques

Pick techniques by the shape of the target. Most units need equivalence partitions plus boundaries; add the others when the shape calls for them.

| Target shape | Technique |
|---|---|
| A value with valid and invalid ranges | Equivalence partitioning + boundary values |
| Several conditions that combine into one outcome | Decision table |
| An object with a lifecycle or status column | State transition |
| Many independent parameters (options, flags, config) | Pairwise |
| Branching code | Branch and condition coverage |
| Code with side effects | Side effect checks |

## Black-box

### Equivalence partitioning

Split each input into classes the code treats the same way: valid classes and each distinct invalid class (nil or undefined, empty, wrong type, out of range, wrong format). One case per class is enough; more cases in the same class add no information.

### Boundary values

For each ordered range, test the boundary and the values on both sides: `min - 1`, `min`, `max`, `max + 1`. Check the operator in the code (`<` or `<=`), since off-by-one bugs live here. Include implicit boundaries: 0, empty collection, a single element, the column or string length limit, the page size, the start and end of a day, month, or fiscal year.

### Decision table

List the conditions and the outcomes as a table, one column per meaningful combination. Collapse combinations where one condition decides the outcome alone (for example, "not logged in" gives 401 regardless of the others). Each remaining column is one case.

### State transition

Draw states and events. Cover every valid transition once, and the invalid transitions that matter (an event on a terminal state, a skipped step, repeating the same event). Check what is written on each transition (timestamps, history rows, notifications).

### Pairwise

When there are many independent parameters, cover every pair of values instead of every combination. Use it only for parameters that do not interact through one condition; interacting conditions belong in a decision table.

### Error guessing

Add cases for failures seen in this codebase: search git history and closed issues for bug fixes in the same area, and add a regression case for any not covered.

## White-box

### Branch coverage

Each `if`, `case`, ternary, guard clause, early return, and `&.` or `?.` has at least one case per outcome.

### Condition coverage

For a compound condition (`a && b || c`), show that each sub-condition can change the result on its own (the MC/DC idea): for each sub-condition, find a pair of cases that differ only in that sub-condition and give different results. Use this for conditions with business impact (authorization, pricing, eligibility), not for every compound condition.

### Loops

Iteration count 0, 1, and many. For batching, a count exactly at the batch size and one over it.

### Exception paths

Each `rescue`, `catch`, `ensure`, or `finally`: trigger it and check what the caller sees (re-raise, return value, logged message, retry count) and that cleanup ran.

### Side effects

For each write the unit makes, check it happened with the right values, and that it did not happen on the failure path: DB rows, enqueued jobs, sent mail, published events, cache writes, external calls. In a transaction, check rollback on failure.

## What not to test

- Framework or library behavior (that `validates :presence` works, that `useState` updates).
- Private methods directly; test them through the public interface.
- Exact log text or internal call order, unless a consumer depends on it.
- Trivial getters, setters, and constants with no logic.
