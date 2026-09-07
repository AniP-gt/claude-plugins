---
name: omo-git-master
description: Git workflow for atomic commits, rebase and squash, and history archaeology (pickaxe, blame, bisect). Detects commit style and language from existing history instead of assuming a convention.
argument-hint: [commit message, rebase target, or history question]
allowed-tools: Read, Grep, Glob, Bash, TodoWrite
user-invocable: true
---

# OMO Git Master

Use this skill for git work: creating commits, rewriting local history, or finding when and where a change entered the codebase.

## Mode Detection

Parse the actual request. Do not default to commit mode.

| Request | Mode |
|---|---|
| commit, there are changes to commit | Commit |
| rebase, squash, clean up history, apply fixups, reorder | Rebase |
| when was X added, who wrote this, find the commit that, bisect | History |

## Shared Rules

- Read state before changing it. Gather status, diff, log, branch, and upstream in parallel before deciding anything.
- Never rewrite history that has been pushed without explicit user permission.
- Never use `--force`. Use `--force-with-lease`.
- Never rebase or rewrite `main` or `master`.
- Never run destructive `reset --hard`, `checkout --`, or `clean` against work you did not record first. Preserve pre-existing uncommitted changes that are not part of this task.
- Do not push, force-push, or create a pull request unless the user asked. Report the command and let them run it.
- Report what you actually did. If a step failed or was skipped, say so with the output.

---

## Commit Mode

### Step 1: Gather context

Collect in parallel: `git status`, staged and unstaged diffstat, recent log (subjects included), current branch, merge-base against the default branch, and upstream tracking state.

### Step 2: Detect style from history, then state it

Never assume Conventional Commits. Derive both axes from the recent log:

- Language: whichever the majority of recent subjects use.
- Shape: `type: message` prefixes mean semantic; plain descriptive subjects mean plain; one-to-three-word subjects such as `lint` or `format` mean short. Use the majority, not semantic by default.

Before committing, state the detected language, the detected shape, and two or three real subjects from the log that justify the call. If the log is empty or too mixed to read, say so and ask rather than guessing.

### Step 3: Plan atomic units

Default to multiple commits. A single commit spanning unrelated files is the failure mode this skill exists to prevent.

Split when files differ by directory or module, by concern (interface, logic, config, test, docs), or by whether they can be reverted independently.

Combine only when the parts form one atomic unit that would not build or make sense apart, such as a function and the test that covers it. Never separate a test from the implementation it covers, and never group by file type across features.

Order commits so dependencies land before the code that uses them.

State the plan before executing: the groups, the file in each, a one-sentence justification per group, and the order. If you cannot justify a grouping in one sentence, it is not one group.

### Step 4: Choose fixup or new commit

Use a fixup when the change completes or corrects the intent of an existing local commit and that commit is safe to rewrite. Use a new commit for a new capability, an independent unit, or when no suitable target exists.

Rewrite safety by branch state:

| State | Allowed |
|---|---|
| On `main` or `master` | New commits only. Never rewrite. |
| No upstream, or all commits local | Fixup, autosquash, and reset are safe |
| Pushed but not merged | Fixup allowed, but warn that force-with-lease will be required and confirm first |

A full `reset --soft` to the merge-base to rebuild history is acceptable only when every commit involved is local and the user allows it or the branch is clearly work in progress. It discards commit boundaries, so confirm before using it.

### Step 5: Execute

Stage each group explicitly by path. Verify what is staged before committing, so unrelated working-tree changes do not ride along. Commit with a message matching the detected language and shape. Apply fixups with a single `--autosquash` rebase at the end rather than one rebase per fixup.

Validate each message against the detected style before committing. If it does not match, rewrite it.

### Step 6: Verify

Confirm the working tree is in the expected state, review the resulting log against the merge-base, and check that each commit stands alone and could be reverted independently. Report the commits created, any fixups merged, whether a force-with-lease push would be needed, and the exact push command for the user to run.

---

## Rebase Mode

### Step 1: Assess safety before touching anything

| Condition | Action |
|---|---|
| On `main` or `master` | Abort. Do not rebase. |
| Dirty working tree | Stash with a named message first, and restore it afterward |
| Commits already pushed | Force-with-lease will be required. Confirm with the user first. |
| All commits local | Proceed |
| Upstream diverged | Consider `--onto`; explain the plan before running it |

Record the starting commit so the pre-rebase state can be recovered.

### Step 2: Pick the strategy

Squash or clean up means combining local commits. Rebase onto the base means updating the branch against its upstream. Autosquash means applying existing `fixup!` or `squash!` commits. Reorder or split means restructuring the sequence.

Interactive rebase cannot be driven by hand here, so automate the todo list: `GIT_SEQUENCE_EDITOR=: git rebase -i --autosquash <merge-base>` accepts the generated plan for autosquash. Use that auto-accept only for autosquash, where the generated todo just reorders `fixup!` and `squash!` commits onto their targets. Never pair it with a reorder, drop, or reword plan, which would apply an unreviewed rewrite. For a full squash, `reset --soft` to the merge-base and recommit is simpler and more predictable than scripting a rebase todo.

### Step 3: Resolve conflicts deliberately

Identify the conflicting files, read both sides, resolve by editing, remove every conflict marker, then stage and continue. Verify no markers survive before continuing. When the resolution is unclear, `git rebase --abort` is the safe exit; do not guess at semantics you cannot verify.

Recovery: `--abort` returns to the pre-rebase state mid-rebase; `git reflog` finds the original commits afterward; `git fsck --lost-found` is the last resort.

### Step 4: Verify and report

Check the tree is clean, review the new log, and confirm the content still matches expectations by diffing against the recorded pre-rebase commit. Run the project's tests if they exist. Report commits before and after, conflicts resolved, and the exact push command, noting force-with-lease when the branch was already pushed.

---

## History Mode

### Step 1: Match the tool to the question

| Question | Tool |
|---|---|
| When was this string added or removed | `git log -S` (pickaxe) |
| Which commits changed lines matching a pattern | `git log -G` (regex) |
| Who last changed this line | `git blame -L` |
| Which commit introduced this bug | `git bisect` |
| How did this file evolve | `git log --follow -- path` |
| Where did this deleted code go | `git log -S --all`, or `--all --full-history` for files |

`-S` counts occurrences and finds where a string appeared or vanished. `-G` matches the diff text itself. Choosing the wrong one silently returns misleading results.

### Step 2: Search precisely

Scope by path, revision range, or `--all` when the code may live on another branch or be deleted. Use `blame -C -w` when code may have moved or been reformatted, otherwise attribution lands on the wrong commit. For bisect, establish genuinely good and bad boundaries first; a wrong boundary invalidates the whole search. Automate with `git bisect run` when a command can decide, and always `git bisect reset` when finished. If bisect aborts or the run command fails partway, run `git bisect reset` anyway before doing anything else; leaving the session open strands the repository on a detached HEAD.

### Step 3: Report with evidence

Give the command used, the commits found with hash, date, and subject, and the most relevant commit with its author and the diff excerpt that answers the question. Anchor claims to real hashes and paths; never infer a commit that the search did not return. If the search found nothing, say so and state what was searched rather than offering a plausible guess.

Offer concrete follow-ups where useful, such as viewing, reverting, or cherry-picking the commit.

---

## Report Contract

State the mode, what changed in the repository, the detected style if commits were made, what was verified, and any command left for the user to run. Never claim a commit, rebase, or push happened if it did not.
