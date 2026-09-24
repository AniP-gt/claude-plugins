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

1. Define trusted boundaries, attacker capabilities, assets, non-goals, target scope, base or diff, and safe-test constraints.
2. Run exactly three independent, bounded hunter passes: attack surface and trust boundaries; auth, authorization, data isolation, injection, and secrets; then runtime, filesystem, subprocess, archive, dependency, configuration, and install risks. Each pass covers only its assigned lane and returns before candidates are deduplicated.
3. Deduplicate plausible candidates and give them to exactly two independent, bounded PoC passes. Each pass reproduces, falsifies, or documents why only a safe static or dry-run proof is possible.
4. Cross-check candidates against the PoC results. Keep only candidates with a concrete attacker capability, attack path, preconditions, impact, and evidence.
5. Calibrate severity by actual exploitability and impact. Keep CWE classification separate from severity, and use OWASP or CVSS framing only when the assessment was actually performed.
6. Recommend the smallest fix that removes the exploit path and a regression check.

## Evidence Rules

- A vulnerability finding needs source, sink, attacker control, preconditions, impact, and mitigation.
- If exploitability is not proven, report it as a hypothesis or hardening note, not a confirmed vulnerability.
- Keep secrets out of reports and handoffs.
- Never run destructive exploits against real services or third-party systems. Use local fixtures, toy inputs, dry runs, or static proof.
- Every hunter and PoC pass must return its assigned lane or candidate set, candidates considered, evidence paths or commands, safe-proof result, rejected or untestable candidates, missing evidence, and one next action or stop reason.
- Return `INCONCLUSIVE` rather than a confirmed conclusion when required evidence or either independent PoC pass is unavailable. Record the gap and preserve only safe proof options.

## Output Contract

- Scope and threat model.
- Confirmed vulnerabilities ordered by severity.
- Exploitability evidence.
- Reproduced, downgraded, rejected, and unsafe-to-run candidates with their rationale.
- Missing evidence.
- Minimal remediation and regression guidance.
- Residual risk and the exact paths or commands supporting every surviving finding.
