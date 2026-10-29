// Run: node --test omo-orchestrator/hooks/pasted.test.mjs
import assert from "node:assert/strict";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import { buildPlanContext, handsOverIssue, handsOverReviewComments, recordTurnStart, run, wantsChange, wantsPlan, wantsReview } from "./preflight.mjs";
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

test("a change request is sent to omo-plan first, with typo, wording, and config value changes exempt", () => {
  const output = JSON.parse(run({ hook_event_name: "UserPromptSubmit", prompt: "ログイン処理を修正して" }, noRecord))
    .hookSpecificOutput.additionalContext;
  assert.match(output, /omo-plan/);
  assert.match(output, /typo fix, a wording change, or a config value change/);
  assert.match(output, /Documentation changes are\s+not exempt/);
  assert.match(output, /omo-implement/);
  assert.match(output, /omo-review` with args `review-loop/);
  assert.match(output, /omo-ultrawork` with args `ulw-execute/);
});

test("a GitHub issue link routes to triage and then omo-plan, even without a change verb", () => {
  const prompt = "https://github.com/o/r/issues/42";
  assert.equal(handsOverIssue(prompt), true);
  const output = run({ hook_event_name: "UserPromptSubmit", prompt }, noRecord);
  assert.match(output, /omo-work-with-pr` with args `github-triage/);
  assert.match(output, /omo-plan/);
});

test("an issue link inside pasted text or a PR link does not route to the issue steps", () => {
  assert.equal(handsOverIssue(paste("see https://github.com/o/r/issues/42")), false);
  assert.equal(handsOverIssue("https://github.com/o/r/pull/12"), false);
  assert.doesNotMatch(run({ hook_event_name: "UserPromptSubmit", prompt: "https://github.com/o/r/issues/42 をレビューして" }, noRecord), /github-triage/);
});

test("route order: review thread beats an issue link, and an issue link beats a change verb", () => {
  const route = (prompt) => run({ hook_event_name: "UserPromptSubmit", prompt }, noRecord);
  assert.match(route("https://github.com/o/r/issues/42 を修正して"), /omo-work-with-pr` with args `github-triage/);
  assert.doesNotMatch(route("`https://github.com/o/r/issues/42` とは別件、ログイン処理を修正して"), /github-triage/);
  assert.match(route("`https://github.com/o/r/issues/42` とは別件、ログイン処理を修正して"), /omo-plan/);
  assert.match(route("https://github.com/o/r/pull/12#discussion_r1 と https://github.com/o/r/issues/42"), /follow-up changes to an existing PR/);
  assert.doesNotMatch(route("https://github.com/o/r/pull/12#discussion_r1 と https://github.com/o/r/issues/42"), /github-triage/);
});

test("a plan or design request routes to omo-plan with the planning agents", () => {
  for (const prompt of ["認証の設計をして", "移行の計画を立てて", "段取りを考えて", "make a plan for the retry logic", "Design the cache layer"]) {
    assert.equal(wantsPlan(prompt), true, prompt);
    const output = run({ hook_event_name: "UserPromptSubmit", prompt }, noRecord);
    assert.match(output, /omo-plan-consultant/, prompt);
    assert.match(output, /omo-planner/, prompt);
  }
});

test("plan and design inside names, paths, slash commands, or pastes do not route to planning", () => {
  for (const prompt of ["omo-plan の description を見て", "plan.md を開いて", "docs/design/x を見て", "planner は何？", "/omo-plan 認証の設計", `${paste("設計メモ")}\nこれ何？`]) {
    assert.equal(wantsPlan(prompt), false, prompt);
  }
});

test("a change request that mentions plan or design keeps the change checklist and only offers the planning agents", () => {
  for (const prompt of ["設計書の誤字を直して", "Fix the bug where free plan users cannot log in", "update the design tokens", "設計どおりに修正して"]) {
    const output = run({ hook_event_name: "UserPromptSubmit", prompt }, noRecord);
    assert.match(output, /Who is affected/, prompt);
    assert.match(output, /typo fix, a wording change/, prompt);
    assert.match(output, /If the prompt also asks for a plan or a design/, prompt);
  }
  const plain = run({ hook_event_name: "UserPromptSubmit", prompt: "バグを修正して" }, noRecord);
  assert.doesNotMatch(plain, /omo-plan-consultant/);
});

