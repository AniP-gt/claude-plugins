#!/usr/bin/env node
// Stop hook: when this turn changed files (one or more by default) and nothing reviewed them after the last edit, block the
// stop once and ask Claude for a review of hidden impact (risk map, undefined cases, validation).
// Changed files come from the git snapshot preflight.ts took at the prompt, so Bash and sub-agent edits
// count; the transcript's Edit/Write calls are the fallback outside git.
// A stop with stop_hook_active=true checks again after goal-gate feedback, even if both gates blocked the same Stop.
// Only this hook's feedback from a later Stop (after a main-thread assistant entry) ends that re-check chain.
// An unreadable transcript or unrecognized feedback passes.
// A background task notification continues the same turn and triggers a fresh stop without that flag, so
// the gate also passes when its own feedback already follows the last edit: it asks once per edit.
// While a Codex implementation run is in flight, the review is not due: its edits are half done and the turn may
// end only to relay a Codex question or to wait. The controller marks the run with <git root>/.claude/omo/codex/IN_FLIGHT;
// a marker younger than 24 hours holds the review check back, an older one is stale and ignored.
// A second check blocks once when this turn ran omo-review but shows no sign of its Codex lane afterwards.
import { readFileSync, realpathSync, statSync } from "node:fs";
import { basename, dirname, isAbsolute, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { filesChangedSince, gitRoot, loadSnapshot } from "./turn-snapshot.ts";
import { stripInjected } from "./ulw-keyword.ts";

type Env = NodeJS.ProcessEnv;

// One content block of a transcript message; tool_use, tool_result, and text blocks share this loose shape.
export interface ContentBlock {
  type?: string;
  text?: string;
  name?: string;
  id?: string;
  input?: Record<string, unknown>;
  tool_use_id?: string;
  is_error?: boolean;
  content?: unknown;
}

// One parsed transcript line. Only the fields the gates read are listed.
export interface TranscriptEntry {
  type?: string;
  isMeta?: boolean;
  isSidechain?: boolean;
  message?: { content?: string | ContentBlock[] };
  attachment?: { type?: string; blockingError?: string | { blockingError?: unknown } };
}

// A tool_use block, or the { name: GATE_FEEDBACK } marker entry.
export type ToolUse = ContentBlock;

export interface TurnSummary {
  files: string[];
  delegatedEdit: boolean;
  reviewed: boolean;
}

// The Stop hook payload fields the gates read; the payload is untrusted JSON.
export interface StopInput {
  hook_event_name?: unknown;
  transcript_path?: unknown;
  stop_hook_active?: unknown;
  cwd?: unknown;
  session_id?: unknown;
}

const MARKER = "[OMO REVIEW GATE]";
export const GOAL_MARKER = "[OMO GOAL GATE]";
const EDIT_TOOLS = new Set<string | undefined>(["Edit", "Write", "MultiEdit", "NotebookEdit"]);
const DELEGATE_TOOLS = new Set<string | undefined>(["Agent", "Task"]);
// Sub-agents whose edits never appear in this transcript; one call counts as a change to unknown files.
const EDITING_AGENT_PATTERN = /implementer|builder/i;
const REVIEW_SKILL_PATTERN = /review/i;
// omo-oracle advises and never approves (omo-review review-loop), so consulting it does not count as a review.
const REVIEW_AGENT_PATTERN = /review|security-check/i;
// The handoff ledger and notepads are bookkeeping, not product changes. Review skills write their reports
// under docs/reviews/ after they run; counting those would ask for a review of the review.
const IGNORED_PATH_PATTERN = /(^|\/)(?:\.claude\/omo|docs\/reviews)\//;

const CODEX_IN_FLIGHT_MARKER = ".claude/omo/codex/IN_FLIGHT";
const CODEX_IN_FLIGHT_MAX_AGE_MS = 24 * 60 * 60 * 1000;

// True when a Codex run's marker file exists under the git root of cwd, with an mtime within the last 24 hours
// (a future mtime is not trusted).
export function codexRunInFlight(cwd: string | undefined, now: number = Date.now()): boolean {
  if (cwd === undefined) return false;
  const root = gitRoot(cwd);
  if (root === null) return false;
  try {
    const marker = statSync(join(root, CODEX_IN_FLIGHT_MARKER));
    const age = now - marker.mtimeMs;
    return marker.isFile() && age >= 0 && age < CODEX_IN_FLIGHT_MAX_AGE_MS;
  } catch {
    return false;
  }
}

export function minFiles(env: Env = process.env): number {
  const value = Number.parseInt(env.OMO_REVIEW_GATE_MIN_FILES ?? "", 10);
  return Number.isInteger(value) && value > 0 ? value : 1;
}

// A `!` shell command the user runs lands as <bash-input>/<bash-stdout> user messages. It fires no
// UserPromptSubmit, so the snapshot stays at the last prompt; treating it as a new turn would forget the
// gate's earlier feedback and block again on the same files.
const BASH_MODE_PATTERN = /<(bash-input|bash-stdout|bash-stderr)>[\s\S]*?<\/\1>/g;

// Task notifications, system reminders, and `!` shell commands arrive as user messages but continue the
// same turn.
function isRealUserPrompt(entry: TranscriptEntry | null | undefined): boolean {
  if (entry?.type !== "user" || entry.isMeta === true || entry.isSidechain === true) return false;
  const content = entry.message?.content;
  let text: string;
  if (typeof content === "string") text = content;
  else if (Array.isArray(content) && !content.some((block) => block?.type === "tool_result")) {
    text = content.map((block) => (block?.type === "text" ? block.text : "")).join("\n");
  } else return false;
  return stripInjected(text).replace(BASH_MODE_PATTERN, " ").trim().length > 0;
}

// Marks where this gate's own feedback landed in the turn; summarizeTurn treats it like a review.
export const GATE_FEEDBACK = "omo-review-gate-feedback";

// Stop feedback may be stored as a meta user message or as a hook_blocking_error attachment.
export function isGateFeedback(entry: TranscriptEntry | null | undefined, marker: string = MARKER): boolean {
  if (entry?.isSidechain === true) return false;
  if (entry?.type === "attachment" && entry.attachment?.type === "hook_blocking_error") {
    return JSON.stringify(entry.attachment.blockingError ?? "").includes(marker);
  }
  if (entry?.type !== "user" || entry.isMeta !== true) return false;
  const content = entry.message?.content;
  return typeof content === "string" && content.includes(marker);
}

// Index of the first entry after the last real user prompt.
function turnStart(entries: TranscriptEntry[]): number {
  for (let i = entries.length - 1; i >= 0; i -= 1) if (isRealUserPrompt(entries[i])) return i + 1;
  return 0;
}

// Returns the tool_use blocks the main thread issued since the last real user prompt, with a
// { name: GATE_FEEDBACK } entry wherever the gate already blocked a stop.
export function currentTurnToolUses(entries: TranscriptEntry[]): ToolUse[] {
  const start = turnStart(entries);
  const uses: ToolUse[] = [];
  for (const entry of entries.slice(start)) {
    if (isGateFeedback(entry)) {
      uses.push({ name: GATE_FEEDBACK });
      continue;
    }
    if (entry?.type !== "assistant" || entry.isSidechain === true) continue;
    const content = entry.message?.content;
    if (!Array.isArray(content)) continue;
    for (const block of content) if (block?.type === "tool_use") uses.push(block);
  }
  return uses;
}

// Edits seen in the transcript, whether a sub-agent may have edited, and whether a review ran after the
// last edit. A review that an edit follows no longer covers the final state.
export function summarizeTurn(uses: ToolUse[], cwd: string | undefined): TurnSummary {
  const files = new Set<string>();
  let delegatedEdit = false;
  let reviewed = false;
  for (const use of uses) {
    const input = use.input ?? {};
    if (EDIT_TOOLS.has(use.name)) {
      const target = input.file_path ?? input.notebook_path;
      if (typeof target !== "string") continue;
      const absolute = cwd && !isAbsolute(target) ? resolve(cwd, target) : target;
      if (!isReviewable(absolute, cwd)) continue;
      files.add(absolute);
      reviewed = false;
    } else if (DELEGATE_TOOLS.has(use.name)) {
      const type = typeof input.subagent_type === "string" ? input.subagent_type : "";
      if (REVIEW_AGENT_PATTERN.test(type)) reviewed = true;
      else if (EDITING_AGENT_PATTERN.test(type)) {
        delegatedEdit = true;
        reviewed = false;
      }
    } else if (use.name === GATE_FEEDBACK) {
      reviewed = true;
    } else if (use.name === "Skill") {
      if (REVIEW_SKILL_PATTERN.test(String(input.skill ?? ""))) reviewed = true;
    }
  }
  return { files: [...files], delegatedEdit, reviewed };
}

// Scratch files outside the working tree and the omo ledger are not part of the change under review.
function isReviewable(absolute: string, cwd: string | undefined): boolean {
  const shown = inside(absolute, cwd);
  if (shown === null) return false;
  // A session started in docs/ shows reports as reviews/self/x.md, so the last two cwd segments are
  // prefixed. Ancestors above them are left out: a repository under /work/docs/reviews/ is not all reports.
  const context = cwd ? `${basename(dirname(cwd))}/${basename(cwd)}/${shown}` : shown;
  return !IGNORED_PATH_PATTERN.test(context);
}

// Path relative to cwd, or null when it lies outside. Git reports symlink-resolved paths (/private/tmp
// for /tmp on macOS), so the resolved cwd is tried as well.
function inside(absolute: string, cwd: string | undefined): string | null {
  if (!cwd) return absolute;
  for (const base of [cwd, resolvedCwd(cwd)]) {
    const shown = relative(base, absolute);
    if (!shown.startsWith("..") && !isAbsolute(shown)) return shown;
  }
  return null;
}

function resolvedCwd(cwd: string): string {
  try {
    return realpathSync(cwd);
  } catch {
    return cwd;
  }
}

function display(absolute: string, cwd: string | undefined): string {
  return (inside(absolute, cwd) ?? absolute).replace(/[\r\n]+/g, " ");
}

const MAX_LISTED_FILES = 5;

export function buildReason({ files, delegatedEdit }: { files: string[]; delegatedEdit: boolean }): string {
  const what = files.length > 0 ? `${files.length} ファイルを変更し` : "サブエージェントがファイルを変更し";
  const lines = [`${MARKER} ${what}、最後の編集のあとにレビューしていません。`];
  for (const file of files.slice(0, MAX_LISTED_FILES)) lines.push(`- ${file}`);
  if (files.length > MAX_LISTED_FILES) lines.push(`- ほか ${files.length - MAX_LISTED_FILES} 件`);
  if (delegatedEdit && files.length === 0) lines.push("先にサブエージェントの差分（git diff）を読んでください。");
  lines.push(
    "",
    "終える前に、次のどれか1つを選んでください。",
    "- 誤字か設定値だけの変更なら、そう1行で書いて終える。ドキュメントやコメントの説明は挙動の主張なので軽いレビューの対象。",
    "- 3ファイル以上、公開 API や CLI の挙動、永続化、セキュリティに関わるなら `omo-orchestrator:omo-review` を実行する。",
    "- それ以外は軽いレビュー: 変更した関数などの呼び出し元と隠れた影響範囲、それを守るテストなど。",
    "  空入力・境界値・重複や並行実行・途中失敗・既存データの扱い。実際に実行した確認。",
    "  範囲内の問題は直し、守りのないリスクは最終回答に書き、必要なら利用者に1つだけ質問する。",
  );
  return lines.join("\n");
}

const CODEX_MARKER = "[OMO CODEX GATE]";
const OMO_REVIEW_SKILL_PATTERN = /(^|:)omo-review$/;
// A user-typed `/omo-review` lands as the prompt itself, not as a Skill call.
const OMO_REVIEW_COMMAND_PATTERN = /<command-name>\/?(omo-orchestrator:)?omo-review<\/command-name>/;
// Every Codex run may put `--dangerously-bypass-hook-trust` between `codex` and `exec`.
const CODEX_EXEC_PATTERN = /codex\s+(--dangerously-bypass-hook-trust\s+)?exec\b/;
const CODEX_COMMAND_PATTERN = new RegExp(`(^|[\\s;&|(])(${CODEX_EXEC_PATTERN.source}|command\\s+-v\\s+codex\\b)`);
// A consult (scratch dir `omo-consult/`) or an adversarial run (`.adv.` files) is read-only Codex use, but not the
// review lane. Their preflight is `codex --version` without `command -v`, so only the lane's probe matches above.
const NON_LANE_EXEC_PATTERN = /omo-consult\/|\.adv\./;
// Status lines a review sub-agent returns: `codex: …` from codex-lane.md and self-review's `Codex 実行: …`.
// `codex: run by caller` is left out: it hands the lane to the caller, which still has to run it.
const CODEX_STATUS_PATTERN =
  /codex:\s*(OK|NOT_EXECUTED)|Codex 実行\**\s*[:：]\s*\**\s*(OK|NOT_EXECUTED)|CODEX_EXECUTION\**\s*[:：]\s*\**\s*(EXECUTED|NOT_EXECUTED)/i;
// A review sub-agent often answers in free prose and leaves the status line in the report file it names.
const REPORT_PATH_PATTERN = /[^\s`'"()<>]*review[^\s`'"()<>]*\.md\b/gi;
const MAX_REPORTS_READ = 3;

export function readReportFile(path: string, cwd: string | undefined): string {
  try {
    return readFileSync(isAbsolute(path) || !cwd ? path : resolve(cwd, path), "utf8");
  } catch {
    return "";
  }
}

// True when the sub-agent's result carries a Codex status line, or names a review report file that does.
function hasCodexStatus(text: string, readReport: (path: string) => string): boolean {
  if (CODEX_STATUS_PATTERN.test(text)) return true;
  const paths = [...new Set(text.match(REPORT_PATH_PATTERN) ?? [])].slice(0, MAX_REPORTS_READ);
  return paths.some((path) => CODEX_STATUS_PATTERN.test(readReport(path)));
}

// Comment lines mention commands without running them.
function withoutComments(command: unknown): string {
  return String(command ?? "")
    .split("\n")
    .filter((line) => !line.trimStart().startsWith("#"))
    .join("\n");
}

function isLaneCodexCommand(command: string): boolean {
  if (!CODEX_COMMAND_PATTERN.test(command)) return false;
  return !(CODEX_EXEC_PATTERN.test(command) && NON_LANE_EXEC_PATTERN.test(command));
}

function textOf(content: unknown): string {
  if (typeof content === "string") return content;
  if (!Array.isArray(content)) return "";
  return content.map((block) => (typeof block?.text === "string" ? block.text : "")).join("\n");
}

// Launch results of background work. Their id is the <task-id> of the notification that reports the end.
const BACKGROUND_LAUNCH_PATTERNS = [
  /^\s*Async agent launched successfully[\s\S]*?agentId:\s*([\w-]+)/,
  /^\s*Command running in background with ID:\s*([\w-]+)/,
];
const TASK_NOTIFICATION_PATTERN = /<task-notification>([\s\S]*?)<\/task-notification>/g;

function backgroundTaskId(text: string): string | null {
  for (const pattern of BACKGROUND_LAUNCH_PATTERNS) {
    const match = pattern.exec(text);
    if (match) return match[1];
  }
  return null;
}

// Shared background launch/result/notification tracking; callers decide when a launch counts.
function backgroundTaskTracker() {
  const uses = new Map<string | undefined, boolean>();
  const running = new Map<string, boolean>();
  return {
    running,
    use(block: ContentBlock): void {
      if (DELEGATE_TOOLS.has(block.name) || block.input?.run_in_background === true) {
        uses.set(block.id, DELEGATE_TOOLS.has(block.name));
      }
    },
    result(block: ContentBlock, enabled = true): void {
      if (!enabled || !uses.has(block.tool_use_id)) return;
      const id = backgroundTaskId(textOf(block.content));
      if (id !== null) running.set(id, uses.get(block.tool_use_id) as boolean);
    },
    notifications(content: unknown, onComplete: (body: string, delegated: boolean) => void = () => {}): void {
      for (const [, body] of textOf(content).matchAll(TASK_NOTIFICATION_PATTERN)) {
        const id = /<task-id>\s*([\w-]+)\s*<\/task-id>/.exec(body)?.[1];
        if (id === undefined || !running.has(id)) continue;
        onComplete(body, running.get(id) as boolean);
        running.delete(id);
      }
    },
  };
}

export function backgroundPending(entries: TranscriptEntry[]): boolean {
  const tasks = backgroundTaskTracker();
  for (const entry of entries.slice(turnStart(entries))) {
    if (entry?.isSidechain === true) continue;
    const content = entry?.message?.content;
    if (entry?.type === "user") tasks.notifications(content);
    if (!Array.isArray(content)) continue;
    for (const block of content) {
      if (entry.type === "assistant" && block?.type === "tool_use") tasks.use(block);
      else if (entry.type === "user" && block?.type === "tool_result") tasks.result(block);
    }
  }
  return tasks.running.size > 0;
}

// True when this turn invoked omo-review and nothing after the last invocation shows its Codex lane: a Bash
// call that ran or probed `codex`, or a Codex status line in a sub-agent's result or in the review report file
// that result names. Only Agent/Task results
// and their task notifications count, because a Read of codex-lane.md or the skill text carries the same
// status line as an example.
// While background work launched after the invocation (a sub-agent running the review, or a background Bash
// command) has not reported back, the turn ends only to wait: its notification continues the turn and triggers
// a fresh stop. Launches are recognized only at the start of a tool result, so a report quoting them is not one.
export function codexLaneMissing(entries: TranscriptEntry[], readReport: (path: string) => string = () => ""): boolean {
  const start = turnStart(entries);
  let pending = start > 0 && OMO_REVIEW_COMMAND_PATTERN.test(textOf(entries[start - 1]?.message?.content));
  const delegateIds = new Set<string | undefined>();
  const background = backgroundTaskTracker();
  const running = background.running;
  for (const entry of entries.slice(start)) {
    if (isGateFeedback(entry, CODEX_MARKER)) {
      pending = false;
      continue;
    }
    if (entry?.isSidechain === true) continue;
    const content = entry?.message?.content;
    if (entry?.type === "user") {
      background.notifications(content, (body, delegated) => {
        if (delegated && hasCodexStatus(body, readReport)) pending = false;
      });
    }
    if (!Array.isArray(content)) continue;
    for (const block of content) {
      if (entry.type === "assistant" && block?.type === "tool_use") {
        const input = block.input ?? {};
        if (block.name === "Skill" && OMO_REVIEW_SKILL_PATTERN.test(String(input.skill ?? ""))) {
          pending = true;
          running.clear();
        } else if (block.name === "Bash" && isLaneCodexCommand(withoutComments(input.command))) pending = false;
        else if (DELEGATE_TOOLS.has(block.name)) delegateIds.add(block.id);
        background.use(block);
      } else if (entry.type === "user" && block?.type === "tool_result") {
        const text = textOf(block.content);
        if (delegateIds.has(block.tool_use_id) && hasCodexStatus(text, readReport)) pending = false;
        background.result(block, pending);
      }
    }
  }
  return pending && running.size === 0;
}

export function buildCodexReason(): string {
  return [
    `${CODEX_MARKER} このターンで omo-review を実行しましたが、Codex レーンの実行が見当たりません。`,
    "",
    "終える前に、次のどれか1つを選んでください。",
    "- `omo-review` の `references/codex-lane.md` に従って Codex を実行し、`codex:` の状態行を最終報告に書く。",
    "- self-review が Codex を実行済みなら、そのレポートの `Codex 実行` 行を確認して `codex: OK (self-review, <path>)` を書く。",
    "- レビュー自体を実行しなかった（コントローラー内で二重レビューを避けた等）なら、そう1行で書いて終える。",
  ].join("\n");
}

function block(reason: string): string {
  return `${JSON.stringify({ decision: "block", reason })}\n`;
}

export function readTranscript(path: string): TranscriptEntry[] {
  try {
    return readFileSync(path, "utf8")
      .split("\n")
      .filter((line) => line.trim().length > 0)
      .map((line) => {
        try {
          return JSON.parse(line) as TranscriptEntry | null;
        } catch {
          return null;
        }
      })
      .filter((entry): entry is TranscriptEntry => entry !== null);
  } catch {
    return [];
  }
}

// Goal feedback always arms the check. Own feedback can disarm only after the assistant resumed,
// so simultaneous blocks cannot hide later edits. Unknown or absent goal feedback remains fail-open.
function goalChainNeedsCheck(entries: TranscriptEntry[]): boolean {
  let pending = false;
  let assistantSinceGoal = false;
  for (const entry of entries.slice(turnStart(entries))) {
    if (entry?.isSidechain === true) continue;
    if (entry?.type === "assistant" && pending) assistantSinceGoal = true;
    if (assistantSinceGoal && (isGateFeedback(entry, MARKER) || isGateFeedback(entry, CODEX_MARKER))) {
      pending = false;
    }
    // Separate from the own-marker check: a combined same-Stop record also arms the re-check.
    if (isGateFeedback(entry, GOAL_MARKER)) {
      pending = true;
      assistantSinceGoal = false;
    }
  }
  return pending;
}

export interface RunDeps {
  env?: Env;
  loadTranscript?: (path: string) => TranscriptEntry[];
  changedFiles?: (sessionId: unknown, env: Env, cwd: string | undefined) => string[] | null;
  codexInFlight?: (cwd: string | undefined) => boolean;
  readReport?: (path: string, cwd: string | undefined) => string;
}

export function run(
  input: unknown,
  {
    env = process.env,
    loadTranscript = readTranscript,
    changedFiles = gitChangedFiles,
    codexInFlight = codexRunInFlight,
    readReport = readReportFile,
  }: RunDeps = {},
): string {
  if (typeof input !== "object" || input === null) return "";
  const stop: StopInput = input;
  if (stop.hook_event_name !== undefined && stop.hook_event_name !== "Stop") return "";
  if (typeof stop.transcript_path !== "string") return "";
  const entries = loadTranscript(stop.transcript_path);
  if (stop.stop_hook_active === true && !goalChainNeedsCheck(entries)) return "";
  if (!/^(off|0|false)$/i.test(env.OMO_REVIEW_GATE ?? "")) {
    const reason = reviewReason(entries, stop, env, changedFiles, codexInFlight);
    if (reason !== null) return block(reason);
  }
  if (!/^(off|0|false)$/i.test(env.OMO_CODEX_GATE ?? "")) {
    const cwd = typeof stop.cwd === "string" ? stop.cwd : undefined;
    if (codexLaneMissing(entries, (path) => readReport(path, cwd))) return block(buildCodexReason());
  }
  return "";
}

function reviewReason(
  entries: TranscriptEntry[],
  input: StopInput,
  env: Env,
  changedFiles: NonNullable<RunDeps["changedFiles"]>,
  codexInFlight: NonNullable<RunDeps["codexInFlight"]>,
): string | null {
  const cwd = typeof input.cwd === "string" ? input.cwd : undefined;
  const turn = summarizeTurn(currentTurnToolUses(entries), cwd);
  if (turn.reviewed) return null;
  const fromGit = changedFiles(input.session_id, env, cwd);
  const files = new Set(turn.files);
  for (const file of fromGit ?? []) if (isReviewable(file, cwd)) files.add(file);
  // With a git snapshot, sub-agent edits are already in the file list; without one, guess from the call.
  const delegatedEdit = fromGit === null && turn.delegatedEdit;
  if (files.size < minFiles(env) && !delegatedEdit) return null;
  if (codexInFlight(cwd)) return null;
  const shown = [...files].map((file) => display(file, cwd)).sort();
  return buildReason({ files: shown, delegatedEdit });
}

// Absolute paths the turn changed according to the git snapshot, or null when there is no snapshot.
export function gitChangedFiles(
  sessionId: unknown,
  env: Env = process.env,
  cwd: string | undefined = undefined,
): string[] | null {
  const snapshot = loadSnapshot(sessionId, env, cwd);
  if (snapshot === null) return null;
  const changed = filesChangedSince(snapshot);
  return changed === null ? null : changed.map((path) => join(snapshot.root, path));
}

async function readStdin(): Promise<string> {
  let data = "";
  process.stdin.setEncoding("utf8");
  for await (const chunk of process.stdin) data += chunk;
  return data;
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  let parsed: unknown;
  try {
    parsed = JSON.parse(await readStdin());
  } catch {
    parsed = undefined;
  }
  const output = run(parsed);
  if (output.length > 0) process.stdout.write(output);
}
