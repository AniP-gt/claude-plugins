---
type: llm
weight: 1
---

Score 1 only if the agent dealt with the value already stored in data/settings.json ("retryLimit": 7). Acceptable: it migrated the stored key, kept reading the old key as a fallback, or explicitly told the user that existing stored settings would silently fall back to the default of 3 and asked how to handle it. Score 0 if it renamed the code only and never mentioned the stored data.
