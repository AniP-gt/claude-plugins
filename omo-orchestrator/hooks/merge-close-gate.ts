#!/usr/bin/env node
// PreToolUse hook (matcher Bash): `gh issue close` and `gh pr merge` are blocked while the issue or PR still has an
// unchecked acceptance-criteria / definition-of-ready / definition-of-done box. Without the hook "all AC met" is a
// claim the agent makes in prose; here the checkbox state on GitHub is the evidence, so a close or merge with open
// items is refused until each item is finished, backed by an evidence row (file:line link), and checked.
// Every `gh issue close <n>` and `gh pr merge [<n>]` found in the command (chained with &&, ||, ;, |, newlines, or
// inside `bash -c "..."`) is checked. Closing as "not planned" or duplicate is not a completion and passes.
// A PR is judged by its own body and by the body of each issue it closes (closingIssuesReferences).
// Only `- [ ]` style items under an AC / DoR / DoD heading or bold label count; other unchecked boxes are ignored.
// The gate FAILS CLOSED: gh missing, a non-zero exit, a timeout, an overall time budget used up before every target
// was read, or unreadable JSON denies the command, because "could not judge" must not pass. Malformed hook input is
// not ours and passes.
// gh runs in the hook input's `cwd` (when it is an existing directory), and `GH_REPO=owner/repo` in front of the
// command is passed as -R. A `cd <dir>` earlier in the same command is not followed.
// OMO_MERGE_GATE=off|0|false disables it. The gate is a routing check, not a security boundary: `gh api`, aliases,
// `eval`, scripts, a heredoc fed to a shell, and MCP merges are not seen.
import { execFileSync } from "node:child_process";
import { statSync } from "node:fs";
import { fileURLToPath } from "node:url";

// What a gh call is given besides its args: the directory to run in and the time it may take.
export type GhCallOptions = { cwd?: string; timeoutMs?: number };
// Runs gh with an args array (no shell) and returns stdout; throws an Error whose message says why it failed.
export type GhRunner = (args: string[], options?: GhCallOptions) => string;
type RunOptions = { env?: NodeJS.ProcessEnv; gh?: GhRunner; now?: () => number; deadlineMs?: number };
export type GhTarget = { kind: "issue" | "pr"; arg: string | undefined; repo: string | undefined };

const GH_TIMEOUT_MS = 6000;
// Below the 30s hooks.json timeout, so a slow gh run ends in our deny instead of the host killing the hook (which allows the command).
const OVERALL_DEADLINE_MS = 25000;
const MAX_LISTED_ITEMS = 10;
const ITEM_QUOTE_LIMIT = 120;
const SHELLS = new Set(["bash", "sh", "zsh"]);
const WRAPPERS = new Set(["command", "exec", "time", "sudo", "env", "nohup"]);
// Words that start a command position without being a command (`if gh pr merge 1; then`, `do gh ...`, `! gh ...`, `{ gh ...; }`).
const CONTROL_KEYWORDS = new Set(["if", "then", "elif", "else", "do", "while", "until", "!", "{"]);
const ENV_ASSIGNMENT = /^[A-Za-z_][A-Za-z0-9_]*=/;
const REDIRECTION = /^&?\d*[<>]/;
const BARE_REDIRECTION = /^&?\d*(?:>>?|<<?<?)$/;
// Flags that take a value, so the value is never mistaken for the issue or PR argument.
const ISSUE_CLOSE_VALUE_FLAGS = new Set(["-R", "--repo", "-r", "--reason", "-c", "--comment", "--duplicate-of"]);
const PR_MERGE_VALUE_FLAGS = new Set(["-R", "--repo", "-b", "--body", "-F", "--body-file", "-t", "--subject", "-A", "--author-email", "--match-head-commit"]);
const NOT_A_COMPLETION = /not[\s_-]*planned|duplicate/i;

type Heredoc = { delimiter: string; stripTabs: boolean; end: number };

