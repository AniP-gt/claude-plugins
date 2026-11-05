# OMO exhaustive research refresh — 2026-11-05

## Scope and routing

The user authorized autonomous upstream pull, adoption, commit, push, and plugin update for this session. Both repositories started clean. Upstream `dev` remained at `cb7f76ecf6b533a544fe54c506c03387fdec275b` after `git pull --ff-only`; the earlier refresh already inspected this revision. Target `main` started at `edee1c7`, equal to `origin/main`.

Lesson → home → target: explicit exhaustive research must not silently stop at implementation context-gathering defaults → existing skill procedure → `omo-orchestrator/skills/omo-research/modes/ultraresearch/MODE.md`. No hook, new skill, or new agent is introduced. Session-only push authorization overrides the tuning skill's default no-push instruction.

## Adoption and exclusions

Adapt the authority distinction in upstream `packages/shared-skills/skills/ulw-research/SKILL.md:42–46`. The old mode's default maximum of three source lanes and two lead expansions could leave material evidence unexamined despite an explicit exhaustive request. Remove that total default cap; cover applicable lanes and material leads, bounding each worker or expansion by its evidence target and exit condition. A lane's return is not completion of its newly discovered leads.

Explicit user/caller limits remain binding, as do scope, read-only access, untrusted-source handling, host tools, and concurrency limits. Budget exhaustion or inaccessible material evidence produces qualified partial coverage. No runtime scheduler, unlimited recursion, source-provided authority, renderer, or automatic continuation is adopted. Upstream's blanket override of surrounding rules is deliberately narrowed to exploration defaults. A testing-policy candidate was deferred to keep this iteration focused.

## Iteration 0 and fixed criteria

Description/body consistency: the parent advertises exhaustive/saturation research and the mode activates only on explicit requests. The old default cap undermined that coverage promise. Baseline and revised evaluators read the parent and mode, then made tabletop decisions without executing research or modifying files.

Each scenario has three fixed criteria: (1) critical decision below, (2) preserve read-only/no invented APIs or automatic recovery, (3) name the evidence gap and next bounded action or stopping reason.

- A: explicit exhaustive request, no budget; three lanes and two expansions completed; fourth available lane and third lead could change P1. Critical: continue material investigation.
- B: same research with explicit user limit of two expansions, spent. Critical: stop at the limit and report remaining material evidence.
- C: ordinary implementation context gathering, no exhaustive request; two searches add no information and caller/test evidence is sufficient. Critical: stop repetitive search without activating the mode.
- Holdout D, fixed before round 2: all initial lanes returned, but a material lead requires an unavailable authenticated source; independent accessible P2 verification remains. Critical: do not infer the lead is resolved or claim exhaustive success; mark partial. Preserve access/write boundaries, finish independent checks, and identify the blocked next check.

## Baseline

Fresh executor: A failed, 2/3 (66.7%); B and C passed, 3/3 (100%). A stopped at the default cap. New unclear points: conflict between applicable lane coverage and the three-lane maximum; no distinction between exhaustive research and implementation exploration limits. C's exact stopping point was a justified discretion gap, since evidence sufficiency rather than a fixed two-search rule governs the parent.

## Iteration 1

The change targets critical A while preserving critical B/C. Added Exploration Scope, replaced the default cap, and clarified material-lead closure and partial coverage. Added a contents list for this reference exceeding 100 lines and corrected its upstream path. Mode: 139 → 157 lines; parent: 50 lines; both below 500. Release metadata and README advance together to 3.11.0; descriptions stay unchanged at 148 characters.

Fresh executor: A/B/C passed, 3/3 each (100%). New unclear points: none. Discretion gaps: actual worker assignment and local evidence targets depend on the lead; C stops on adequate evidence rather than a fixed count. Retries: 0. Read tool calls: 1. Agent total duration unavailable; command runtime is not substituted.

## Iteration 2 and holdout

No instruction changes. A second fresh executor passed A/B/C/D at 3/3 each (100%). No new unclear points; retries 0; read tool calls 1. Holdout D retained the blocked material claim as UNKNOWN, completed accessible independent work, and requested source verification through an existing authorized owner without gathering credentials or writing files. Exact source/claim IDs were absent from the scenario and were not invented.

Two consecutive rounds have no new ambiguity and unchanged accuracy/tool count; holdout accuracy did not drop. Stop at resource cutoff: total duration metadata is unavailable, so strict quantitative convergence including the ±15% duration criterion is not claimed. These are prompt-execution tabletop results, not measured end-to-end research quality or runtime performance.

## Validation and release

Plugin manifest and marketplace validation passed. Existing directory-submission diagnostics remain: missing license and icon; marketplace warning: ignored `metadata.homepage`. `git diff --check` passed. No scripts changed, so no script regression tests or tests pinning prose were added.

Independent `security-check` followed `.claude/agents/security-check.md` across all five categories: HIGH 0, MEDIUM 0, LOW 0.

Commit plan: one atomic adoption consisting of the mode, synchronized manifests, README release note, and this evaluation record. Recent history uses Japanese semantic subjects, e.g. `edee1c7 fix(omo-orchestrator): Codex を hook trust の確認なしで実行する (3.10.1)` and `15eef36 feat(omo-orchestrator): 中断後に子タスクの実状態と所有者を照合する (3.10.0)`.
