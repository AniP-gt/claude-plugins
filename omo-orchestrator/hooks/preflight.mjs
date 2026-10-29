#!/usr/bin/env node
// UserPromptSubmit hook: when a prompt asks for a code change, inject a short pre-flight checklist so that
// affected users, undefined cases, and existing callers are looked at before the first edit, even when the
// user did not ask for it. When it asks for a review, route it to omo-review, the single review entry, which
// a model does not pick on its own for a plain "review this" request. When it hands over review comments
// on an existing PR, ask for the follow-up steps (review, reply drafts, PR body) that a fix there skips.
// Change requests and GitHub issue links are sent to omo-plan before the first edit. A prompt that asks for
// a plan or a design is sent to omo-plan with the consultant and planner agents, which a model skips on its own.
// ulw prompts are left to ulw-keyword.mjs, which loads a fuller workflow.
// Every prompt also records a git snapshot that review-gate.mjs compares against when Claude stops.
import { fileURLToPath } from "node:url";
import { saveSnapshot, takeSnapshot } from "./turn-snapshot.mjs";
import { detectKeyword, stripInjected, userText } from "./ulw-keyword.mjs";

const MARKER = "<omo-preflight>";
const IMPACT_SCRIPT = fileURLToPath(new URL("../scripts/impact.mjs", import.meta.url));
const B = "(?<![A-Za-z0-9_])";
const E = "(?![A-Za-z0-9_])";
const CHANGE_PATTERNS = [
  /実装|追加して|修正|直して|直す|変更して|変えて|書き換え|リファクタ|作って|作成して|対応して|移行|削除して|置き換え|改修|組み込/,
  new RegExp(
    `${B}(?:implement|add|fix|refactor|change|update|modify|rewrite|migrate|remove|delete|build|create|rename|support)${E}`,
    "i",
  ),
];

// "plan" and "design" also appear in names such as omo-plan or plan.md, so a hyphen, slash, or a dot that starts an
// extension next to the word does not count; a sentence-ending dot does.
const PLAN_PATTERNS = [
  // Bare プラン is left out: 料金プラン and 無料プラン name a product tier, not a request for a plan.
  /計画|設計|段取り|プラン(?:を|は)?(?:立て|作成|考え|練)/,
  /(?<![A-Za-z0-9_./-])(?:plan|design)(?![A-Za-z0-9_/-]|\.[A-Za-z0-9_])/i,
];

// A request whose object is the plan itself. It wins over the change verbs, which also fire on such prompts
// (移行, create), so planning is not mistaken for a change request. Only the main clause counts: in Japanese the
// request ends the sentence (移行の計画を立てて), in English it starts one (Create a plan for ...). A clause that
// only describes the change (設計図を作成する処理を修正して, Add a button to create a plan) stays a change request.
const PLAN_REQUEST_PATTERNS = [
  /(?:計画|設計|段取り|プラン)(?:案|図)?(?:を|は|だけ|も)?(?:立てて|作って|作成して|考えて|練って|書いて|して)(?:ください|ほしい|欲しい|もらえる|くれる)?[？?。.!！\s]*$/m,
  /(?:^|[.!?]\s+)(?:please\s+)?(?:create|make|write|draft|prepare|propose|come up with)\s+(?:(?:me|us)\s+)?(?:a|an)\s+(?:[A-Za-z-]+\s+){0,2}?(?:plan|design)(?=\s*$|\s*[.,;:!?]|\s+(?:for|of|to|that|on|about|with|so)\b)/im,
  /^[ \t]*(?:plan|design)\s+(?:the|a|an|our|my)\s/im,
];

const REVIEW_PATTERNS = [/レビュー|監査|指摘だけ|指摘して/, new RegExp(`${B}(?:review|audit)${E}`, "i")];
// The user picked a specific reviewer or command; leave that choice alone.
const NAMED_REVIEWER_PATTERN = /review-pr|code-review|self-review|omo-review|security-review/i;

// A link to a PR review thread or a review thread id. Unlike the request patterns, this is checked in
// pasted text too: review tools hand over the comments to address as a paste.
const REVIEW_THREAD_PATTERN = /\/pull\/\d+#(?:discussion_r|pullrequestreview-)\d+|(?<![A-Za-z0-9_])PRRT_[A-Za-z0-9_-]+/;