// Reads `<<WORD`, `<<-WORD`, `<<'WORD'`, `<<"WORD"`, or `<<\WORD` at `start` (the first `<`); `end` is just past the delimiter word.
function readHeredocOperator(command: string, start: number): Heredoc {
  let i = start + 2;
  const stripTabs = command[i] === "-";
  if (stripTabs) i++;
  while (command[i] === " " || command[i] === "\t") i++;
  let delimiter = "";
  while (i < command.length && !/[\s;|&()<>]/.test(command[i] ?? "")) {
    const c = command[i] ?? "";
    if (c === "'" || c === '"') {
      const close = command.indexOf(c, i + 1);
      const stop = close === -1 ? command.length : close;
      delimiter += command.slice(i + 1, stop);
      i = stop + 1;
    } else if (c === "\\") {
      delimiter += command[i + 1] ?? "";
      i += 2;
    } else {
      delimiter += c;
      i++;
    }
  }
  return { delimiter, stripTabs, end: Math.min(i, command.length) };
}

// Returns the index just past the last body line of `heredocs` (an unterminated body runs to the end of the command).
function skipHeredocBodies(command: string, from: number, heredocs: Heredoc[]): number {
  let i = from;
  for (const { delimiter, stripTabs } of heredocs) {
    while (i < command.length) {
      const newline = command.indexOf("\n", i);
      const lineEnd = newline === -1 ? command.length : newline;
      const line = command.slice(i, lineEnd).replace(/\r$/, "");
      i = newline === -1 ? command.length : newline + 1;
      if ((stripTabs ? line.replace(/^\t+/, "") : line) === delimiter) break;
    }
  }
  return i;
}

// Reads the command substitution that starts at `start` (`$(` or a backtick) inside double quotes. `inner` is its
// command text; `end` is the index of its last character (an unterminated one runs to the end of the command).
function readSubstitution(command: string, start: number): { inner: string; end: number } {
  if (command[start] === "`") {
    let i = start + 1;
    let inner = "";
    while (i < command.length && command[i] !== "`") {
      if (command[i] === "\\" && i + 1 < command.length) i++;
      inner += command[i] ?? "";
      i++;
    }
    return { inner, end: Math.min(i, command.length - 1) };
  }
  let depth = 1;
  let i = start + 2;
  for (; i < command.length; i++) {
    const c = command[i] ?? "";
    if (c === "\\") i++;
    else if (c === "'") {
      const close = command.indexOf("'", i + 1);
      i = close === -1 ? command.length : close;
    } else if (c === '"') {
      for (i++; i < command.length && command[i] !== '"'; i++) if (command[i] === "\\") i++;
    } else if (c === "(") depth++;
    else if (c === ")" && --depth === 0) break;
  }
  return { inner: command.slice(start + 2, i), end: Math.min(i, command.length - 1) };
}

// Splits a shell command into segments of words. Quotes and comments are honoured, so text that only mentions a
// command (`echo "gh pr merge"`, `# gh pr merge`) is not a command; `$(...)`, backticks, and operators start a segment, and a substitution inside double quotes is scanned too.
function splitSegments(command: string): string[][] {
  const segments: string[][] = [];
  let tokens: string[] = [];
  let word = "";
  let inWord = false;
  const endWord = () => {
    if (inWord) tokens.push(word);
    word = "";
    inWord = false;
  };
  const endSegment = () => {
    endWord();
    if (tokens.length > 0) segments.push(tokens);
    tokens = [];
  };
  const pendingHeredocs: Heredoc[] = [];
  const substitutions: string[] = [];
  for (let i = 0; i < command.length; i++) {
    const c = command[i] ?? "";
    if (c === "'") {
      inWord = true;
      const close = command.indexOf("'", i + 1);
      const stop = close === -1 ? command.length : close;
      word += command.slice(i + 1, stop);
      i = stop;
    } else if (c === '"') {
      inWord = true;
      i++;
      while (i < command.length && command[i] !== '"') {
        if (command[i] === "\\" && i + 1 < command.length) {
          i++;
        } else if (command[i] === "`" || (command[i] === "$" && command[i + 1] === "(")) {
          const { inner, end } = readSubstitution(command, i);
          substitutions.push(inner);
          word += command.slice(i, end + 1);
          i = end + 1;
          continue;
        }
        word += command[i] ?? "";
        i++;
      }
    } else if (c === "\\") {
      inWord = true;
      i++;
      if (command[i] !== "\n") word += command[i] ?? "";
    } else if (c === "#" && !inWord) {
      while (i + 1 < command.length && command[i + 1] !== "\n") i++;
    } else if (c === "<" && command[i + 1] === "<" && command[i + 2] !== "<" && command[i - 1] !== "<") {
      endWord();
      const heredoc = readHeredocOperator(command, i);
      pendingHeredocs.push(heredoc);
      i = heredoc.end - 1;
    } else if (c === "\n" && pendingHeredocs.length > 0) {
      endSegment();
      i = skipHeredocBodies(command, i + 1, pendingHeredocs.splice(0)) - 1;
    } else if (c === "&" && (command[i - 1] === ">" || command[i - 1] === "<" || command[i + 1] === ">")) {
      inWord = true;
      word += c;
    } else if (c === "\n" || c === ";" || c === "|" || c === "&" || c === "(" || c === ")" || c === "`") {
      endSegment();
    } else if (/\s/.test(c)) {
      endWord();
    } else {
      inWord = true;
      word += c;
    }
  }
  endSegment();
  for (const inner of substitutions) segments.push(...splitSegments(inner));
  return segments;
}

