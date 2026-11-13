// Run: node --test omo-orchestrator/hooks/non-interactive-env.test.mjs
import assert from "node:assert/strict";
import { test } from "node:test";
import { run } from "./non-interactive-env.mjs";

const input = (command) => ({ hook_event_name: "PreToolUse", tool_name: "Bash", tool_input: { command } });

test("direct interactive commands receive non-blocking guidance", () => {
  for (const command of ["vim file.txt", "less README.md", "git add -p", "git rebase -i HEAD~2", "git commit", "git --no-pager commit", "git rebase --continue"]) {
    const response = run(input(command));
    assert.notEqual(response, "", command);
    const output = JSON.parse(response);
    assert.equal(output.hookSpecificOutput.hookEventName, "PreToolUse", command);
    assert.ok(output.hookSpecificOutput.additionalContext, command);
    assert.equal(output.hookSpecificOutput.permissionDecision, undefined, command);
    assert.equal(output.hookSpecificOutput.updatedInput, undefined, command);
  }
});

test("unrelated, explicit noninteractive, help, and quoted examples remain silent", () => {
  for (const command of ["echo 'git add -p'", "git status", "git add file", "git commit -m 'hello world'", "git commit -F msg.txt", "git commit --no-edit", "git rebase -i --help", "vim --help", "cat README.md", "echo hi && vim file", "git rebase --abort"]) {
    assert.equal(run(input(command)), "", command);
  }
});

test("wrong events, other tools, and malformed input remain silent", () => {
  for (const value of [null, {}, { ...input("vim file"), hook_event_name: "PostToolUse" }, { ...input("vim file"), tool_name: "Read" }, input(null)]) {
    assert.equal(run(value), "");
  }
});
