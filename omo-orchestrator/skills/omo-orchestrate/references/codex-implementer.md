# Codex Implementer

The Codex implementer lane hands an implementation or fix pass to a Codex CLI TUI running in a separate Orca terminal tab. Claude stays the owner of design, research, review, verification, real-surface QA, and commits. Codex only implements and applies fixes, and its report is a claim that Claude checks, never evidence.

The implementing session never reviews its own work. Review stays with the Claude lanes plus `omo-review` `references/codex-lane.md` (a fresh `codex exec --sandbox read-only` on the diff). Neither the TUI session nor this lane satisfies that review lane.

## When it applies

The lane applies when the trigger holds: an approved `omo-plan` exists for the change, or `omo-ultrawork` runs (any mode). A `LIGHT` change that skipped `omo-plan` outside `omo-ultrawork` (typo, wording, config value) does not meet the trigger. The lane simply does not apply, `omo-implementer` or Claude does the work, and nothing is recorded.

When the trigger holds but the lane did not run, use `omo-implementer` and record `codex-impl: FALLBACK - <reason>`. The reasons are: Claude Code is not inside Orca, a preflight failure, or a launch failure.

Three scopes always stay with `omo-implementer`, with no status line: a prose-only wiki or docs writer lane (not planned product implementation), a verification-only scope (verification is Claude's job), and git or commit tasks (Codex never commits).

One Codex session serves one worktree at a time. Waves of one plan are sent to the same session in order; never open parallel Codex tabs in one worktree.

## Running it

`<slug>` is the plan or task slug restricted to one or more characters of `[a-z0-9-]`, never empty, because it enters a shell command and file paths (an empty slug would make `rm -r .claude/omo/codex/` delete every slug and the marker). Never put user or Codex text in a shell argument: anything but a fixed pointer goes into a file written with the Write tool. `<round>` is one running number per slug: round 1 is the first task (the initial implementation), and each later task of the same plan or fix pass is the next round (the first one after round 1 is round 2). Every file and message of a pass uses its round: `result-<round>.md`, plus `task-<round>.md` for a later task or `fix-<round>.md` for a fix pass.

1. Preflight, as separate commands. Every command of this lane runs from the repository root (`cd "$(git rev-parse --show-toplevel)"`), because the marker, the brief, and the snapshots use relative `.claude/omo/...` paths and the review-gate hook looks for the marker at the git root. Resolve the Orca executable as the `orca-cli` skill says (`ORCA_CLI_COMMAND`, else `orca`).
   - `orca worktree current --json` must report `"ok": true`.
   - `codex --version` must succeed. Use it alone, never `command -v codex`: the review-gate Stop hook counts that probe as the review lane.
   - `jq --version` must succeed: the screen read in step 6 needs `jq`.

   Any failure is a fallback with its error as the reason. A `runtime_access_denied` or EPERM error means the Claude sandbox blocked the Orca socket, not that Orca is absent: rerun that `orca` command outside the sandbox through the permission prompt. Do not run `orca open` or restart Orca.
2. Marker. When `.claude/omo/codex/IN_FLIGHT` already exists, show its content and mtime (`cat`, `ls -l`). It is stale when the recorded terminal is not alive (its `handle:` line is `pending` or missing, `orca terminal read --terminal <handle> --json` fails, or its `status` is not `running`) or when it is older than 24 hours. For a stale marker, ask the user whether to remove it and remove it on yes. A live (not stale) marker means another delegation is running in this worktree: that is BLOCKED, not a fallback. Tell the user and wait for their decision. When the user declines to remove a stale marker, that is BLOCKED too: ask how to proceed. When no marker exists, write it as three lines, `slug: <slug>`, `title: codex:<slug>`, and `handle: pending`, and rewrite the last line as `handle: <handle>` once step 5 returns the handle. Whenever a later round recreates the marker, it follows this step: an existing marker is overwritten only when its `slug:` and `handle:` are this run's, and another delegation's marker is BLOCKED, so tell the user. Remove the marker this run wrote (never another delegation's live marker) on DONE, BLOCKED, the post-run stop, or fallback. While it exists and is younger than 24 hours, the review-gate Stop hook does not demand a review, so ending the turn during a wait or a question relay does not trigger it on half-done work.
3. Brief. Write `.claude/omo/codex/<slug>/brief.md` with the same content as an `omo-implementer` brief: goal, files in scope, the existing pattern as file:line, tests to read first, the test-first rule, a binary Done when, the approved real-surface QA design, the verification commands, and the project rules that apply to the files in scope (chosen per `project-rules.md`, Codex lane paragraph: the `CLAUDE.md` and `.claude/rules/` rules Codex does not load). In the lane Codex writes the tests the brief requires (test-first), and Claude reruns them and the QA afterwards; Claude never edits during the run. It also carries these mandatory rules:
   - Do not commit, push, amend, rebase, or otherwise rewrite git history.
   - Do not run `claude`, `codex`, or any other agent CLI.
   - Do not read or print `.env*`, key and certificate files (`*.pem`, `*.key`, `id_*`), or credential files: everything Codex reads is sent to OpenAI.
   - Do not edit `docs/reviews/` or `.claude/omo/`, except your own result file.
   - Edit only the listed files.
   - When finished, blocked, or in need of an answer, write the result file named in the prompt (`result-<round>.md`, below) and stop.

   The brief is sent to OpenAI. Remove secrets as `codex-consult.md` step 3 says: leave out the content of `.env*`, key and certificate files, and credential files, and replace token, password, and connection-string values with `<redacted>`.
4. Before-state. Take the snapshot below with `<name>` = `before`, from the repository root.
5. Launch (round 1; `rm -f .claude/omo/codex/<slug>/result-1.md` first):

   ```bash
   orca terminal create --worktree active --title codex:<slug> \
     --command "codex --dangerously-bypass-hook-trust -s workspace-write -a never 'Read .claude/omo/codex/<slug>/brief.md and follow it. Round 1: write .claude/omo/codex/<slug>/result-1.md when done.'" --json
   ```

   `-s workspace-write` limits writes to the worktree and `-a never` removes approval prompts, so the TUI never stalls on a prompt nobody answers. `--dangerously-bypass-hook-trust` (approved by the user) skips the hook-trust prompt for the same reason. `orca agent launch --agent codex` is not used because it has no way to pass `-s` or `-a`. Record the returned terminal handle in the controller ledger and in the marker. A create failure removes the marker and falls back. After the create, Claude does not edit the working tree until the run ends.
6. Wait. Run this with the Bash tool's `run_in_background: true`, so Claude is notified when it returns:

   ```bash
   orca terminal wait --terminal <handle> --for tui-idle --timeout-ms 600000 --json
   ```

   On timeout, start the same wait again, `touch` `.claude/omo/codex/IN_FLIGHT` each time so a run longer than 24 hours keeps the review gate quiet, and record each wait in the ledger. After 3 consecutive timeouts without an idle, read the screen and ask the user whether to keep waiting, send a nudge, or stop, and record the answer in the ledger. On stop, end the run as "Ending a run without DONE" says. On `satisfied: true`, read `.claude/omo/codex/<slug>/result-<round>.md` and run `orca terminal read --terminal <handle> --screen --json | jq -r '.result.terminal.status, ((.result.terminal.tail // [])[-19:][] | tostring)'` (the full JSON is about 50 lines of metadata and `grep` on it also matches metadata keys; the first output line is the `status`, then come the last screen rows, where you look for the Codex UI markers below). Do not wait `--for exit`: `--command` is typed into a shell, so when Codex exits the terminal stays alive at the shell prompt. A screen read that shows a shell prompt instead of the Codex UI, or a read `status` other than `running`, means Codex ended: treat it as BLOCKED.
7. Read the first line of the result file and act on it (next section).

### Snapshot

The Codex scratch directory `.claude/omo/codex/` is kept out of Git from 3.9.0 through the `omo-dir-ignore` hook's managed block in the Git-resolved `info/exclude` file, and Claude writes the ledger and evidence under `.claude/omo/` during a run. Review reports that Claude-side review skills write to `docs/reviews/` during a run are also not Codex edits. Every snapshot therefore excludes the whole `.claude/omo` bookkeeping tree (the review-gate hook ignores it too) and `docs/reviews` with the same pathspec, so neither Codex's result file nor Claude's own notes and review reports count as a change. These two trees are therefore not covered by the post-run check; the brief rule that Codex must not edit them is what covers them. Run this as one command from the repository root with `<name>` = `before` or `after`; it records the porcelain status, HEAD, the index entries (mode, object, and stage of tracked paths), the raw diff against HEAD (modes of the working tree files), and one content hash per changed or untracked file (a status line shows only path and state, so a further edit to an already-dirty file shows only in its hash line):

```bash
S=.claude/omo/codex/<slug>
git status --porcelain=v1 -uall -- . ':!.claude/omo' ':!docs/reviews' > "$S/<name>.status"
git rev-parse HEAD > "$S/<name>.head"
git ls-files -s -- . ':!.claude/omo' ':!docs/reviews' > "$S/<name>.index"
git diff --raw HEAD -- . ':!.claude/omo' ':!docs/reviews' > "$S/<name>.raw"
{ git diff --name-only -z HEAD -- . ':!.claude/omo' ':!docs/reviews' | xargs -0 shasum --
  git ls-files --others --exclude-standard -z -- . ':!.claude/omo' ':!docs/reviews' | xargs -0 shasum --; } 2>/dev/null | sort -k2 > "$S/<name>.hash"
```

The hash covers file content only. The index snapshot covers tracked paths, so a staged-only change and a mode change of a tracked file in the index show in the index diff, and the raw diff shows a working-tree-only mode change of an already-dirty tracked file. What stays uncovered is a mode or symlink-target change of an untracked file, and any change to a file ignored by Git.

## Result contract

`result-<round>.md` starts with `STATUS: DONE | BLOCKED | QUESTION` on the first line, always in English. The rest may be in the user's language. Then:

- the changed files;
- the commands Codex ran, each with its exit code;
- for QUESTION, the question text;
- for BLOCKED, the failing command and its error.

## Before every send

Before every `orca terminal send` (answer pointer, missing-result reminder, fix round), run the screen read of step 6 and confirm the Codex UI is showing. The Codex UI shows `Ask Codex to do anything` (the input prompt) or `Worked for` after a turn. Send only when the read shows `status` `running` and a Codex-UI marker; when either is missing, treat the run as BLOCKED and relaunch per Fix rounds instead of sending, because text sent to a bare shell would run as a command.

## Undefined cases

- Idle with no result file: read the screen. A visible question is a QUESTION. Otherwise send one reminder, wait once more, then BLOCKED if the file is still missing:

  ```bash
  orca terminal send --terminal <handle> --text "Write .claude/omo/codex/<slug>/result-<round>.md now." --enter --wait-submit 15 --json
  ```
- Tab closed, or Codex exited or crashed (a shell prompt on the screen read, a `status` other than `running`, or the read fails): BLOCKED. Show the tail of the screen read and offer a relaunch (see Fix rounds, with the current round number) or a fallback.
- Codex blocked by its own sandbox (network, Docker): BLOCKED with the command. Claude runs that verification itself.
- The user edits in the Codex tab directly: allowed. The post-run check below still runs.

## Question relay

On `STATUS: QUESTION`, record the question in the ledger and delete `.claude/omo/codex/<slug>/result-<round>.md` (`rm -f` on that exact path), so a stale QUESTION is never reread, whoever answers. Claude then asks the user in chat (`AskUserQuestion` when available), quoting Codex's question. Then write the answer with the Write tool to `.claude/omo/codex/<slug>/answer-<round>.md`: the answer is user text, and inside a shell argument backticks and `$()` would expand. After the send guard above passes and only after a `satisfied: true` idle, send a fixed pointer:

```bash
orca terminal send --terminal <handle> --text 'Read .claude/omo/codex/<slug>/answer-<round>.md, then create .claude/omo/codex/<slug>/result-<round>.md again.' --enter --wait-submit 15 --json
```

and wait again (step 6), still in the same round. When the send reports `accepted: true` without an observed submission, tell the user to check the tab instead of resending. The user may also answer in the Codex tab directly: Claude then just waits for the next idle and re-reads the result file. Ending the Claude turn while waiting for the user is fine, because the marker keeps the review gate quiet.

## Post-run check

On DONE or BLOCKED, take the snapshot with `<name>` = `after`, then compare it with the `before` files (`S=.claude/omo/codex/<slug>`): `diff "$S/before.head" "$S/after.head"`, `diff "$S/before.status" "$S/after.status"`, `diff "$S/before.index" "$S/after.index"`, `diff "$S/before.raw" "$S/after.raw"`, and `diff "$S/before.hash" "$S/after.hash"`. The paths edited during the run are the union of the paths in the status, index, raw, and hash diffs: the status diff shows a path that was clean before and was added, deleted, or modified, the index diff shows a staged-only change or an index mode change of a tracked path, the raw diff shows a working-tree mode change of a tracked path, and the hash diff shows a path whose content changed, including one that was already dirty before the run.

- HEAD changed (Codex committed), or an edited path lies outside the brief's scope, on DONE or BLOCKED alike: stop. End the run as "Ending a run without DONE" says, do not revert or keep the changes yourself, and report the paths to the user.
- On DONE otherwise, remove the marker. Claude then reruns the diagnostics, the tests, and the approved real-surface QA itself, with the tool chosen by `omo-implement` `references/real-surface-qa.md`. The result file's commands are not evidence.

On BLOCKED without a stop case, end the run as below, include the comparison in the report, and hand the blocker to the controller (`omo-ralph-loop` rules for retries and stuck states).

### Ending a run without DONE

On BLOCKED, on "stop waiting", and on the stop branch above: when the tab is still `running`, run `orca terminal close --terminal <handle> --json` first, then remove the marker this run wrote. Relaunch for a retry only after that. Once the user has decided how to proceed, the run also does the Cleanup steps (close the tab if still open, copy the result files, remove the scratch directory); a FALLBACK does the same for any scratch files it created.

## Next task of the same plan

One Codex session serves one plan. The next task of the plan is the next round on the same handle, with `<slug>` the plan's slug. Write `.claude/omo/codex/<slug>/task-<round>.md` with the same fields as the brief (goal, files in scope, the existing pattern as file:line, tests to read first, the test-first rule, a binary Done when, the approved real-surface QA design, the verification commands, the project rules that apply to the files in scope, chosen as for the brief) and name `brief.md` for the mandatory rules instead of repeating them. Run `rm -f .claude/omo/codex/<slug>/result-<round>.md`, recreate the marker as step 2 says (with the handle), and retake the `before` snapshot. After the send guard above passes, send:

```bash
orca terminal send --terminal <handle> --text 'Read .claude/omo/codex/<slug>/task-<round>.md and follow it. Write .claude/omo/codex/<slug>/result-<round>.md when done.' --enter --wait-submit 15 --json
```

Wait, run the post-run check, and verify as for any round.

## Fix rounds

Review findings (the synthesis directives) go to the same handle as the next round. Write `.claude/omo/codex/<slug>/fix-<round>.md` with the directives and the scope, run `rm -f .claude/omo/codex/<slug>/result-<round>.md`, recreate the marker as step 2 says (with the handle) and retake the `before` snapshot, then, after the send guard above passes, send:

```bash
orca terminal send --terminal <handle> --text "Read .claude/omo/codex/<slug>/fix-<round>.md and apply it. Round <round>: write .claude/omo/codex/<slug>/result-<round>.md when done." --enter --wait-submit 15 --json
```

Wait and check as above. Delete the round's result file before every launch or send except the missing-result reminder. When the terminal is gone, relaunch in the order of round 1: the step 2 marker check and write (`handle: pending`), the step 4 `before` snapshot, then the step 5 launch with the brief plus the current round's file, and finally the new handle written into the marker's `handle:` line. Never launch before the marker and the `before` snapshot exist. The file is `task-<round>.md`, `fix-<round>.md`, or for round 1 only the brief (never a nonexistent `fix-1.md`). The pointer prompt for rounds above 1 is `Read .claude/omo/codex/<slug>/brief.md and follow it, then read .claude/omo/codex/<slug>/<file> and follow it. Round <round>: write .claude/omo/codex/<slug>/result-<round>.md when done.` with `<file>` that round's file (the current round number, not 1). Record the new handle in the ledger. The iteration budget and the stuck rules stay with `omo-ralph-loop`.

## Hooks and commits

Hooks stay Claude-side; nothing is added to `~/.codex`. Codex never commits, pushes, or rewrites history. Claude commits after verification and the final gate.

## Cleanup

After the controller's final gate returns `APPROVE`, copy the result files into the directory that holds the controller's handoff ledger (for example `.claude/omo/handoffs/<task-slug>-codex/`), delete the scratch directory, and close the tab (use `rm -r`: an environment hook denies `rm -rf`):

```bash
rm -r .claude/omo/codex/<slug>
orca terminal close --terminal <handle> --json
```

A run that ends BLOCKED or FALLBACK does the same steps once the user has decided how to proceed.

## Status line

Report `codex-impl: DONE (<handle>, round <round>) | BLOCKED - <reason> | FALLBACK - <reason>` in the final report and the ledger. A fallback is not a failure of the task: continue with `omo-implementer` and give the reason.
