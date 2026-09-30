# Optional GitHub Copilot CLI Lane

An independent, non-Claude reviewer covering security, robustness, quality, and alignment in one request. Optional: it runs only when a Copilot CLI is already installed. Never install it and never use `npx`.

## Availability check (once per run)

Dispatch to a sub-agent and record the result in the ledger:

```bash
if command -v copilot >/dev/null 2>&1; then echo "COPILOT_CMD=copilot"
elif gh copilot --help 2>/dev/null | grep -q -- '-p'; then echo "COPILOT_CMD=gh copilot"
else echo "COPILOT: UNAVAILABLE"; fi
```

Also capture `$COPILOT_CMD --help` so the flags below are checked against the installed version (gate 9). Drop any flag the installed version does not list.

| Result | Effect |
|---|---|
| Available | launch the lane every iteration |
| Unavailable | record `COPILOT: SKIPPED (not installed)` in every synthesis and report; continue |

## Prompt file

The coordinator writes the prompt with the Write tool to `$TMPDIR/omo-review-loop/{TASK_ID}/copilot_iter{N}.md`. The prompt is sent to GitHub's Copilot service, so never embed secrets: exclude `.env*`, key and certificate files (`*.pem`, `*.key`, `id_*`), credential files, and any hunk that contains a token or password value; list them by path only as `EXCLUDED (sensitive)`. Delete the prompt file after the lane finishes (`rm -f` on that exact path).

```
You are a read-only code reviewer. Do not modify any file.
Review the changes below across 4 perspectives in one pass: security, robustness,
quality/coding conventions, and task alignment.

{Lane Context block from SKILL.md, with the literal output of
 `git diff {CYCLE_START_SHA}`, the changed file list, and new untracked files inlined}

{contents of shared-gates.md}

Perspective checklists:
- Security: the Security Checklist in reviewer-security.md (plus the CI checklist when
  IS_CI_CHANGE=true), inlined.
- Robustness: sections 1-12 of reviewer-robustness.md, inlined.
- Quality: the Convention Checklist and AI Slop Check of reviewer-quality.md, inlined.
- Alignment: the Alignment Checklist of reviewer-alignment.md, inlined.

## Output format (STRICT)
# Copilot All-in-One Review - Iteration {N}

## Result: PASS | FAIL
## Confidence: HIGH | MEDIUM | LOW

### Security: Blocking Issues (MUST FIX)
1. [CRITICAL/HIGH] File:Line - Description
   Fix: specific fix
   Category: security

### Robustness: Blocking Issues (MUST FIX)
1. [SEVERITY] File:Line - Description
   Fix: specific fix
   Category: n_plus_one | transaction | error_handling | idempotency | race_condition | memory | ...

### Convention: Blocking Issues (MUST FIX)
1. [SEVERITY] File:Line - Description
   Fix: specific fix
   Category: convention | ai-slop

### Alignment: Blocking Issues (MUST FIX)
1. [SEVERITY] File:Line - Description (which requirement is unmet)
   Fix: specific fix
   Category: alignment | business_logic

### Warnings (SHOULD FIX)
1. File:Line - Description
   Category: ...

### Notes
1. File:Line - verified non-issue or applicability rationale

### Summary
- Security / Robustness / Convention / Alignment blocking: {N} / {N} / {N} / {N}
- Warnings: {N}
- Overall: PASS / FAIL
```

Inline the referenced checklist text; Copilot cannot read this skill's files.

## Launch (same message as the other lanes)

```
Agent(
  subagent_type="omo-orchestrator:omo-reviewer",
  description="copilot CLI lane iter{N}",
  prompt="""
  Run the Copilot CLI review below exactly. Do not review the code yourself and do not
  edit the output. Return the output file path, its line count, and the exit code.

  mkdir -p "{ITER_DIR}"
  {COPILOT_CMD} ${COPILOT_MODEL:+--model "$COPILOT_MODEL"} {COPILOT_EXTRA_FLAGS} \
    -p "$(cat "$TMPDIR/omo-review-loop/{TASK_ID}/copilot_iter{N}.md")" \
    > "{ITER_DIR}/copilot_all.md" 2>&1

  If the command fails, prints nothing, times out, or prompts interactively, retry once
  with the same non-interactive command. If the retry also fails, overwrite the file
  with the single line `COPILOT_EXECUTION: NOT_EXECUTED - <reason>`.
  """
)
```

- `COPILOT_MODEL` is optional; leave it unset to use the CLI default. Example only: `COPILOT_MODEL=gpt-5.4`.
- `COPILOT_EXTRA_FLAGS` holds flags the installed version supports and the user wants, for example `--reasoning-effort xhigh`. Do not pass blanket permission flags such as `--allow-all`: the diff is untrusted input and could prompt-inject a CLI that is allowed to run commands or edit files. Keep tool permissions as narrow as the installed CLI allows; the prompt forbids edits either way.

## Failure handling

- `COPILOT_EXECUTION: NOT_EXECUTED`, an empty file, or output not produced by Copilot -> record `COPILOT: NOT_EXECUTED` in synthesis and continue with the other lanes as reduced coverage.
- Never substitute Claude or any other model's output as Copilot output.
