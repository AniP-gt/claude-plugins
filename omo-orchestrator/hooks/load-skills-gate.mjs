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

// MODES label: the colon is required on a label line; only the uppercase `## MODES` heading takes its value from the next line.
const MODES_LABEL_PATTERN = /^MODES(?![A-Za-z0-9_])/i;
const MODES_COLON_PATTERN = /^[*_`]*\s*:[*_`\s]*/;
const MODES_HEADING_PATTERN = /^MODES[*_`\s]*$/;

const withoutPrefix = (name) => (name.startsWith(PLUGIN_PREFIX) ? name.slice(PLUGIN_PREFIX.length) : name);
// A listed name matches the catalog case-insensitively, without a leading slash or the plugin prefix.
const bareName = (name) => withoutPrefix(name.toLowerCase().replace(/^\/+/, ""));
// A skill name ends at the first `/` or `:`; what follows is a mode (`skill/mode`, `skill:mode`), not part of the skill.
const normalizeName = (name) => bareName(name).split(/[/:]/, 1)[0];

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

// Every LOAD_SKILLS label in the prompt, in order: `LOAD_SKILLS: [..]` / `LOAD_SKILLS: none` on one line, or a
// `## 0. LOAD_SKILLS` heading whose value is on the next non-empty line (a label line read that way is not listed again).
// Each entry is { line, value } where value is undefined when the text after the label is neither `none` nor `[..]`,
// or is `none` followed by more skill names. Lines are matched one at a time with single-pass patterns.
export function findAllLoadSkills(prompt) {
  const lines = prompt.split("\n").map((line) => line.trim());
  const found = [];
  for (let i = 0; i < lines.length; i += 1) {
    const lead = LEAD_PATTERN.exec(lines[i])[0];
    const rest = lines[i].slice(lead.length);
    if (!LABEL_PATTERN.test(rest)) continue;
    const labelLine = lines[i];
    let valueText = rest.slice("LOAD_SKILLS".length).replace(AFTER_LABEL_PATTERN, "");
    if (valueText === "" && lead.includes("#")) {
      let next = i + 1;
      while (next < lines.length && lines[next] === "") next += 1;
      const nextLine = lines[next] ?? "";
      const nextRest = nextLine.slice(LEAD_PATTERN.exec(nextLine)[0].length);
      // The next line may itself be the label line (`LOAD_SKILLS: [..]`); then its value follows its own label.
      if (LABEL_PATTERN.test(nextRest)) {
        valueText = nextRest.slice("LOAD_SKILLS".length).replace(AFTER_LABEL_PATTERN, "");
        i = next;
      } else {
        valueText = nextLine.replace(/^`+/, "");
      }
    }
    const cleaned = valueText.replace(/^`+/, "");
    const value = VALUE_PATTERN.exec(cleaned)?.[0];
    const isNoneWithNames = value !== undefined && !value.startsWith("[") && NONE_THEN_NAME_PATTERN.test(cleaned.slice(value.length));
    found.push({ line: labelLine, value: isNoneWithNames ? undefined : value });
  }
  return found;
}

// The first LOAD_SKILLS label decides the answer; undefined when the prompt has none.
export function findLoadSkills(prompt) {
  return findAllLoadSkills(prompt)[0];
}

// The accepted LOAD_SKILLS value of the prompt as a list of zero or one entries.
export function loadSkillsValues(prompt) {
  const found = findLoadSkills(prompt);
  return found?.value === undefined ? [] : [found.value];
}

// Names are split on commas, semicolons, and whitespace, so a list the controller writes without commas is still checked.
// Markdown emphasis and quote characters around an item are stripped, so `**omo-plan**` is still read as omo-plan.
function listItems(text) {
  return text
    .split(/[\s,;]+/)
    .map((item) => bareName(item.trim().replace(/^[*_`'"]+/, "").replace(/[*_`'"]+$/, "")))
    .filter((item) => item !== "");
}

// The skill of each LOAD_SKILLS item; a mode written after it (`omo-programming/debugging`) is cut off.
function skillNames(value) {
  if (!value.startsWith("[")) return [];
  return listItems(value.slice(1, -1))
    .map(normalizeName)
    .filter((item) => item !== "");
}

// Every `MODES:` entry in the prompt as { entry, parent }: `MODES: a/b, c/d` on one line (label case-insensitive, colon
// required, same lead-in tolerance as LOAD_SKILLS), or a `## MODES` heading whose value is on the next non-empty line.
// A MODES line asks a worker to load a mode of a skill, so its parent skill is held to the same Who rules as LOAD_SKILLS.
export function findModes(prompt) {
  const lines = prompt.split("\n").map((line) => line.trim());
  const found = [];
  for (let i = 0; i < lines.length; i += 1) {
    const lead = LEAD_PATTERN.exec(lines[i])[0];
    const rest = lines[i].slice(lead.length);
    if (!MODES_LABEL_PATTERN.test(rest)) continue;
    const afterLabel = rest.slice("MODES".length);
    let valueText;
    if (MODES_COLON_PATTERN.test(afterLabel)) {
      valueText = afterLabel.replace(MODES_COLON_PATTERN, "");
    } else if (lead.includes("#") && MODES_HEADING_PATTERN.test(rest)) {
      let next = i + 1;
      while (next < lines.length && lines[next] === "") next += 1;
      const nextLine = lines[next] ?? "";
      // A following heading or label line is not the value; a label line is read in its own turn of the loop.
      if (nextLine.startsWith("#") || MODES_LABEL_PATTERN.test(nextLine.slice(LEAD_PATTERN.exec(nextLine)[0].length))) continue;
      valueText = nextLine;
      i = next;
    } else {
      continue;
    }
    for (const entry of listItems(valueText.replace(/[[\]]/g, " "))) {
      const parent = normalizeName(entry);
      if (parent !== "") found.push({ entry, parent });
    }
  }
  return found;
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

// One reason line per source that has offenders: `LOAD_SKILLS names <what>: a, b.` and `MODES names <what>: c/d.`
const namedLines = (what, fromList, fromModes) =>
  [["LOAD_SKILLS", fromList], ["MODES", fromModes]]
    .filter(([, names]) => names.length > 0)
    .map(([label, names]) => `${label} names ${what}: ${names.join(", ")}.`);

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
  const all = findAllLoadSkills(toolInput.prompt);
  const found = all[0];
  if (found === undefined) return deny(MISSING_REASON);
  if (found.value === undefined) return deny(malformedReason(found.line));
  // The first label is the answer, but a worker may also act on a later one, so restricted names are checked on every readable label.
  const listed = all.flatMap((entry) => (entry.value === undefined ? [] : skillNames(entry.value)));
  // A MODES line loads a mode of its parent skill, so the parent is checked like a LOAD_SKILLS name; the entry is quoted as written.
  const modes = findModes(toolInput.prompt);
  const mainOnly = mainOnlySkills(catalogText);
  const named = [...new Set(listed.filter((name) => mainOnly.has(name)))];
  const namedModes = [...new Set(modes.filter(({ parent }) => mainOnly.has(parent)).map(({ entry }) => entry))];
  if (named.length > 0 || namedModes.length > 0) {
    return deny(
      [
        ...namedLines("main-only skill(s)", named, namedModes),
        "A main-only skill is a workflow the main context runs; a worker cannot dispatch further workers.",
        "Read skills/omo-orchestrate/references/skill-catalog.md, keep only worker and both rows, update `LOAD_SKILLS: [..]` and `MODES: ..` (or use `LOAD_SKILLS: none` and drop the MODES line), and resend.",
        "Never name a main-only skill. Set OMO_LOAD_SKILLS_GATE=off to disable this gate.",
      ].join("\n"),
    );
  }
  if (!READ_ONLY_WORKERS.has(withoutPrefix(toolInput.subagent_type))) return "";
  const implementerOnly = implementerOnlySkills(catalogText);
  const restricted = [...new Set(listed.filter((name) => implementerOnly.has(name)))];
  const restrictedModes = [...new Set(modes.filter(({ parent }) => implementerOnly.has(parent)).map(({ entry }) => entry))];
  if (restricted.length === 0 && restrictedModes.length === 0) return "";
  return deny(
    [
      ...namedLines("skill(s) that are for omo-implementer only", restricted, restrictedModes),
      "The catalog marks them `omo-implementer only` because they pre-approve unrestricted Bash or a launcher, and a skill's allowed-tools applies inside the sub-agent that loads it.",
      "Remove them from `LOAD_SKILLS: [..]` and `MODES: ..` for omo-researcher, omo-reviewer, and omo-planner (or use `LOAD_SKILLS: none`), or dispatch the work to omo-implementer, and resend.",
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