export function handsOverReviewComments(prompt) {
  return REVIEW_THREAD_PATTERN.test(stripInjected(prompt));
}

export function wantsReview(prompt) {
  const text = userText(prompt);
  if (text.trimStart().startsWith("/") || NAMED_REVIEWER_PATTERN.test(text)) return false;
  return REVIEW_PATTERNS.some((pattern) => pattern.test(text));
}

// A GitHub issue link the user typed. Pasted text is ignored like the request patterns: a log or a
// document that mentions an issue is not a request to work on it.
const ISSUE_URL_PATTERN = /github\.com\/[^/\s]+\/[^/\s]+\/issues\/\d+/;

export function handsOverIssue(prompt) {
  return ISSUE_URL_PATTERN.test(userText(prompt));
}

export function wantsPlan(prompt) {
  const text = userText(prompt);
  if (text.trimStart().startsWith("/")) return false;
  return PLAN_PATTERNS.some((pattern) => pattern.test(text));
}

export function asksForPlan(prompt) {
  const text = userText(prompt);
  if (text.trimStart().startsWith("/")) return false;
  return PLAN_REQUEST_PATTERNS.some((pattern) => pattern.test(text));
}

export function wantsChange(prompt) {
  const text = userText(prompt);
  return CHANGE_PATTERNS.some((pattern) => pattern.test(text));
}

// The pre-edit checks for a change request. A plan request that also carries a change verb gets them too.
const CHANGE_CHECKLIST = [
  "Before the first edit, check these briefly and keep the result to a few lines:",
  "1. Who is affected besides the requester: callers of the code, API or CLI users, operators, jobs, other agents.",
  "2. Up to three cases the request leaves undefined or contradicts (empty, boundary, repeat, concurrent,",
  "   partial failure, existing data). Ask the user only when the answer changes a reachable result;",
  "   otherwise pick the reading that matches existing code and say which one you used.",
  "3. Search the callers of every existing function, config key, or command you will modify.",
  `   \`node "${IMPACT_SCRIPT}" --symbol <name>\` lists callers and related tests in a few lines;`,
  "   use Grep for literal strings such as messages, keys built at runtime, or config values.",
];

export function buildContext({ withPlanAgents = false } = {}) {
  return [
    MARKER,
    "This prompt may ask for a code change. If it does not, ignore this block.",
    ...CHANGE_CHECKLIST,
    ...PLAN_FIRST,
    ...(withPlanAgents ? PLAN_AGENTS : []),
    "</omo-preflight>",
  ].join("\n");
}

// Every change settles its approach in omo-plan before the first edit. Only edits that cannot change
// behavior skip it. Documentation is not exempt: describing behavior correctly often needs the source read.
const PLAN_FIRST = [
  "Before the first edit, load `omo-orchestrator:omo-plan` and settle the approach there. Skip it only when",
  "the whole change is a typo fix, a wording change, or a config value change. Documentation changes are",
  "not exempt: describing behavior correctly often needs the source read.",
  "The plan names the executor by size, and its approval starts it: one scoped pass on 1-2 files ->",
  "`omo-orchestrator:omo-implement`; several tasks or a change that needs review-fix rounds ->",
  "`omo-orchestrator:omo-review` with args `review-loop <plan-path>`; dependent waves across many files ->",
  "`omo-orchestrator:omo-ultrawork` with args `ulw-execute <plan-path>`.",
];

// Added when a change request also asks for a plan or a design: omo-plan then runs its planning agents.
const PLAN_AGENTS = [
  "If the prompt also asks for a plan or a design (not just a change to something named plan or design), omo-plan",
  "runs its planning agents instead of writing the plan in the main context: `omo-plan-consultant`, then",
  "`omo-planner`, then `omo-plan-reviewer`.",
];

export function buildPlanContext({ withChecklist = false } = {}) {
  return [
    MARKER,
    "This prompt asks for a plan or a design. If it only asks about an existing one, ignore this block.",
    "Load `omo-orchestrator:omo-plan` with the Skill tool and follow it as a plan request. Run its planning",
    "agents instead of writing the plan in the main context: `omo-plan-consultant` first, then `omo-planner`",
    "with the consultant's findings (its dispatch carries a `LOAD_SKILLS` line), then `omo-plan-reviewer`.",
    "When the prompt also asks for the change itself, omo-plan's approval scope for a change request applies:",
    "approval also starts the recommended executor.",
    "Skip omo-plan only when the whole request is a typo fix, a wording change, or a config value change.",
    // Telling "移行の計画を立てて" (移行 is a noun) from "計画を立てて、実装して" needs more than keywords,
    // so a plan request with a change verb keeps the change checks and lets the model judge.
    ...(withChecklist ? ["If the prompt also asks for a code change, apply these checks to it too.", ...CHANGE_CHECKLIST] : []),
    "</omo-preflight>",
  ].join("\n");
}