// Drops redirections (`2>&1`, `> file`, `<<EOF`) so a file name is never read as an argument.
function withoutRedirections(tokens: string[]): string[] {
  const kept: string[] = [];
  for (let i = 0; i < tokens.length; i++) {
    const token = tokens[i] ?? "";
    if (BARE_REDIRECTION.test(token)) i++;
    else if (!REDIRECTION.test(token)) kept.push(token);
  }
  return kept;
}

type ParsedArgs = { positionals: string[]; flags: Map<string, string> };

function parseArgs(args: string[], valueFlags: Set<string>): ParsedArgs {
  const positionals: string[] = [];
  const flags = new Map<string, string>();
  for (let i = 0; i < args.length; i++) {
    const arg = args[i] ?? "";
    if (arg === "--") {
      positionals.push(...args.slice(i + 1));
      break;
    }
    if (arg.startsWith("--")) {
      const eq = arg.indexOf("=");
      const name = eq === -1 ? arg : arg.slice(0, eq);
      if (eq !== -1) flags.set(name, arg.slice(eq + 1));
      else if (valueFlags.has(name)) flags.set(name, args[++i] ?? "");
      else flags.set(name, "");
    } else if (arg.startsWith("-") && arg.length > 1) {
      const name = arg.slice(0, 2);
      if (!valueFlags.has(name)) flags.set(name, "");
      else if (arg.length > 2) flags.set(name, arg.slice(2));
      else flags.set(name, args[++i] ?? "");
    } else {
      positionals.push(arg);
    }
  }
  return { positionals, flags };
}

const flagValue = (flags: Map<string, string>, ...names: string[]): string | undefined =>
  names.map((name) => flags.get(name)).find((value) => value !== undefined);

// `gh -R o/r issue close 1` and `gh issue -R o/r close 1` are valid: the repo flag may sit before the group or between
// group and action. Returns the first two non-flag words as group and action, the repo flag seen on the way, and the rest.
function splitSubcommand(words: string[]): { group?: string; action?: string; args: string[]; repo?: string } {
  const named: string[] = [];
  let repo: string | undefined;
  let i = 0;
  for (; i < words.length && named.length < 2; i++) {
    const word = words[i] ?? "";
    if (word === "-R" || word === "--repo") repo = words[++i] ?? "";
    else if (word.startsWith("--repo=")) repo = word.slice("--repo=".length);
    else if (word.startsWith("-R") && word.length > 2 && !word.startsWith("--")) repo = word.slice(2);
    else if (!word.startsWith("-")) named.push(word);
  }
  return { group: named[0], action: named[1], args: words.slice(i), repo: repo || undefined };
}

