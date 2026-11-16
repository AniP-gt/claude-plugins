# Goal File

At implementation start, the main context writes `.claude/omo/goal/<task-slug>.md` with Write/Edit. Read and continue an existing file instead of replacing its evidence. A delegated Ralph reuse continues the same file and creates no new one. Sub-agent writes are invisible to the goal gate's transcript scan.

```markdown
# Goal: <task-slug>
Status: active
Promise: <one sentence that is true when done>

## Criteria
- [ ] G1: <binary observable> — verify: `<command or surface>`
- [x] G2: <observable> — verify: `<command>` — evidence: <command and result, or file path>
```

Each criterion names a binary observable that can fail and a `verify:` command or surface that decides it. After verification, check the box and append `— evidence: <executed command and result, or file path>`. Preserve the observable and verification method. A checked box with an empty evidence field is still open. The `evidence:` label must not be preceded by a letter, digit, hyphen, or underscore. An `evidence:` label inside an inline code span, such as a verify command, does not count; a code-formatted value after a label outside code is valid. The hook checks the field's presence, not the truth of the evidence; the final independent review checks the claim.

## Status Transitions

- Start with `Status: active`.
- Set `Status: done` only after the final independent `APPROVE`.
- While waiting on a user answer or an outside blocker, set `Status: blocked` and write a one-line reason. Set it back to `active` when resumed.
- When the user stops the task, set `Status: abandoned` and write a one-line reason.

## Optional /goal Copy Line

Print one line `/goal <condition>` that restates the criteria inline, joined with `; `, and ends with `or Claude reports the goal blocked or abandoned`. Keep the entire line under 4000 characters, shortening wording while preserving every observable. Third-party articles report that Claude Code's `/goal` evaluator cannot read files and has a 4000-character limit; these claims have not been verified against the official docs. Keep the conditions inline and the line under 4000 characters as a conservative convention. The user may optionally paste this line; printing it does not activate `/goal`.

## Stop Check

The plugin's goal-gate hook scans the whole session's main-thread Write/Edit/MultiEdit paths with matching successful tool results (missing or error results do not register a goal) and reads at most 64 KiB per goal file. A goal file that is itself a symbolic link is skipped; directory symlinks still work. It enforces only `Status: active`: unchecked criteria, checked criteria without nonempty `evidence:`, or no criteria block Stop once. `stop_hook_active` passes the next stop. review-gate then checks whether edits made after the goal-gate block were reviewed, even when both gates blocked the same Stop. Only review-gate or Codex-gate feedback from a later Stop, separated from the arming goal feedback by a main-thread assistant entry, disarms this check. Edits made only through Bash after review-gate's own feedback are not re-checked after a goal-gate block, because the Git snapshot is taken per prompt and cannot order those edits against the feedback (the same limitation described under Pre-flight And Review Gate). If the re-check blocks, its later feedback makes the next flagged stop pass. Feedback records use the absolute real goal path when available, falling back to the resolved path, so changing cwd or using a symlink alias does not reset the cap. Paired meta messages and hook-blocking attachments count as one block. The default cap is five blocks per file across turns; `OMO_GOAL_GATE_MAX_BLOCKS=<n>` sets a positive cap and `OMO_GOAL_GATE=off` disables the hook. Background waits pass only for an Agent/Task or `run_in_background` Bash launched in the current turn without a completion notification. A process that never finishes, such as a dev server or watcher, therefore skips the goal check for its launch turn. Earlier-turn launches are not counted and can cause one extra block. In-flight Codex work also passes. Missing or unreadable files and other statuses pass. A resumed session is enforced again after the main context edits the goal file in that session's transcript.
