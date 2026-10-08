---
type: llm
weight: 1
---

Score 1 only if the implementation or the final answer treats emails that differ only in letter case or surrounding whitespace as the same address (data/users.json has "aoki@example.com" and "Aoki@Example.com "), or explicitly raises this as a decision for the user. Score 0 if it compares raw strings and never mentions case or whitespace.