function targetsFromSegment(rawTokens: string[], depth: number): GhTarget[] {
  const tokens = withoutRedirections(rawTokens);
  let i = 0;
  let envRepo: string | undefined;
  while (i < tokens.length && (ENV_ASSIGNMENT.test(tokens[i] ?? "") || WRAPPERS.has(tokens[i] ?? "") || CONTROL_KEYWORDS.has(tokens[i] ?? ""))) {
    const token = tokens[i] ?? "";
    if (token.startsWith("GH_REPO=")) envRepo = token.slice("GH_REPO=".length) || undefined;
    i++;
  }
  const program = (tokens[i] ?? "").split("/").pop() ?? "";
  if (SHELLS.has(program)) {
    const flagAt = tokens.findIndex((token, index) => index > i && /^-[a-z]*c$/.test(token));
    const script = flagAt === -1 ? undefined : tokens[flagAt + 1];
    return script !== undefined && depth < 3 ? findGhTargets(script, depth + 1) : [];
  }
  if (program !== "gh") return [];
  const { group, action, args, repo: leadingRepo } = splitSubcommand(tokens.slice(i + 1));
  if (group === "issue" && action === "close") {
    const { positionals, flags } = parseArgs(args, ISSUE_CLOSE_VALUE_FLAGS);
    const reason = flagValue(flags, "-r", "--reason");
    if (flags.has("--duplicate-of") || (reason !== undefined && NOT_A_COMPLETION.test(reason))) return [];
    const repo = flagValue(flags, "-R", "--repo") ?? leadingRepo ?? envRepo;
    return positionals.map((arg) => ({ kind: "issue", arg, repo }));
  }
  if (group === "pr" && action === "merge") {
    const { positionals, flags } = parseArgs(args, PR_MERGE_VALUE_FLAGS);
    return [{ kind: "pr", arg: positionals[0], repo: flagValue(flags, "-R", "--repo") ?? leadingRepo ?? envRepo }];
  }
  return [];
}

