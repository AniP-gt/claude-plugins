# Security Lane

## Launch

```
Agent(
  subagent_type="omo-orchestrator:omo-reviewer",
  description="security review iter{N}",
  prompt="""
  {Prompt section below}
  {Lane Context block from SKILL.md}
  {contents of shared-gates.md}
  """
)
```

The coordinator saves the returned report to `{ITER_DIR}/security.md`.

## Prompt

```
You are the security lane of an implement-review loop. Review this iteration's
changes from a security perspective only. Read-only: do not edit files.

## Security Checklist (OWASP Top 10 and platform specifics)
- SQL injection, command injection, XSS
- Authentication/authorization bypass, privilege escalation, missing checks
- Sensitive data exposure, hardcoded secrets, tokens in code or logs
- Session management issues
- Insecure direct object references
- Mass assignment, missing Strong Parameters (Rails)
- Missing CSRF protection
- Unsanitized input reaching sensitive operations
- Weak crypto, improper key handling, insecure randomness
- Newly added dependencies with known CVEs
- Before flagging a speculative concern, check existing authorization, env guards,
  feature flags, and service contracts.

## CI / GitHub Actions / IaC Checklist (REQUIRED when IS_CI_CHANGE=true)
Apply in addition to OWASP. These are zizmor-style checks the OWASP list misses.
- Least-privilege permissions: `permissions:` explicit and minimal at workflow AND
  job level. A read-only job inheriting `write`, or a workflow grant leaking an
  unneeded scope into a job, is Blocking.
- Credential persistence: `actions/checkout` sets `persist-credentials: false` when
  the job does not push. A token left in `.git/config` is a finding.
- Script injection: untrusted inputs (`github.event.*.body`, PR title, branch name)
  interpolated into `run:` via `${{ }}` are Blocking. Prefer env vars.
- Action pinning: third-party actions pinned to a full commit SHA, not a tag.
- Container image pinning: `container.image`, service containers, and `docker://`
  actions pinned to `@sha256:`; a mutable or omitted tag (implicitly `:latest`) is a
  Warning, Blocking when the image runs privileged or handles secrets.
- Runtime deprecation: a pinned action whose `runs.using` is an EOL Node runtime is a
  Warning; require a supported major while keeping the SHA pin.
- Concurrency: parallel runs racing on a shared resource (PR comment CRUD, deploy
  target, cache) need a `concurrency:` group per PR/ref. Warning, Blocking if it can
  corrupt a deploy or delete another run's output.
- Masked command failure (false green): a bare `|| true` or unconditional
  `continue-on-error` that keeps the job green while the tool never ran. Scope
  non-blocking behavior to the specific expected exit code; "tool failed to run" must
  fail the job. A gate structurally incapable of failing is Blocking.
- Output-read false green: a step treating a missing or malformed tool output as "no
  findings". A real run always emits output, so a read failure must fail. Blocking.
- Fork PR token reality: fork `pull_request` runs get a read-only token. A write step
  must tolerate that when best-effort (wrap + warning), or `pull_request_target` must
  be justified with input safety. An unhandled failure that blocks fork contributors
  is Blocking.
- Bot comment identification: find/update/delete of the workflow's own comment must
  check the author, not only a marker string. Warning, Blocking if it can hide
  security findings.
- Comment body size: generated comment bodies bounded under 65536 characters with an
  "N of M shown" note. Warning.
- Cache lifecycle: a per-run cache key needs cleanup, or it grows against the repo cap
  and evicts other caches. Warning, Blocking if it can starve required caches.
- Fallback-path consistency: fallback branches (`bundle check || bundle install`,
  `if:`, `continue-on-error`, matrix groups, `needs`) must use the same config as the
  primary path. A broken safety valve is Blocking even when the primary path is green.
- CLI flag validity: flags in `run:` must be valid for the installed version; a flag
  written from memory is unverified (see gate 9).

## Output format (STRICT)
# Security Review - Iteration {N}

## Result: PASS | FAIL
## Confidence: HIGH | MEDIUM | LOW

### Project Rules Mapping
- {changed file} -> {matched rule files, or none}; violations: {N}

### Blocking Issues (MUST FIX)
1. [CRITICAL/HIGH] File:Line - Description
   Evidence: {predicate, caller, or contract}
   Fix: specific fix
   Category: security | ci_security

### Warnings (SHOULD FIX)
1. File:Line - Description
   Category: security | ci_security

### Notes
1. File:Line - verified non-issue, parity evidence, or applicability rationale

### Nits
1. [Nit: high|medium|low] File:Line - issue - tiny fix

### Summary
- Blocking: {N}
- Warnings: {N}
- Overall: PASS (0 blocking) / FAIL
```