export function buildIssueContext() {
  return [
    MARKER,
    "This prompt hands over a GitHub issue to work on. If it does not, ignore this block.",
    "Load `omo-orchestrator:omo-work-with-pr` with args `github-triage <issue-url>` first and read the issue: goal, reproduction, whether the premise",
    "still holds in the current code, and the next action. When the next action is a code or doc change:",
    ...PLAN_FIRST,
    "</omo-preflight>",
  ].join("\n");
}

export function buildReviewContext() {
  return [
    MARKER,
    "This prompt asks for a review. If it does not, ignore this block.",
    "Load `omo-orchestrator:omo-review` with the Skill tool before reading the change. It is the single review",
    "entry: it runs an omo reviewer, then the `self-review` skill to fix findings, and merges their verdicts.",
    "Whatever runs, follow each changed value past the diff: who reads a status, flag, or field the change",
    "now writes (queries, schedulers, jobs, other services), what the old code did on the failure path that",
    "the new code changes, and whether a retried or repeated call is safe.",
    "</omo-preflight>",
  ].join("\n");
}

export function buildFollowUpContext() {
  return [
    MARKER,
    "This prompt hands over review comments on an existing PR. If it does not, ignore this block.",
    "Load `omo-orchestrator:omo-work-with-pr` and follow its section on follow-up changes to an existing PR.",
    "Before calling the work done, without asking first: run `omo-orchestrator:omo-review` on the whole",
    "branch diff, and end the report with one reply draft per comment you handled and a PR body update",
    "draft (or `no update needed` with the reason), so the user only has to approve posting.",
    "</omo-preflight>",
  ].join("\n");
}

export function recordTurnStart(input, env = process.env) {
  if (typeof input.session_id !== "string" || typeof input.cwd !== "string") return;
  // A task notification continues the current turn; resnapshotting would hide the turn's earlier edits.
  if (stripInjected(input.prompt).trim().length === 0) return;
  if (/^(off|0|false)$/i.test(env.OMO_REVIEW_GATE ?? "")) return;
  saveSnapshot(input.session_id, takeSnapshot(input.cwd), env);
}

export function run(input, { env = process.env, record = recordTurnStart } = {}) {
  if (typeof input !== "object" || input === null || typeof input.prompt !== "string") return "";
  if (input.hook_event_name !== undefined && input.hook_event_name !== "UserPromptSubmit") return "";
  record(input, env);
  if (/^(off|0|false)$/i.test(env.OMO_PREFLIGHT ?? "")) return "";
  if (detectKeyword(input.prompt) !== null) return "";
  // A review request often says "do not fix" (修正はせず), so it is checked before the change verbs.
  let context;
  if (handsOverReviewComments(input.prompt)) context = buildFollowUpContext();
  else if (wantsReview(input.prompt)) context = buildReviewContext();
  else if (handsOverIssue(input.prompt)) context = buildIssueContext();
  else if (asksForPlan(input.prompt)) context = buildPlanContext({ withChecklist: wantsChange(input.prompt) });
  else if (wantsChange(input.prompt)) context = buildContext({ withPlanAgents: wantsPlan(input.prompt) });
  else if (wantsPlan(input.prompt)) context = buildPlanContext();
  else return "";
  const output = {
    hookSpecificOutput: { hookEventName: "UserPromptSubmit", additionalContext: context },
  };
  return `${JSON.stringify(output)}\n`;
}

async function readStdin() {
  let data = "";
  process.stdin.setEncoding("utf8");
  for await (const chunk of process.stdin) data += chunk;
  return data;
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  let parsed;
  try {
    parsed = JSON.parse(await readStdin());
  } catch {
    parsed = undefined;
  }
  const output = run(parsed);
  if (output.length > 0) process.stdout.write(output);
}
