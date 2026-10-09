// Run: node --test omo-orchestrator/hooks/pasted.test.mjs
import assert from "node:assert/strict";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import { handsOverReviewComments, recordTurnStart, run, wantsChange, wantsReview } from "./preflight.mjs";
import { loadSnapshot } from "./turn-snapshot.mjs";
import { detectKeyword, stripPasted } from "./ulw-keyword.mjs";

const paste = (body) => `<pasted_content id="ae31">\n${body}\n</pasted_content id="ae31">`;
const noRecord = { env: {}, record: () => {} };

test("pasted text does not route a prompt to review, change, or ulw", () => {
  const prompt = `\n\n${paste("- サブスキル（commit/review/help）\n- ulw で修正して")}\n`;
  assert.equal(wantsReview(prompt), false);
  assert.equal(wantsChange(prompt), false);
  assert.equal(detectKeyword(prompt), null);
  assert.equal(run({ hook_event_name: "UserPromptSubmit", prompt }, noRecord), "");
});

test("the user's own words around a paste still route", () => {
  assert.equal(wantsReview(`${paste("log output")}\nこれをレビューして`), true);
  assert.equal(wantsChange(`これを修正して\n${paste("stack trace")}`), true);
  assert.notEqual(detectKeyword(`ulw ${paste("notes")}`), null);
});

test("review comments handed over in a paste route to the PR follow-up steps", () => {
  const thread = '"threadId": "PRRT_kwDOB_Rkc86qJvT0", "url": "https://github.com/o/r/pull/12#discussion_r4213500002"';
  const prompt = paste(`Inspect and fix the selected review feedback for PR #12.\n${thread}`);
  assert.equal(handsOverReviewComments(prompt), true);
  assert.equal(handsOverReviewComments("https://github.com/o/r/pull/12#discussion_r1 このコメントに返信して"), true);
  assert.equal(handsOverReviewComments("https://github.com/o/r/pull/12#pullrequestreview-9"), true);
  const output = run({ hook_event_name: "UserPromptSubmit", prompt }, noRecord);
  assert.match(output, /omo-work-with-pr/);
  assert.match(output, /reply draft/);
});

test("a PR link without a review thread does not route to the follow-up steps", () => {
  assert.equal(handsOverReviewComments("https://github.com/o/r/pull/12 をレビューして"), false);
  assert.equal(handsOverReviewComments("XPRRT_abc"), false);
  assert.match(run({ hook_event_name: "UserPromptSubmit", prompt: "https://github.com/o/r/pull/12 をレビューして" }, noRecord), /omo-review/);
});

test("an unclosed paste tag is stripped to the end", () => {
  assert.equal(stripPasted('before <pasted_content id="x">review this').trim(), "before");
});

test("a paste ends only at the closing tag with its own id", () => {
  const prompt = '<pasted_content id="a">diff: </pasted_content id="z"> please review x</pasted_content id="a">';
  assert.equal(wantsReview(prompt), false);
  assert.equal(wantsReview(`${prompt}\nこれをレビューして`), true);
});

test("a bare unclosed <pasted_content> the user typed keeps the request after it", () => {
  assert.equal(wantsChange("```\n<pasted_content>x\n```\nfix it"), true);
});

test("pathological openers are stripped in linear time", () => {
  for (const unit of ["<pasted_content ", "<pasted_content>", '<pasted_content id="a">']) {
    const started = Date.now();
    stripPasted(unit.repeat(40000));
    assert.ok(Date.now() - started < 500, `${unit} took ${Date.now() - started}ms`);
  }
});

test("several pastes are each stripped", () => {
  const out = stripPasted(`a ${paste("review")} b ${paste("fix")} c`);
  assert.doesNotMatch(out, /review|fix/);
  assert.match(out, /a .* b .* c/);
});

test("an unclosed injected-block opener inside a paste does not swallow the request after it", () => {
  const prompt = `${paste("<system-reminder>\nnotes\n<task-notification>")}\nこれをレビューして`;
  assert.equal(wantsReview(prompt), true);
  assert.notEqual(detectKeyword(`${prompt}\nulw fix this`), null);
});

test("a paste-only prompt still starts a turn snapshot", () => {
  const dir = mkdtempSync(join(tmpdir(), "omo-pasted-"));
  const sessionId = "pasted-only";
  try {
    const env = { OMO_SNAPSHOT_DIR: dir };
    recordTurnStart({ session_id: sessionId, cwd: process.cwd(), prompt: paste("log output") }, env);
    assert.notEqual(loadSnapshot(sessionId, env), null);
    const empty = "empty-session";
    recordTurnStart({ session_id: empty, cwd: process.cwd(), prompt: "<task-notification>done</task-notification>" }, env);
    assert.equal(loadSnapshot(empty, env), null);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});
