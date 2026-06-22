---
name: omo-security-research
description: Exploitability-first security research workflow for OMO work. Uses evidence, PoC thinking, severity calibration, and safe reporting.
argument-hint: [scope]
allowed-tools: Read, Grep, Glob, Bash, Task
user-invocable: true
---

# OMO Security Research

Use this skill for security review, threat modeling, vulnerability research, or pre-release security checks.

## Workflow

1. Define trusted boundaries, attacker capabilities, assets, and non-goals.
2. Inventory entry points: user input, network, file system, subprocesses, credentials, auth, serialization, and plugin install paths.
3. Search for exploit paths, not just suspicious code.
4. For each candidate, prove or disprove exploitability with code evidence, control flow, tests, or a safe proof sketch.
5. Calibrate severity by actual impact and reachability.
6. Recommend the smallest fix that removes the exploit path.

## Evidence Rules

- A vulnerability finding needs source, sink, attacker control, preconditions, impact, and mitigation.
- If exploitability is not proven, report it as a hypothesis or hardening note, not a confirmed vulnerability.
- Keep secrets out of reports and handoffs.

## Output Contract

- Scope and threat model.
- Confirmed vulnerabilities ordered by severity.
- Exploitability evidence.
- Non-exploitable candidates that were checked.
- Missing evidence.
- Minimal remediation guidance.
