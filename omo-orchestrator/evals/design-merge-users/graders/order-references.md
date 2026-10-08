---
type: llm
weight: 1
---

Score 1 only if the agent noticed that data/orders.json refers to users by userId (order 102 belongs to user 2, a duplicate of user 1) and either reassigns those orders to the kept user or tells the user that merging would orphan them. Score 0 if orders are never mentioned.
