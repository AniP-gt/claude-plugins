/**
 * At session end, extract candidates worth keeping in the wiki from the conversation and save them to raw/inbox/.
 *
 * Started as a separate process from the SessionEnd hook (llm_wiki.ts capture). Does not update pages.
 * At the start of the next session, the candidates are triaged without asking, following /llm-wiki:ingest.
 */
import { spawnSync } from "node:child_process";
import { appendFileSync, mkdirSync, mkdtempSync, readdirSync, readFileSync, rmSync, unlinkSync, writeFileSync } from "node:fs";
import { homedir, tmpdir } from "node:os";
import { dirname, join } from "node:path";

export const GUARD_ENV = "LLM_WIKI_CAPTURE";
const LOG_PATH = join(homedir(), ".config", "llm-wiki", "capture.log");
export const DEFAULTS = { enabled: false, model: "sonnet", min_chars: 3000, max_chars: 80000, timeout: 300 };
export type CaptureSettings = typeof DEFAULTS;
const MESSAGE_MAX_CHARS = 4000;
const TAG_RE = /<(system-reminder|command-[a-z-]+|local-command-[a-z-]+|task-notification)>.*?<\/\1>/gs;
const SECRET_PATTERNS: [RegExp, string][] = [
  [/-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----/gs, "<redacted-private-key>"],
  [/\bAKIA[0-9A-Z]{16}\b/g, "<redacted-aws-key>"],
  [/\bgh[pousr]_[A-Za-z0-9]{20,}\b/g, "<redacted-github-token>"],
  [/\bsk-[A-Za-z0-9_-]{20,}\b/g, "<redacted-api-key>"],
  [/\bxox[abprs]-[A-Za-z0-9-]{10,}\b/g, "<redacted-slack-token>"],
  [/\b(password|passwd|secret|token|api[_-]?key|access[_-]?key)(\s*[:=]\s*)(\S+)/gi, "$1$2<redacted>"],
];

const PROMPT = `You are the record keeper for a software development team. The <conversation> below is a Claude Code session in the repository {project}.
Extract only the "candidates" worth keeping in this repository's knowledge wiki.

Worth keeping:
- Design decisions (what was decided and how, why, and rejected alternatives)
- Causes of and fixes for incidents and bugs
- Gotchas, specs, and operational notes that are hard to see from the code or docs
- Measured values and confirmed facts (with dates and Issue/PR numbers)

Not worth keeping:
- The work steps themselves, small talk, command output, transient progress
- General programming knowledge
- Anything already in <existing_index> below (keep it only when a new fact was added)
- Secrets (tokens, passwords, keys, personal contact details)

Output rules:
- If there is nothing worth keeping, output only NONE.
- Otherwise, write Markdown with one entry per candidate in the format below. Do not write any introduction or closing.
- Write the candidates in English (the wiki is written in English). Translate even when the conversation is in Japanese. Keep code, identifiers, paths, commands, error messages, and proper names exactly as they appear.

## <short title>
- Type: decision | problem | gotcha | fact
- Content: <1-5 lines. Facts only. Mark guesses with "Speculation:">
- Evidence: <evidence confirmed in the conversation: file paths, PR/Issue numbers, command results, etc.>
- Confidence: high | medium | low
- Related existing pages: <[[page name]] or none>

<existing_index>
{index}
</existing_index>

<conversation>
{conversation}
</conversation>
`;

export interface Project {
  project: string;
  repo: string;
  wiki: string;
}

/** Length in code points (Python str semantics), so limits match the former implementation. */
export const cpLength = (s: string): number => Array.from(s).length;
export const cpSlice = (s: string, start: number, end?: number): string => Array.from(s).slice(start, end).join("");

export function settings(config: Record<string, unknown>): CaptureSettings {
  return { ...DEFAULTS, ...((config.capture as Partial<CaptureSettings> | undefined) || {}) };
}

const pad = (n: number, w = 2) => String(n).padStart(w, "0");
const localDate = (d: Date) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
const localTime = (d: Date) => `${pad(d.getHours())}:${pad(d.getMinutes())}`;

export function log(message: string): void {
  try {
    mkdirSync(dirname(LOG_PATH), { recursive: true });
    const now = new Date();
    appendFileSync(LOG_PATH, `${localDate(now)}T${localTime(now)}:${pad(now.getSeconds())} ${message}\n`, "utf-8");
  } catch {
    // Logging must never break the hook
  }
}

function redact(text: string): string {
  for (const [pattern, repl] of SECRET_PATTERNS) text = text.replace(pattern, repl);
  return text;
}