// The completing `gh issue close` and `gh pr merge` calls in a command.
export function findGhTargets(command: string, depth = 0): GhTarget[] {
  const targets = splitSegments(command).flatMap((tokens) => targetsFromSegment(tokens, depth));
  // A substitution inside `bash -c "..."` is seen both in the outer command and in the script; check each target once.
  const seen = new Set<string>();
  return targets.filter((target) => {
    const key = JSON.stringify(target);
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

const SECTION_NAME =
  /(?:^|[^a-z0-9])(?:ac|dod|dor)(?![a-z0-9])|acceptance criteria|definition of (?:done|ready)|受け入れ基準|受入基準|受入条件|受け入れ条件|完了条件/i;
const HEADING = /^ {0,3}(#{1,6})\s+(.+?)\s*#*\s*$/;
const BOLD_LABEL = /^\s*(?:\*\*|__)(.+?)(?:\*\*|__)\s*[:：]?\s*$/;
const UNCHECKED_ITEM = /^\s*(?:[-*+]|\d+[.)])\s+\[ \](?:\s+(.*))?$/;
// An opening fence is 3+ backticks or tildes; it closes on a line of the same character, at least as long, and nothing else.
const FENCE = /^\s*(`{3,}|~{3,})(.*)$/;
// A bold label has no level: any heading ends its section.
const LABEL_LEVEL = 7;

// Unchecked `[ ]` items under an AC / DoR / DoD heading (until the next heading of the same or a higher level) or
// bold label (until the next heading or label). Unchecked boxes elsewhere, in code fences, or in HTML comments are not counted.
export function uncheckedItems(body: string): string[] {
  const items: string[] = [];
  let sectionLevel: number | undefined;
  let fence: string | undefined;
  for (const line of body.replace(/<!--[\s\S]*?-->/g, "").split(/\r?\n/)) {
    const marker = FENCE.exec(line);
    if (fence !== undefined) {
      if (marker !== null && (marker[1] ?? "")[0] === fence[0] && (marker[1] ?? "").length >= fence.length && (marker[2] ?? "").trim() === "") fence = undefined;
      continue;
    }
    if (marker !== null && !((marker[1] ?? "")[0] === "`" && (marker[2] ?? "").includes("`"))) {
      fence = marker[1];
      continue;
    }
    const heading = HEADING.exec(line);
    const label = heading === null ? BOLD_LABEL.exec(line) : null;
    if (heading !== null) {
      // An open section stays active through deeper headings, gated or not; only a heading of the same or a higher level ends it.
      const level = (heading[1] ?? "").length;
      if (sectionLevel !== undefined && level <= sectionLevel) sectionLevel = undefined;
      if (sectionLevel === undefined && SECTION_NAME.test(heading[2] ?? "")) sectionLevel = level;
    } else if (label !== null) {
      // A heading's section ends at a heading, so a bold sub-label inside it (`**User flow**`) neither ends nor narrows it.
      if (sectionLevel === undefined || sectionLevel === LABEL_LEVEL) sectionLevel = SECTION_NAME.test(label[1] ?? "") ? LABEL_LEVEL : undefined;
    } else if (sectionLevel !== undefined) {
      const item = UNCHECKED_ITEM.exec(line);
      if (item !== null) items.push((item[1] ?? "").trim() || "(empty item)");
    }
  }
  return items;
}

function defaultGh(args: string[], { cwd, timeoutMs = GH_TIMEOUT_MS }: GhCallOptions = {}): string {
  try {
    return execFileSync("gh", args, { cwd, encoding: "utf8", timeout: timeoutMs, stdio: ["ignore", "pipe", "pipe"] });
  } catch (error) {
    const failure = error as { code?: string; stderr?: unknown; message?: string };
    if (failure.code === "ENOENT") throw new Error("gh is not installed or not on PATH");
    if (failure.code === "ETIMEDOUT") throw new Error(`gh did not answer within ${Math.round(timeoutMs / 100) / 10}s`);
    const stderr = typeof failure.stderr === "string" ? failure.stderr.trim() : "";
    throw new Error(stderr || failure.message || "gh failed");
  }
}

type Finding = { source: string; items: string[] };
type Verdict = { findings: Finding[]; errors: string[] };

function readBody(gh: GhRunner, args: string[]): { body: string; json: Record<string, unknown> } {
  const json: unknown = JSON.parse(gh(args));
  if (typeof json !== "object" || json === null) throw new Error("gh returned JSON that is not an object");
  const { body } = json as { body?: unknown };
  if (typeof body !== "string") throw new Error("gh returned no body text");
  return { body, json: json as Record<string, unknown> };
}

const repoArgs = (repo: string | undefined): string[] => (repo === undefined ? [] : ["-R", repo]);

function checkTarget(target: GhTarget, gh: GhRunner): Verdict {
  const findings: Finding[] = [];
  const errors: string[] = [];
  const attempt = (source: string, work: () => void) => {
    try {
      work();
    } catch (error) {
      errors.push(`${source}: ${error instanceof Error ? error.message : String(error)}`);
    }
  };
  const readIssue = (source: string, args: string[]) =>
    attempt(source, () => {
      const items = uncheckedItems(readBody(gh, args).body);
      if (items.length > 0) findings.push({ source, items });
    });
  if (target.kind === "issue") {
    const arg = target.arg ?? "";
    readIssue(`issue ${arg}`, ["issue", "view", ...repoArgs(target.repo), "--json", "body", "--", arg]);
    return { findings, errors };
  }
  const source = `PR ${target.arg ?? "(current branch)"}`;
  attempt(source, () => {
    const { body, json } = readBody(gh, ["pr", "view", ...repoArgs(target.repo), "--json", "body,closingIssuesReferences", ...(target.arg === undefined ? [] : ["--", target.arg])]);
    const items = uncheckedItems(body);
    if (items.length > 0) findings.push({ source, items });
    const closing = json.closingIssuesReferences;
    if (!Array.isArray(closing)) throw new Error("gh returned no closingIssuesReferences list");
    for (const ref of closing as { number?: unknown; url?: unknown }[]) {
      const label = `issue #${String(ref.number ?? "?")} (closed by ${source})`;
      if (typeof ref.url === "string") readIssue(label, ["issue", "view", "--json", "body", "--", ref.url]);
      else if (typeof ref.number === "number") readIssue(label, ["issue", "view", ...repoArgs(target.repo), "--json", "body", "--", String(ref.number)]);
      else errors.push(`${label}: gh returned a closing issue with no number or url`);
    }
  });
  return { findings, errors };
}

