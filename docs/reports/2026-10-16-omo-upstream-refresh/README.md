# OMO upstream refresh / 2026-10-16

## Scope and routing

- User authorized upstream pull, Claude Code adaptation, commit, push, and installed plugin update without interview.
- Upstream `origin/dev`: `e8a7bcf45` → `3ed403b60077195648f9323a06fbd25bbd00e9ca`, fast-forward pull. Root package version remains 5.1.33. Compared range: 479 files, 16,914 additions, 724 deletions.
- Lesson → home → target: machine-readable Git path identity and rename accounting → existing skill → `omo-git-master/SKILL.md`. No new hook, skill, agent, runtime, or script.
- Source: upstream `a048ab9cb`, `packages/utils/src/git-worktree/collect-git-diff-stats.ts`, `parse-status-porcelain-z.ts`, and `parse-diff-numstat-z.ts`. Upstream switches status, numstat, and untracked inventories to NUL records and distinguishes rename source/destination order.
- Adaptation: preserve path bytes, select literal arguments, inspect both rename endpoints, and keep unknown binary line counts distinct from measured zero. Binary unknown is an explicit adaptation choice; upstream UI converts binary counts to zero.
- Excluded: Senpi task/RPC lifecycle, lazy thread surfaces, telemetry, desktop capture/holds, provider/model catalogs, and browser daemon IPC fixes. They require runtimes this content plugin does not provide. No portable skill body changed in the compared range; the browser test verifies an omowright dependency update, not a Claude Code procedure.

## Evaluation protocol

Task under evaluation is generating inspection/parsing/staging command plans from the skill. Executors read the skill independently and produce plans; they do not commit, push, or mutate repositories. These results measure instruction interpretation, not execution of Git against fixture repositories. Runtime Git parsing was not tested because no parser implementation is introduced.

Fixed checklist before the edit:

- A, unusual names and rename-only commit: [critical] preserve filename bytes without line/whitespace splitting; [critical] distinguish status destination/source from numstat source/destination; use literal pathspecs and argument boundaries; inspect staged content and preserve unrelated/untracked paths.
- B, function history: [critical] no writes; use pickaxe/blame and report evidence rather than fabricated results.
- Holdout C: [critical] preserve a leading dash, glob characters, and a newline in one filename; [critical] binary `-` counts remain unknown; no writes.

Iteration 0: description/body are consistent about Git operations and mode routing. No trigger expansion required.

## Baseline

Executor produced plans satisfying A 4/4 and B 2/2 (100%, all critical items met), but filled NUL parsing, rename order, literal pathspecs, and argument boundaries from its own judgment. These are qualitative gaps despite high output accuracy. Existing-index isolation and unstaged rename discovery also required judgment; they are pre-existing workflow choices outside this parsing theme.

Tool calls: 2 reported (read plus parent update); retries: 0. Duration is unavailable from collaboration tool metadata and is not estimated. One initial dispatch was rejected for missing explicit agent type; corrected before execution.

## Change

One theme: add machine-readable path inventory guidance. Skill grows 153 → 161 lines, within the 500-line budget. The description is unchanged. Plugin manifest, marketplace, and README synchronize at 1.44.0.

## Validation

- `claude plugin validate ./omo-orchestrator`: passed.
- `claude plugin validate .`: passed with pre-existing warning that `metadata.homepage` is unknown and ignored.
- Manifest versions agree at 1.44.0; descriptions are 148 characters each, under the 200-character limit.
- `git diff --check`: passed.
- JSON LSP unavailable: biome is not installed and the user's prior installation refusal is respected. CLI manifest validation provides the relevant syntax check.
- No script, hook, credential, or permission changes; AGENTS.md security-check condition (new plugin or script changes) does not apply.

## Iteration 1

- Change: machine-readable inventory paragraph above, 153 → 161 lines / budget 500.
- A and B: executor reports byte-parser assertions passed for newline/tab names, status and numstat opposite rename ordering, destination-only accounting, binary unknowns, empty input and truncated records. Command-plan output follows the fixed checklist. No real staging or commit was performed by the executor.
- New target-theme unclear points: none. Existing-index isolation, unstaged filesystem moves, and function-body search need contextual judgment and are not new parsing requirements.
- Retries: 0 reported. Tool usage and duration are not fully exposed by collaboration metadata; no numeric comparison is claimed.

## Iteration 2 and holdout

| Scenario | Success | Accuracy | Steps | Duration | Retries |
|---|---|---|---|---|---|
| A: unusual names / rename | yes | 4/4, 100% | 1 skill read for entire run | unavailable | 0 |
| B: history | yes | 2/2, 100% | shared run | unavailable | 0 |
| C: dash, glob, newline, binary | yes | 3/3, 100% | shared run | unavailable | 0 |

Fresh executor generated byte-preserving parsing pseudocode and literal argv plans. No target-theme ambiguity was added. It noted the existing display-oriented Step 5 and general History Mode bisect option: shared NUL inventory rules apply in addition to display checks, and a read-only question does not authorize bisect. No critical failure occurred.

Qualitative parsing gaps are closed in two independent readings and the holdout score does not decline. Full quantitative convergence cannot be established because duration metadata is unavailable and the second run did not execute its parser. Stop under the skill's resource cutoff for this eight-line prompt-only change, rather than claiming measured runtime or strict quantitative convergence.

## Delivery

Commit `fc6bda4` contains the skill, synchronized versions, README, and this evidence report. User explicitly authorized push in this session, overriding the tuning skill's default no-push policy. `git push origin main` was attempted but rejected by the PreToolUse automatic approval hook: `Blocked by Claude settings port: git push is denied.` No alternate push route was used; remote delivery remains incomplete.

The local-folder marketplace still allowed `claude plugin update omo-orchestrator@AniP-gt --scope user --json` and the same command with `--scope local`. Both returned `outcome: ok`, updating 1.43.0 → 1.44.0. Claude Code requires restart to load the updated version into an existing session.