test("a plan request without a change verb gets the plan block with the typo exemption", () => {
  const output = run({ hook_event_name: "UserPromptSubmit", prompt: "認証の設計をして" }, noRecord);
  assert.doesNotMatch(output, /Who is affected/);
  assert.match(output, /typo fix, a wording change, or a config value change/);
});

test("a plan word before sentence punctuation still counts, a file extension does not", () => {
  for (const prompt of ["Please draft a plan.", "Draft the design.", "plan, then build"]) assert.equal(wantsPlan(prompt), true, prompt);
  for (const prompt of ["open plan.md", "see design.json"]) assert.equal(wantsPlan(prompt), false, prompt);
});

test("a product tier named プラン is not a plan request", () => {
  for (const prompt of ["料金プランの表示を確認して", "無料プランの上限は？"]) assert.equal(wantsPlan(prompt), false, prompt);
  assert.equal(wantsPlan("プランを立てて"), true);
});

test("route order: an issue link beats a plan request, and a review beats both", () => {
  const issue = run({ hook_event_name: "UserPromptSubmit", prompt: "https://github.com/o/r/issues/42 の設計をして" }, noRecord);
  assert.match(issue, /github-triage/);
  assert.doesNotMatch(issue, /omo-plan-consultant/);
});

test("a review request with a design word still routes to review", () => {
  assert.match(run({ hook_event_name: "UserPromptSubmit", prompt: "この設計をレビューして" }, noRecord), /single review/);
});

test("a request whose object is the plan itself gets the plan block even when a change word appears", () => {
  for (const prompt of ["Create a plan for the cache layer", "移行の計画を立てて", "write a design for the import job", "DB移行の段取りを考えて", "The import is slow. Please write a plan for the migration."]) {
    const output = run({ hook_event_name: "UserPromptSubmit", prompt }, noRecord);
    assert.match(output, /This prompt asks for a plan or a design/, prompt);
  }
  assert.match(run({ hook_event_name: "UserPromptSubmit", prompt: "make the design responsive and fix the header" }, noRecord), /Who is affected/);
  assert.match(buildPlanContext(), /also asks for the change itself/);
  const both = run({ hook_event_name: "UserPromptSubmit", prompt: "認証まわりを設計して実装して" }, noRecord);
  assert.match(both, /Who is affected/);
  assert.match(both, /If the prompt also asks for a plan or a design/);
});

test("a feature named after a plan or design is a change request, not a plan request", () => {
  for (const prompt of ["Create a design token editor", "Create a plan selector for the billing page", "設計図を書き込む処理を修正して", "Add a button to create a plan for paid users", "設計図を作成する処理を修正して"]) {
    assert.match(run({ hook_event_name: "UserPromptSubmit", prompt }, noRecord), /Who is affected/, prompt);
  }
});

test("a plan request that also carries a change verb keeps the change checks", () => {
  for (const prompt of ["Create a plan for the migration and implement it.", "Design the cache layer and implement it.", "ログインのバグを修正して。移行の計画を立てて。"]) {
    const output = run({ hook_event_name: "UserPromptSubmit", prompt }, noRecord);
    assert.match(output, /This prompt asks for a plan or a design/, prompt);
    assert.match(output, /Who is affected/, prompt);
  }
  assert.doesNotMatch(run({ hook_event_name: "UserPromptSubmit", prompt: "認証の設計をして" }, noRecord), /Who is affected/);
});

test("plan detection stays linear on long runs of newlines", () => {
  const started = Date.now();
  run({ hook_event_name: "UserPromptSubmit", prompt: `${"\n".repeat(100000)}x` }, noRecord);
  assert.ok(Date.now() - started < 500, `took ${Date.now() - started}ms`);
});