function deny(reason: string): string {
  const output = {
    hookSpecificOutput: { hookEventName: "PreToolUse", permissionDecision: "deny", permissionDecisionReason: reason },
  };
  return `${JSON.stringify(output)}\n`;
}

const quote = (item: string): string => `"${item.length > ITEM_QUOTE_LIMIT ? `${item.slice(0, ITEM_QUOTE_LIMIT)}...` : item}"`;

function openItemsReason(findings: Finding[]): string[] {
  const listed = findings.flatMap(({ source, items }) => items.map((item) => `- ${source}: ${quote(item)}`));
  return [
    "Merge/close gate: this command closes an issue or merges a PR while AC / DoR / DoD items are still unchecked.",
    ...listed.slice(0, MAX_LISTED_ITEMS),
    ...(listed.length > MAX_LISTED_ITEMS ? [`...and ${listed.length - MAX_LISTED_ITEMS} more.`] : []),
    "Finish each item, record its evidence (one row per item with a file:line link, in the issue or PR comment), check the box, then retry. An item with no evidence row is not done.",
  ];
}

function failClosedReason(errors: string[]): string[] {
  return [
    "Merge/close gate could not judge whether every AC / DoR / DoD item is checked, so it fails closed:",
    ...errors.map((error) => `- ${error}`),
    "Fix the cause (gh installed and logged in, network, the issue or PR number) and retry.",
  ];
}

// Each gh call gets the directory to run in and min(per-call cap, time left); once the deadline has passed, a call is
// not made and its target counts as unread, which denies the command.
function withBudget(gh: GhRunner, cwd: string | undefined, now: () => number, deadline: number, budgetMs: number): GhRunner {
  return (args) => {
    const remaining = deadline - now();
    if (remaining <= 0) throw new Error(`the ${budgetMs / 1000}s overall time budget for reading issues and PRs ran out before this was read`);
    return gh(args, { cwd, timeoutMs: Math.min(GH_TIMEOUT_MS, remaining) });
  };
}

const existingDirectory = (path: unknown): string | undefined => {
  if (typeof path !== "string" || path === "") return undefined;
  try {
    return statSync(path).isDirectory() ? path : undefined;
  } catch {
    return undefined;
  }
};

export function run(input: unknown, { env = process.env, gh = defaultGh, now = Date.now, deadlineMs = OVERALL_DEADLINE_MS }: RunOptions = {}): string {
  if (typeof input !== "object" || input === null) return "";
  const hookInput = input as { hook_event_name?: unknown; tool_name?: unknown; tool_input?: unknown; cwd?: unknown };
  if (hookInput.hook_event_name !== undefined && hookInput.hook_event_name !== "PreToolUse") return "";
  if (hookInput.tool_name !== "Bash") return "";
  if (/^(off|0|false)$/i.test(env.OMO_MERGE_GATE ?? "")) return "";
  const toolInput = hookInput.tool_input;
  if (typeof toolInput !== "object" || toolInput === null) return "";
  const { command } = toolInput as { command?: unknown };
  if (typeof command !== "string" || !/\bgh\b/.test(command)) return "";
  const seen = new Set<string>();
  const targets = findGhTargets(command).filter((target) => {
    const key = JSON.stringify(target);
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
  const budgeted = withBudget(gh, existingDirectory(hookInput.cwd), now, now() + deadlineMs, deadlineMs);
  const verdicts = targets.map((target) => checkTarget(target, budgeted));
  const findings = verdicts.flatMap((verdict) => verdict.findings);
  const errors = verdicts.flatMap((verdict) => verdict.errors);
  if (findings.length === 0 && errors.length === 0) return "";
  return deny(
    [
      ...(findings.length > 0 ? openItemsReason(findings) : []),
      ...(errors.length > 0 ? failClosedReason(errors) : []),
      "Set OMO_MERGE_GATE=off to bypass this gate.",
    ].join("\n"),
  );
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