function messageText(content: unknown): string {
  if (typeof content === "string") return content;
  if (!Array.isArray(content)) return "";
  return content
    .filter((b) => b && typeof b === "object" && !Array.isArray(b) && b.type === "text")
    .map((b) => (typeof b.text === "string" ? b.text : ""))
    .join("\n");
}

/** Return a list of [role, text] and the last git branch seen. Excludes tool input/output, thinking, and meta lines. */
function readTranscript(path: string): { turns: [string, string][]; branch: string } {
  const turns: [string, string][] = [];
  let branch = "";
  for (const line of readFileSync(path, "utf-8").split("\n")) {
    let entry: any;
    try {
      entry = JSON.parse(line);
    } catch {
      continue;
    }
    if (!entry || typeof entry !== "object" || Array.isArray(entry)) continue;
    if ((entry.type !== "user" && entry.type !== "assistant") || entry.isMeta || entry.isSidechain) continue;
    branch = entry.gitBranch || branch;
    const text = messageText((entry.message || {}).content).replace(TAG_RE, "").trim();
    if (text) turns.push([entry.type, cpSlice(text, 0, MESSAGE_MAX_CHARS)]);
  }
  return { turns, branch };
}

function buildConversation(turns: [string, string][], maxChars: number): string {
  const body = turns.map(([role, text]) => `[${role}] ${text}`).join("\n\n");
  const chars = Array.from(body);
  return chars.length <= maxChars ? body : "… (earlier part omitted)\n\n" + chars.slice(-maxChars).join("");
}

function summarize(prompt: string, model: string, timeoutSec: number): string {
  const cmd = ["-p", "--model", model, "--setting-sources", "project", "--tools", "",
    "--no-session-persistence", "--disable-slash-commands"];
  const tmp = mkdtempSync(join(tmpdir(), "llm-wiki-"));
  try {
    const result = spawnSync("claude", cmd, {
      input: prompt, cwd: tmp, timeout: timeoutSec * 1000, maxBuffer: 64 * 1024 * 1024,
      env: { ...process.env, [GUARD_ENV]: "1" }, encoding: "utf-8",
    });
    if (result.error) throw result.error;
    if (result.status !== 0) {
      throw new Error(`claude exit ${result.status}: ${cpSlice((result.stderr || "").trim(), 0, 300)}`);
    }
    return (result.stdout || "").trim();
  } finally {
    rmSync(tmp, { recursive: true, force: true });
  }
}

export function run(found: Project, config: Record<string, unknown>, transcript: string, sessionId: string, indexText: string): number {
  const opts = settings(config);
  const sid = sessionId.slice(0, 8);
  const label = `${found.project} session=${sid}`;
  const { turns, branch } = readTranscript(transcript);
  const conversation = redact(buildConversation(turns, opts.max_chars));
  const chars = cpLength(conversation);
  if (chars < opts.min_chars) {
    log(`skip ${label}: chars=${chars}`);
    return 0;
  }
  // Replace placeholders in one pass so text inside the index or conversation is never substituted again
  const values: Record<string, string> = { project: found.project, index: indexText, conversation };
  const prompt = PROMPT.replace(/\{(project|index|conversation)\}/g, (_, k: string) => values[k]);
  let output: string;
  try {
    output = redact(summarize(prompt, opts.model, opts.timeout));
  } catch (e) {
    log(`error ${label}: ${e instanceof Error ? e.message : e}`);
    return 1;
  }
  if (!output || output.toUpperCase().startsWith("NONE")) {
    log(`none ${label}`);
    return 0;
  }
  const now = new Date();
  const inbox = join(found.wiki, "raw", "inbox");
  mkdirSync(inbox, { recursive: true });
  // A resumed session's conversation is a superset of the previous one, so replace older candidates from the same session
  for (const name of readdirSync(inbox)) {
    if (name.endsWith(`-${sid}.md`)) unlinkSync(join(inbox, name));
  }
  const dest = join(inbox, `${localDate(now)}-${pad(now.getHours())}${pad(now.getMinutes())}-${sid}.md`);
  const header = `> Source: Claude Code session \`${sessionId}\` (${found.project}` +
    `${branch ? ", branch " + branch : ""}), auto-extracted at ${localDate(now)} ${localTime(now)}. ` +
    "Unverified candidates. Triage them with /llm-wiki:ingest.\n\n";
  writeFileSync(dest, header + output + "\n", "utf-8");
  log(`saved ${label}: ${dest}`);
  return 0;
}
