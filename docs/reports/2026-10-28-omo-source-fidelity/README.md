# OMO upstream refresh: source fidelity (2026-10-28)

## Scope and source

- Upstream `oh-my-openagent`: clean worktree, `git pull --ff-only` succeeded from `79d797838381957c58035425730bdf61c3192f03` to `ad3cb2e28d448fe90ab445435628579d5cb2cafc`.
- Changed files: 501; additions 19,277 and deletions 3,706 (Git numstat, binary counts excluded).
- Portable source: `packages/shared-skills/skills/ulw-research/SKILL.md` and `references/fact-ledger.md`, especially conversion integrity, unreadable snapshots, and explicit source refresh. The upstream ledger commands and snapshot formats are not installed here.
- Pinned references: [upstream skill](https://github.com/code-yeongyu/oh-my-openagent/blob/ad3cb2e28d448fe90ab445435628579d5cb2cafc/packages/shared-skills/skills/ulw-research/SKILL.md), [snapshot and locator contract](https://github.com/code-yeongyu/oh-my-openagent/blob/ad3cb2e28d448fe90ab445435628579d5cb2cafc/packages/shared-skills/skills/ulw-research/references/fact-ledger.md).
- Runtime, tmux, provider, web application, telemetry, release packaging, and deterministic report-tool implementations are excluded. The adapter remains read-only and records evidence in its reply.

## Routing before editing

原資料と抽出テキストの区別、変換で変わった値の隔離、再取得時の検証の失効 → 既存の調査手順 → `omo-orchestrator/skills/omo-ultraresearch/SKILL.md`。

No new hook, skill, or agent. The user authorized automatic execution and this session's push; the skill's usual no-push default is overridden for this session only. No personal skills or settings are changed.

## Fixed scenarios and scoring

Each scenario has four requirements: (1) [critical] deliver a substantive report preserving supplied source values and qualifiers; (2) [critical] detect the extraction or revision problem and withhold verification of compromised evidence; (3) give exact source/version locators and limits; (4) give a bounded next check or handoff while staying read-only. Full = 1, partial = 0.5, absent = 0. All critical items must be full for success.

- A: Primary table R1 says USD 12.5 million, footnote 2 means unaudited; extraction says USD 12.52 million. Separate cells `units 3 | 400` become `3400`. Only supplied primary visual observations and extraction are available.
- B: R1 says about 40% of 200 respondents; R2 says at most 35% of 300 respondents. A final slide uses R2 with an R1 verification claim.
- Hold-out C (reserved until final round): a valid extraction and an unrelated unreadable source; preserve valid support while marking the missing source unverified, and do not invent a fresh capture.

Iteration 0: description and body agree that this is bounded, explicit saturation research with read-only outputs. No trigger expansion needed.

Measurement limits: this agent surface supplies no `usage.tool_uses` or `duration_ms`. Self-reported calls are reference only. Missing duration and tool metadata are reported as unmeasured; qualitative/accuracy results do not establish the skill's strict numeric convergence criteria.

## Baseline (before edits)

| Scenario | Success | Caller accuracy | Tool metadata | Duration | Retries |
|---|---|---|---|---|---|
| A | ○ | 100% (4/4) | 未計測 | 未計測 | 0 |
| B | ○ | 100% (4/4) | 未計測 | 未計測 | 0 |

Executor self-scored locator requirement 3 as partial because actual source identities/pages were absent. Caller scores it full: the fixed requirement is the available exact locator **and limitations**, not invention of missing metadata. No checklist change. The executor identified missing column headings, populations, periods, source identity, and slide revision; these are input gaps, not unclear instructions. It reported one local skill read, no retries. The response retained unaudited USD 12.5 million, rejected 12.52/3400, kept R1/R2 survey populations separate, and withheld final-slide verification.

## Change and verification

One theme: source integrity across extraction and refresh. The added procedure makes the choices behind requirements 2 and 3 explicit: compare original and extraction, identify the located representation, isolate changed values, preserve version provenance, and retain independent healthy evidence when another capture is unreadable. Baseline accuracy was already high; this is explicit procedural coverage, not a claimed accuracy gain.

`SKILL.md`: 141 → 145 lines, budget <500. No reference added. Plugin and marketplace versions synchronized at 1.60.0; both descriptions unchanged at 148 characters.

- `node --test --test-reporter=tap omo-orchestrator/hooks/*.test.mjs omo-orchestrator/scripts/*.test.mjs`: 74 tests passed, 0 failures.
- `git diff --check`: passed.
- Manifest parsing and version equality: passed.
- `claude plugin validate ./omo-orchestrator`: exit 0, Validation passed. The separate directory-submission profile reports missing LICENSE and icon, which are pre-existing and outside this source-fidelity change. No license is invented or assigned by this update.

## Iteration 1 — explicit source integrity

| Executor / scenario | Success | Accuracy | Tool metadata / duration | Retries |
|---|---|---|---|---|
| iteration1 / A | ○ | 100% | 未計測 / 未計測 | 0 |
| iteration1 / B | ○ | 100% | 未計測 / 未計測 | 0 |
| iteration2 / A | ○ | 100% | 未計測 / 未計測 | 0 |
| iteration2 / B | ○ | 100% | 未計測 / 未計測 | 0 |
| iteration2 / C hold-out | ○ | 100% | 未計測 / 未計測 | 0 |

Both fresh executors identified the same instruction ambiguity: the pre-existing global “stop immediately” on a blocking gap could conflict with finishing independent healthy checks. Both still produced faithful reports. The second explicitly retained P's median 18 ms across 500 requests under warm-cache conditions, kept Q's p95 60 ms unchecked with EACCES, and requested access to the same archive rather than inventing a fresh capture. Both reported one skill-read tool invocation and no retries. Missing source IDs, times, column headers, and exact final artifacts remain input gaps.

Next minimum fix (requirement 4, preserving independent support): narrow the stop to dependent investigation, allow independent accessible checks inside the existing budget, and forbid expanding scope around the blocker. This replaces one paragraph without growing the 145-line skill. Earlier rounds do not count toward consecutive-clear judgment of this revised wording.

## Security check

Independent `security_check` executor followed `.claude/agents/security-check.md`, inspected the diff and plugin scripts/hooks. HIGH 0 / MEDIUM 0 / LOW 0. No script/hook changes; no unpinned npx, SQL interpolation, sanitizer inconsistency, hardcoded credentials, or sensitive predictable temporary file findings. Existing test temporary directories use `mkdtempSync`. The executor's local evidence receipt is gitignored at `.omo/evidence/security-check-source-fidelity-20261028.json`; this durable summary records the result without committing local paths/hashes from that receipt.

## Iteration 2 — stop only dependent investigation

Two fresh executors read the same final text independently. The second included hold-out C.

| Executor / scenario | Success | Accuracy | Tool metadata / duration | Retries |
|---|---|---|---|---|
| final_round1 / A | ○ | 100% | 未計測 / 未計測 | 0 |
| final_round1 / B | ○ | 100% | 未計測 / 未計測 | 0 |
| final_round2 / A | ○ | 100% | 未計測 / 未計測 | 0 |
| final_round2 / B | ○ | 100% | 未計測 / 未計測 | 0 |
| final_round2 / C hold-out | ○ | 100% | 未計測 / 未計測 | 0 |

Both rejected altered extraction, preserved both survey qualifiers and denominators, and withheld inherited edition verification. C retained independently supported P, kept Q unchecked with EACCES, and did not invent a new capture. Both gave exact bounded handoffs and reported one skill-read invocation, no retries. The first reported no unclear instruction points. The second raised the possible meaning of “verified” (fact versus entire edition), then correctly resolved it by separating source support and edition checks, as the existing final-content paragraph requires. Remaining discretion concerns a non-universal confidence scale and conditional support from supplied observations; neither warrants more instructions for this change.

Size remains 145 lines. No further edit. Stop under the skill's resource-cutoff criterion: no new actionable ambiguity and 100% observed requirements on the tested scenarios including the hold-out. **Strict convergence is not claimed**: duration/tool metadata are unavailable, and the second executor still named the resolved terminology concern. The tests are constrained miniature executions using supplied observations, not live end-to-end research or proof of the upstream deterministic tooling's guarantees.

## Completion

The authorized completion sequence is a local feature commit, ordinary push to `origin/main`, then `claude plugin update omo-orchestrator@AniP-gt` for both existing user and local scopes. Actual results are recorded after execution.
