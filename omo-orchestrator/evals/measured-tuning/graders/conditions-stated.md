---
type: llm
weight: 1
focus: trace
---

Judge only the assistant's own text messages to the user in the transcript, not tool calls or tool results. Score 1 only if one of those messages states the conditions of the speed measurement: the input size it used, and how many times it ran or how much the runs varied. Score 0 if either is missing from the messages.
