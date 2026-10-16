#!/usr/bin/env node
// PreToolUse hook (matcher Agent|Task): a dispatch to an omo worker agent must carry a LOAD_SKILLS line, so the
// controller decides on every dispatch which skills the worker loads. Without the hook the decision is a
// prose rule that a controller skips under load, and the worker then runs without the skill that fits its task.
// A dispatch with no LOAD_SKILLS line is denied with the way to answer; a LOAD_SKILLS list that names a
// main-only skill is denied too, because a worker cannot run a workflow that dispatches further workers.
// A skill whose catalog When cell says `omo-implementer only` pre-approves unrestricted Bash or a launcher, and a
// skill's allowed-tools applies inside the sub-agent that loads it, so naming it for a read-only worker is denied too.
// Both sets are read from the skill catalog table at runtime, so the catalog stays the single source.
// The hook fails open: malformed input or an unreadable catalog never blocks a dispatch.
// OMO_LOAD_SKILLS_GATE=off|0|false disables it.
// The gate is a routing check that makes the controller decide, not a security boundary.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const CATALOG_PATH = fileURLToPath(new URL("../skills/omo-orchestrate/references/skill-catalog.md", import.meta.url));
const PLUGIN_PREFIX = "omo-orchestrator:";
const READ_ONLY_WORKERS = new Set(["omo-researcher", "omo-reviewer", "omo-planner"]);
const GATED_WORKERS = new Set(["omo-implementer", "omo-researcher", "omo-reviewer", "omo-planner"]);
// Before the label: whitespace, heading hashes, quote marks, list markers (- * +), `N.` / `N)` numbers, emphasis and backticks.
const LEAD_PATTERN = /^(?:[\s#>*+\-_`]|\d{1,3}[.)])*/;
const LABEL_PATTERN = /^LOAD_SKILLS(?![A-Za-z0-9_])/i;
// After the label: emphasis and backticks around it, then an optional colon, then emphasis and spaces before the value.
const AFTER_LABEL_PATTERN = /^[*_`]*\s*:?[*_`\s]*/;
// The value is `none` or `[..]` at the start of the value text; whatever follows it is a note and ignored.
const VALUE_PATTERN = /^(?:none(?![A-Za-z0-9_])|\[[^\]]*\])/i;
// `none` followed by a list separator (comma, semicolon, space) and a skill name is a list written without brackets, not none.
const NONE_THEN_NAME_PATTERN = /^[`*_]*[\s,;]+[`*_'"/]*(?:omo-orchestrator:)?omo-/i;
const LINE_QUOTE_LIMIT = 120;
const MAIN_ONLY_ROW = /^\|\s*`([^`\s|]+)`\s*\|\s*main-only\s*\|/;
const SKILL_ROW = /^\|\s*`([^`\s|]+)`\s*\|[^|]*\|([^|]*)\|/;
const IMPLEMENTER_ONLY_MARKER = "omo-implementer only";

const withoutPrefix = (name) => (name.startsWith(PLUGIN_PREFIX) ? name.slice(PLUGIN_PREFIX.length) : name);
// A listed name matches the catalog case-insensitively, without a leading slash or the plugin prefix.
const normalizeName = (name) => withoutPrefix(name.toLowerCase().replace(/^\/+/, ""));

export function mainOnlySkills(catalogText) {
  const names = new Set();
  for (const line of catalogText.split("\n")) {
    const match = MAIN_ONLY_ROW.exec(line.trim());
    if (match) names.add(normalizeName(match[1]));
  }
  return names;
}

export function implementerOnlySkills(catalogText) {
  const names = new Set();
  for (const line of catalogText.split("\n")) {
    const match = SKILL_ROW.exec(line.trim());
    if (match && match[2].includes(IMPLEMENTER_ONLY_MARKER)) names.add(normalizeName(match[1]));
  }
  return names;
}

// The first line of the prompt that carries the LOAD_SKILLS label decides: `LOAD_SKILLS: [..]` /
// `LOAD_SKILLS: none` on one line, or a `## 0. LOAD_SKILLS` heading whose value is on the next non-empty line.
// Returns undefined when no line carries the label, otherwise { line, value } where value is undefined when the
// text after the label is neither `none` nor `[..]`, or is `none` followed by more skill names. Lines are matched one at a time with single-pass patterns.
export function findLoadSkills(prompt) {
  const lines = prompt.split("\n").map((line) => line.trim());
  for (let i = 0; i < lines.length; i += 1) {
    const lead = LEAD_PATTERN.exec(lines[i])[0];
    const rest = lines[i].slice(lead.length);
    if (!LABEL_PATTERN.test(rest)) continue;
    let valueText = rest.slice("LOAD_SKILLS".length).replace(AFTER_LABEL_PATTERN, "");
    if (valueText === "" && lead.includes("#")) {
      let next = i + 1;
      while (next < lines.length && lines[next] === "") next += 1;
      const nextLine = lines[next] ?? "";
      const nextRest = nextLine.slice(LEAD_PATTERN.exec(nextLine)[0].length);
      // The next line may itself be the label line (`LOAD_SKILLS: [..]`); then its value follows its own label.
      valueText = LABEL_PATTERN.test(nextRest)
        ? nextRest.slice("LOAD_SKILLS".length).replace(AFTER_LABEL_PATTERN, "")
        : nextLine.replace(/^`+/, "");
    }
    const cleaned = valueText.replace(/^`+/, "");
    const value = VALUE_PATTERN.exec(cleaned)?.[0];
    const isNoneWithNames = value !== undefined && !value.startsWith("[") && NONE_THEN_NAME_PATTERN.test(cleaned.slice(value.length));
    return { line: lines[i], value: isNoneWithNames ? undefined : value };
  }
  return undefined;
}

// The accepted LOAD_SKILLS value of the prompt as a list of zero or one entries.
export function loadSkillsValues(prompt) {
  const found = findLoadSkills(prompt);
  return found?.value === undefined ? [] : [found.value];
}

// Names are split on commas, semicolons, and whitespace, so a list the controller writes without commas is still checked.
// Markdown emphasis and quote characters around an item are stripped, so `**omo-plan**` is still read as omo-plan.
function skillNames(value) {
  if (!value.startsWith("[")) return [];
  return value
    .slice(1, -1)
    .split(/[\s,;]+/)
    .map((item) => normalizeName(item.trim().replace(/^[*_`'"]+/, "").replace(/[*_`'"]+$/, "")))
    .filter((item) => item !== "");
}

function deny(reason) {
  const output = {
    hookSpecificOutput: { hookEventName: "PreToolUse", permissionDecision: "deny", permissionDecisionReason: reason },
  };
  return `${JSON.stringify(output)}\n`;
}

const MISSING_REASON = [
  "This dispatch to an omo worker has no LOAD_SKILLS line.",
  "Read skills/omo-orchestrate/references/skill-catalog.md in the omo-orchestrator plugin and evaluate every row against this dispatch.",
  "Then add `LOAD_SKILLS: [skill-a, skill-b]` (or `LOAD_SKILLS: none` when no row applies) to the prompt and resend.",
  "Never name a main-only skill. Set OMO_LOAD_SKILLS_GATE=off to disable this gate.",
].join("\n");

function malformedReason(line) {
  const quoted = line.length > LINE_QUOTE_LIMIT ? `${line.slice(0, LINE_QUOTE_LIMIT)}...` : line;
  return [
    `This dispatch to an omo worker has a LOAD_SKILLS line whose value is not readable: ${quoted}`,
    "The value must start with `none` or a bracketed list: `LOAD_SKILLS: none` or `LOAD_SKILLS: [skill-a, skill-b]`. Text after the value is ignored.",
    "Fix that line (a bare name without brackets is not accepted) and resend. Read skills/omo-orchestrate/references/skill-catalog.md in the omo-orchestrator plugin to choose the names.",
    "Never name a main-only skill. Set OMO_LOAD_SKILLS_GATE=off to disable this gate.",
  ].join("\n");
}

export function run(input, { env = process.env, catalogText } = {}) {
  if (typeof input !== "object" || input === null) return "";
  if (input.hook_event_name !== undefined && input.hook_event_name !== "PreToolUse") return "";
  if (input.tool_name !== "Agent" && input.tool_name !== "Task") return "";
  if (/^(off|0|false)$/i.test(env.OMO_LOAD_SKILLS_GATE ?? "")) return "";
  const toolInput = input.tool_input;
  if (typeof toolInput !== "object" || toolInput === null) return "";
  if (typeof toolInput.subagent_type !== "string" || typeof toolInput.prompt !== "string") return "";
  if (!GATED_WORKERS.has(withoutPrefix(toolInput.subagent_type))) return "";
  if (typeof catalogText !== "string") return "";
  const found = findLoadSkills(toolInput.prompt);
  if (found === undefined) return deny(MISSING_REASON);
  if (found.value === undefined) return deny(malformedReason(found.line));
  const mainOnly = mainOnlySkills(catalogText);
  const named = [...new Set(skillNames(found.value).filter((name) => mainOnly.has(name)))];
  if (named.length > 0) {
    return deny(
      [
        `LOAD_SKILLS names main-only skill(s): ${named.join(", ")}.`,
        "A main-only skill is a workflow the main context runs; a worker cannot dispatch further workers.",
        "Read skills/omo-orchestrate/references/skill-catalog.md, keep only worker and both rows, update `LOAD_SKILLS: [..]` (or use `LOAD_SKILLS: none`), and resend.",
        "Never name a main-only skill. Set OMO_LOAD_SKILLS_GATE=off to disable this gate.",
      ].join("\n"),
    );
  }
  if (!READ_ONLY_WORKERS.has(withoutPrefix(toolInput.subagent_type))) return "";
  const implementerOnly = implementerOnlySkills(catalogText);
  const restricted = [...new Set(skillNames(found.value).filter((name) => implementerOnly.has(name)))];
  if (restricted.length === 0) return "";
  return deny(
    [
      `LOAD_SKILLS names skill(s) that are for omo-implementer only: ${restricted.join(", ")}.`,
      "The catalog marks them `omo-implementer only` because they pre-approve unrestricted Bash or a launcher, and a skill's allowed-tools applies inside the sub-agent that loads it.",
      "Remove them from `LOAD_SKILLS: [..]` for omo-researcher, omo-reviewer, and omo-planner (or use `LOAD_SKILLS: none`), or dispatch the work to omo-implementer, and resend.",
      "Set OMO_LOAD_SKILLS_GATE=off to disable this gate.",
    ].join("\n"),
  );
}

function readCatalog() {
  try {
    return readFileSync(CATALOG_PATH, "utf8");
  } catch {
    return undefined;
  }
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
  const output = run(parsed, { catalogText: readCatalog() });
  if (output.length > 0) process.stdout.write(output);
}
