// Run: node --test omo-orchestrator/hooks/load-skills-gate.test.mjs
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { test } from "node:test";
import { implementerOnlySkills, mainOnlySkills, run } from "./load-skills-gate.mjs";

const CATALOG = [
  "| Skill | Who | When |",
  "|---|---|---|",
  "| `omo-ralph-loop` | main-only | goal loop |",
  "| `omo-plan` | main-only | plan first |",
  "| `omo-review` | main-only | review local changes |",
  "| `omo-test-design` | worker | test design |",
  "| `omo-ast-grep` | both | structural search |",
  "| `omo-programming` | both | `omo-implementer only` (unrestricted Bash): a crash needs a root cause |",
  "| `omo-handoff` | worker | omo-implementer only (launcher): append to the ledger |",
  "| `omo-frontend` | both | omo-implementer only: pages and components |",
].join("\n");

const dispatch = (prompt, subagentType = "omo-orchestrator:omo-implementer", tool = "Agent") => ({
  hook_event_name: "PreToolUse",
  tool_name: tool,
  tool_input: { subagent_type: subagentType, prompt },
});
const gate = (input, env = {}) => run(input, { env, catalogText: CATALOG });
const decision = (output) => JSON.parse(output).hookSpecificOutput;

test("a gated worker dispatch without LOAD_SKILLS is denied with the catalog instructions", () => {
  const output = gate(dispatch("do x"));
  assert.ok(output.endsWith("\n"));
  const hook = decision(output);
  assert.equal(hook.hookEventName, "PreToolUse");
  assert.equal(hook.permissionDecision, "deny");
  assert.match(hook.permissionDecisionReason, /skills\/omo-orchestrate\/references\/skill-catalog\.md/);
  assert.match(hook.permissionDecisionReason, /LOAD_SKILLS: none/);
  assert.match(hook.permissionDecisionReason, /main-only/);
  assert.match(hook.permissionDecisionReason, /OMO_LOAD_SKILLS_GATE=off/);
});

test("LOAD_SKILLS: none is an answer and passes", () => {
  assert.equal(gate(dispatch("# Task\nLOAD_SKILLS: none\ndo x")), "");
});

test("a LOAD_SKILLS list of worker and both skills passes, with or without the plugin prefix", () => {
  assert.equal(gate(dispatch("LOAD_SKILLS: [omo-test-design]\ndo x")), "");
  assert.equal(gate(dispatch("LOAD_SKILLS: [omo-orchestrator:omo-test-design, `omo-ast-grep`]")), "");
  assert.equal(gate(dispatch("LOAD_SKILLS: []")), "");
});

test("a `## 0. LOAD_SKILLS` heading with the value on the next line passes", () => {
  assert.equal(gate(dispatch("## 0. LOAD_SKILLS\n\n[omo-ast-grep]\n\n## 1. Task\ndo x")), "");
  assert.equal(gate(dispatch("## 0. LOAD_SKILLS\nnone\n## 1. Task")), "");
  assert.equal(gate(dispatch("## 0. LOAD_SKILLS: none\n## 1. Task")), "");
});

test("a heading followed by a LOAD_SKILLS label line reads the value from that line", () => {
  for (const prompt of [
    "## 0. LOAD_SKILLS\nLOAD_SKILLS: [omo-test-design, omo-ast-grep]\n## 1. Task",
    "## LOAD_SKILLS\n\nLOAD_SKILLS: none\n## Task",
    "## 0. LOAD_SKILLS\n- **LOAD_SKILLS**: none",
  ]) {
    assert.equal(gate(dispatch(prompt)), "", prompt);
  }
  const mainOnly = decision(gate(dispatch("## 0. LOAD_SKILLS\nLOAD_SKILLS: [omo-ralph-loop]\n## 1. Task")));
  assert.equal(mainOnly.permissionDecision, "deny");
  assert.match(mainOnly.permissionDecisionReason, /main-only skill/);
  assert.match(mainOnly.permissionDecisionReason, /omo-ralph-loop/);
  assert.equal(decision(gate(dispatch("## 0. LOAD_SKILLS\nLOAD_SKILLS: omo-ast-grep"))).permissionDecision, "deny");
  assert.equal(decision(gate(dispatch("## 0. LOAD_SKILLS\nLOAD_SKILLS:\n[omo-ast-grep]"))).permissionDecision, "deny");
});

test("a heading without a value, or with a non-list value, is denied", () => {
  assert.equal(decision(gate(dispatch("## 0. LOAD_SKILLS\n## 1. Task\n[omo-ast-grep]"))).permissionDecision, "deny");
  assert.equal(decision(gate(dispatch("LOAD_SKILLS: omo-ast-grep"))).permissionDecision, "deny");
});

const readTemplate = (relativePath) => readFileSync(fileURLToPath(new URL(relativePath, import.meta.url)), "utf8");

test("LOAD_SKILLS lines as controllers write them pass: template note, list marker, number, emphasis, backticks, period", () => {
  for (const prompt of [
    "LOAD_SKILLS: [omo-test-design, omo-ast-grep]   (or LOAD_SKILLS: none ...)",
    "- LOAD_SKILLS: none",
    "* LOAD_SKILLS: none",
    "9. LOAD_SKILLS: none",
    "9) LOAD_SKILLS: none",
    "6. **LOAD_SKILLS**: none",
    "**LOAD_SKILLS:** none",
    "`LOAD_SKILLS: none`",
    "LOAD_SKILLS: `none`",
    "LOAD_SKILLS: none.",
    "load_skills: NONE",
    "## 0. LOAD_SKILLS: [omo-ast-grep] # why",
  ]) {
    assert.equal(gate(dispatch(`# Task\n${prompt}\ndo x`)), "", prompt);
  }
});

test("`none` followed by more skill names is malformed, not an answer of none", () => {
  for (const value of ["none, omo-plan", "none; omo-plan", "none omo-plan", "none,omo-plan", "`none`, omo-plan", "none, omo-orchestrator:omo-plan"]) {
    const hook = decision(gate(dispatch(`LOAD_SKILLS: ${value}\ndo x`)));
    assert.equal(hook.permissionDecision, "deny", value);
    assert.match(hook.permissionDecisionReason, /value is not readable/, value);
  }
  for (const value of ["none", "none.", "none   (note in parentheses)", "`none`", "none (omo-plan was considered)", "none - no row applies"]) {
    assert.equal(gate(dispatch(`LOAD_SKILLS: ${value}\ndo x`)), "", value);
  }
});

test("only the first LOAD_SKILLS line counts as the answer", () => {
  assert.equal(gate(dispatch("LOAD_SKILLS: none\n\nPasted brief:\nLOAD_SKILLS: [omo-research]")), "");
  assert.equal(gate(dispatch("LOAD_SKILLS: none\n\nPasted brief:\nLOAD_SKILLS: omo-test-design")), "");
  assert.equal(decision(gate(dispatch("LOAD_SKILLS: [omo-ralph-loop]\nLOAD_SKILLS: none"))).permissionDecision, "deny");
});

test("a restricted skill on a later LOAD_SKILLS line is denied too", () => {
  const mainOnly = decision(gate(dispatch("LOAD_SKILLS: none\ndo x\nLOAD_SKILLS: [omo-ralph-loop]")));
  assert.equal(mainOnly.permissionDecision, "deny");
  assert.match(mainOnly.permissionDecisionReason, /main-only skill/);
  assert.match(mainOnly.permissionDecisionReason, /omo-ralph-loop/);
  const implementerOnly = decision(
    gate(dispatch("LOAD_SKILLS: [omo-ast-grep]\n## 0. LOAD_SKILLS\n[omo-programming]", "omo-reviewer")),
  );
  assert.equal(implementerOnly.permissionDecision, "deny");
  assert.match(implementerOnly.permissionDecisionReason, /omo-programming/);
  assert.equal(gate(dispatch("LOAD_SKILLS: none\nLOAD_SKILLS: [omo-programming]")), "");
  assert.equal(gate(dispatch("LOAD_SKILLS: [omo-ast-grep]\nLOAD_SKILLS: [omo-test-design]", "omo-reviewer")), "");
});

test("a LOAD_SKILLS line with a malformed value is denied with its own reason that quotes the line", () => {
  const hook = decision(gate(dispatch("intro\n- LOAD_SKILLS: omo-test-design\ndo x")));
  assert.equal(hook.permissionDecision, "deny");
  assert.match(hook.permissionDecisionReason, /LOAD_SKILLS: omo-test-design/);
  assert.match(hook.permissionDecisionReason, /LOAD_SKILLS: none/);
  assert.match(hook.permissionDecisionReason, /LOAD_SKILLS: \[skill-a, skill-b\]/);
  assert.doesNotMatch(hook.permissionDecisionReason, /has no LOAD_SKILLS line/);
  const empty = decision(gate(dispatch("LOAD_SKILLS:\ndo x")));
  assert.equal(empty.permissionDecision, "deny");
  assert.doesNotMatch(empty.permissionDecisionReason, /has no LOAD_SKILLS line/);
  const word = decision(gate(dispatch("LOAD_SKILLS: nonexistent")));
  assert.equal(word.permissionDecision, "deny");
  assert.doesNotMatch(word.permissionDecisionReason, /has no LOAD_SKILLS line/);
});

test("the quoted offending line is truncated", () => {
  const hook = decision(gate(dispatch(`LOAD_SKILLS: ${"x".repeat(500)}`)));
  assert.ok(hook.permissionDecisionReason.length < 900, String(hook.permissionDecisionReason.length));
  assert.doesNotMatch(hook.permissionDecisionReason, /x{200}/);
});

test("a prose mention of LOAD_SKILLS in the middle of a line is not a label", () => {
  const hook = decision(gate(dispatch("Every dispatch carries a LOAD_SKILLS line.\ndo x")));
  assert.match(hook.permissionDecisionReason, /has no LOAD_SKILLS line/);
});

test("main-only names are matched case-insensitively and with a leading slash", () => {
  for (const list of ["[OMO-RALPH-LOOP]", "[/omo-ralph-loop]", "[/omo-orchestrator:omo-ralph-loop]", "[OMO-Orchestrator:OMO-Plan]"]) {
    const hook = decision(gate(dispatch(`LOAD_SKILLS: ${list}`)));
    assert.equal(hook.permissionDecision, "deny", list);
    assert.match(hook.permissionDecisionReason, /main-only skill/, list);
  }
  assert.equal(gate(dispatch("LOAD_SKILLS: [/OMO-Test-Design]")), "");
});

test("the LOAD_SKILLS template lines shipped in the briefs pass the gate", () => {
  for (const path of [
    "../skills/omo-orchestrate/references/delegation-prompt.md",
    "../skills/omo-frontend/references/implementer-brief.md",
  ]) {
    const lines = readTemplate(path)
      .split("\n")
      .filter((line) => /^LOAD_SKILLS:/.test(line));
    assert.ok(lines.length > 0, `${path} has no template line`);
    for (const line of lines) {
      // A template placeholder such as `{per lane}` is not an answer; only concrete lines are checked.
      if (/\{[^}]*\}/.test(line)) continue;
      assert.equal(gate(dispatch(line)), "", `${path}: ${line}`);
    }
  }
});

test("the whole fenced template block of each brief passes the gate", () => {
  for (const path of [
    "../skills/omo-orchestrate/references/delegation-prompt.md",
    "../skills/omo-frontend/references/implementer-brief.md",
  ]) {
    const block = /```markdown\n([\s\S]*?)\n```/.exec(readTemplate(path))?.[1];
    assert.ok(block, `${path} has no markdown template block`);
    assert.equal(gate(dispatch(block)), "", path);
  }
});

test("a main-only skill in LOAD_SKILLS is denied by name, with or without the prefix", () => {
  const bare = decision(gate(dispatch("LOAD_SKILLS: [omo-ralph-loop]")));
  assert.equal(bare.permissionDecision, "deny");
  assert.match(bare.permissionDecisionReason, /omo-ralph-loop/);
  const prefixed = decision(gate(dispatch("LOAD_SKILLS: [omo-test-design, omo-orchestrator:omo-plan]")));
  assert.equal(prefixed.permissionDecision, "deny");
  assert.match(prefixed.permissionDecisionReason, /omo-plan/);
  assert.doesNotMatch(prefixed.permissionDecisionReason, /omo-ralph-loop/);
});

test("LOAD_SKILLS names separated by spaces or semicolons are each checked", () => {
  for (const list of [
    "[omo-test-design omo-plan]",
    "[omo-test-design; omo-plan]",
    "[omo-test-design;omo-plan]",
    "[omo-test-design,\n omo-plan]",
    "[omo-test-design , ; omo-plan]",
  ]) {
    const hook = decision(gate(dispatch(`LOAD_SKILLS: ${list.replace("\n", " ")}`)));
    assert.equal(hook.permissionDecision, "deny", list);
    assert.match(hook.permissionDecisionReason, /omo-plan/, list);
    assert.doesNotMatch(hook.permissionDecisionReason, /main-only skill\(s\): omo-test-design/, list);
  }
  assert.equal(gate(dispatch("LOAD_SKILLS: [omo-test-design omo-ast-grep]")), "");
  assert.equal(gate(dispatch("LOAD_SKILLS: [omo-test-design; omo-ast-grep]")), "");
});

test("Markdown emphasis or quotes around a listed name do not hide it", () => {
  for (const list of ["[**omo-plan**]", "[_omo-plan_]", "[`omo-plan`]", "[*omo-plan*, 'omo-test-design']", '["omo-plan"]']) {
    const hook = decision(gate(dispatch(`LOAD_SKILLS: ${list}`)));
    assert.equal(hook.permissionDecision, "deny", list);
    assert.match(hook.permissionDecisionReason, /main-only skill\(s\): omo-plan/, list);
  }
  assert.equal(gate(dispatch("LOAD_SKILLS: [**omo-ast-grep**]")), "");
  assert.equal(gate(dispatch("LOAD_SKILLS: [_omo-ast-grep_, `omo-test-design`]")), "");
});

test("every gated worker, with or without the prefix, is checked", () => {
  for (const name of ["omo-implementer", "omo-researcher", "omo-reviewer", "omo-planner"]) {
    assert.equal(decision(gate(dispatch("do x", name))).permissionDecision, "deny", name);
    assert.equal(decision(gate(dispatch("do x", `omo-orchestrator:${name}`))).permissionDecision, "deny", name);
    assert.equal(gate(dispatch("LOAD_SKILLS: none", name)), "", name);
  }
  assert.equal(decision(gate(dispatch("do x", "omo-reviewer", "Task"))).permissionDecision, "deny");
});

test("other agents are not gated", () => {
  for (const name of [
    "general-purpose",
    "Explore",
    "omo-orchestrator:omo-oracle",
    "omo-orchestrator:omo-librarian",
    "omo-orchestrator:omo-media-reader",
    "omo-orchestrator:omo-plan-consultant",
    "omo-orchestrator:omo-plan-reviewer",
    "omo-orchestrator:omo-external-reviewer",
    "omo-orchestrator:omo-coordinator",
    "other-plugin:omo-implementer",
    "omo-implementer-extra",
  ]) {
    assert.equal(gate(dispatch("do x", name)), "", name);
  }
});

test("the gate is off for OMO_LOAD_SKILLS_GATE off, 0, or false", () => {
  for (const value of ["off", "0", "false", "OFF"]) {
    assert.equal(gate(dispatch("do x"), { OMO_LOAD_SKILLS_GATE: value }), "", value);
  }
  assert.notEqual(gate(dispatch("do x"), { OMO_LOAD_SKILLS_GATE: "on" }), "");
});

test("malformed input, other events, other tools, and an unreadable catalog produce no output", () => {
  for (const input of [undefined, null, "x", 3, {}, { tool_name: "Agent" }, { tool_name: "Agent", tool_input: "x" }]) {
    assert.equal(gate(input), "");
  }
  assert.equal(gate({ ...dispatch("do x"), tool_input: { subagent_type: "omo-implementer" } }), "");
  assert.equal(gate(dispatch("do x", "omo-implementer", "Bash")), "");
  assert.equal(gate({ ...dispatch("do x"), hook_event_name: "PostToolUse" }), "");
  assert.equal(run(dispatch("do x"), { env: {}, catalogText: undefined }), "");
});

test("a missing hook_event_name is treated as PreToolUse", () => {
  const { hook_event_name: _omit, ...input } = dispatch("do x");
  assert.equal(decision(gate(input)).permissionDecision, "deny");
});

test("only table rows marked main-only are parsed from the catalog", () => {
  assert.deepEqual([...mainOnlySkills(CATALOG)].sort(), ["omo-plan", "omo-ralph-loop", "omo-review"]);
  assert.equal(mainOnlySkills("prose mentioning `omo-x` main-only\n").size, 0);
});

test("pathological prompts are scanned in linear time", () => {
  const started = Date.now();
  gate(dispatch(`${" ".repeat(200000)}\nLOAD_SKILLS:${" ".repeat(200000)}x`));
  gate(dispatch("LOAD_SKILLS: [".repeat(20000)));
  gate(dispatch(`${"- ".repeat(50000)}LOAD_SKILLS: none`));
  gate(dispatch(`${"9. ".repeat(33000)}LOAD_SKILLS: none`));
  gate(dispatch(`${"**".repeat(50000)}LOAD_SKILLS${"`".repeat(50000)}x`));
  gate(dispatch(`LOAD_SKILLS: [${"a,".repeat(50000)}`));
  gate(dispatch(`LOAD_SKILLS: [${"/OMO-orchestrator:a,".repeat(5000)}]`));
  gate(dispatch("LOAD_SKILLS: [omo-ast-grep]\n".repeat(50000)));
  gate(dispatch("## LOAD_SKILLS\n\n".repeat(50000)));
  gate(dispatch(`LOAD_SKILLS: none\n${"MODES: omo-research/x\n".repeat(50000)}`));
  gate(dispatch(`LOAD_SKILLS: none\n${"## MODES\n\n".repeat(50000)}`));
  gate(dispatch(`LOAD_SKILLS: none\nMODES: ${"a/b,".repeat(50000)}`));
  gate(dispatch(`LOAD_SKILLS: none\n${"**".repeat(50000)}MODES${"`".repeat(50000)}x`));
  assert.ok(Date.now() - started < 1000, `took ${Date.now() - started}ms`);
});

test("every main-only skill in the real catalog is a skill directory", (t) => {
  const catalogPath = fileURLToPath(new URL("../skills/omo-orchestrate/references/skill-catalog.md", import.meta.url));
  if (!existsSync(catalogPath)) {
    t.skip("skill-catalog.md does not exist yet");
    return;
  }
  const names = mainOnlySkills(readFileSync(catalogPath, "utf8"));
  assert.ok(names.size > 0, "no main-only rows parsed");
  for (const name of names) {
    assert.ok(existsSync(fileURLToPath(new URL(`../skills/${name}`, import.meta.url))), `${name} has no skills/ directory`);
  }
});

test("implementer-only rows are parsed from the When cell", () => {
  assert.deepEqual([...implementerOnlySkills(CATALOG)].sort(), ["omo-frontend", "omo-handoff", "omo-programming"]);
  assert.equal(implementerOnlySkills("prose `omo-x` omo-implementer only\n").size, 0);
});

test("an implementer-only skill sent to a read-only worker is denied by name, with or without the prefix", () => {
  const cases = [
    ["omo-researcher", "omo-programming"],
    ["omo-orchestrator:omo-researcher", "omo-programming"],
    ["omo-reviewer", "omo-handoff"],
    ["omo-orchestrator:omo-reviewer", "omo-orchestrator:omo-handoff"],
    ["omo-planner", "omo-frontend"],
    ["omo-orchestrator:omo-planner", "/OMO-Frontend"],
  ];
  for (const [worker, skill] of cases) {
    const hook = decision(gate(dispatch(`LOAD_SKILLS: [omo-ast-grep, ${skill}]`, worker)));
    assert.equal(hook.permissionDecision, "deny", `${worker} ${skill}`);
    assert.match(hook.permissionDecisionReason, new RegExp(skill.replace(/^.*:/, "").replace("/", ""), "i"));
    assert.match(hook.permissionDecisionReason, /omo-implementer only/);
    assert.doesNotMatch(hook.permissionDecisionReason, /omo-ast-grep/);
  }
});

test("an implementer-only skill passes for the implementer, and other skills pass for read-only workers", () => {
  assert.equal(gate(dispatch("LOAD_SKILLS: [omo-programming, omo-handoff]", "omo-implementer")), "");
  assert.equal(gate(dispatch("LOAD_SKILLS: [omo-programming]", "omo-orchestrator:omo-implementer")), "");
  assert.equal(gate(dispatch("LOAD_SKILLS: [omo-ast-grep]", "omo-researcher")), "");
  assert.equal(gate(dispatch("LOAD_SKILLS: [omo-test-design, omo-ast-grep]", "omo-orchestrator:omo-reviewer")), "");
  assert.equal(gate(dispatch("LOAD_SKILLS: none", "omo-planner")), "");
});

test("the implementer-only skills of the real catalog are exactly the three that pre-approve broad Bash", (t) => {
  const catalogPath = fileURLToPath(new URL("../skills/omo-orchestrate/references/skill-catalog.md", import.meta.url));
  if (!existsSync(catalogPath)) {
    t.skip("skill-catalog.md does not exist yet");
    return;
  }
  const names = implementerOnlySkills(readFileSync(catalogPath, "utf8"));
  assert.deepEqual([...names].sort(), ["omo-frontend", "omo-handoff", "omo-programming"]);
  for (const name of names) {
    assert.ok(existsSync(fileURLToPath(new URL(`../skills/${name}`, import.meta.url))), `${name} has no skills/ directory`);
  }
});

test("the main-only skills of the real catalog are exactly the ten workflows the main context runs", () => {
  const names = mainOnlySkills(readTemplate("../skills/omo-orchestrate/references/skill-catalog.md"));
  assert.deepEqual(
    [...names].sort(),
    [
      "omo-git-master",
      "omo-implement",
      "omo-init-deep",
      "omo-lsp-setup",
      "omo-orchestrate",
      "omo-plan",
      "omo-ralph-loop",
      "omo-review",
      "omo-ultrawork",
      "omo-work-with-pr",
    ],
  );
});

// The real catalog: research and visual-qa are `both` skills, so a read-only worker may load them and name their modes.
const realCatalog = readTemplate("../skills/omo-orchestrate/references/skill-catalog.md");
const realGate = (input) => run(input, { env: {}, catalogText: realCatalog });

test("a researcher may load omo-research and omo-visual-qa, and name a mode of omo-research", () => {
  assert.equal(realGate(dispatch("LOAD_SKILLS: none\nMODES: omo-research/security-research", "omo-researcher")), "");
  assert.equal(realGate(dispatch("LOAD_SKILLS: [omo-visual-qa]", "omo-researcher")), "");
  assert.equal(realGate(dispatch("LOAD_SKILLS: [omo-research]", "omo-researcher")), "");
});

test("a skill:mode or skill/mode in LOAD_SKILLS is checked by its parent skill", () => {
  for (const [name, reason] of [
    ["omo-programming:debugging", /omo-implementer only/],
    ["omo-programming/debugging", /omo-implementer only/],
    ["omo-orchestrator:omo-programming:debugging", /omo-implementer only/],
    ["omo-review/review-work", /main-only skill/],
  ]) {
    const hook = decision(gate(dispatch(`LOAD_SKILLS: [${name}]`, "omo-reviewer")));
    assert.equal(hook.permissionDecision, "deny", name);
    assert.match(hook.permissionDecisionReason, reason, name);
  }
  assert.equal(gate(dispatch("LOAD_SKILLS: [omo-programming:debugging]", "omo-implementer")), "");
  assert.equal(gate(dispatch("LOAD_SKILLS: [omo-ast-grep/x, omo-research:security-research]", "omo-reviewer")), "");
});

test("a MODES line naming a mode of an implementer-only skill is denied for a read-only worker", () => {
  for (const prompt of [
    "LOAD_SKILLS: [omo-research]\nMODES: omo-programming/debugging",
    "LOAD_SKILLS: none\nMODES: omo-programming/debugging",
    "LOAD_SKILLS: none\nMODES: [omo-programming/debugging]",
    "LOAD_SKILLS: none\nMODES: omo-programming:debugging",
    "LOAD_SKILLS: none\nmodes: omo-programming/debugging",
    "LOAD_SKILLS: none\n## MODES\nomo-programming/debugging",
    "LOAD_SKILLS: none\n## MODES\n\n- omo-programming/debugging",
    "LOAD_SKILLS: none\nMODES: omo-research/security-research\nsome text\nMODES: omo-programming/debugging",
    "LOAD_SKILLS: none\nMODES: `omo-orchestrator:omo-programming/debugging`",
    "LOAD_SKILLS: none\n- **MODES**: omo-programming/debugging",
    "LOAD_SKILLS: none\nMODES: omo-programming/debugging omo-research/security-research",
    "LOAD_SKILLS: none\nMODES: omo-research/security-research, omo-programming/debugging",
  ]) {
    for (const worker of ["omo-researcher", "omo-orchestrator:omo-reviewer", "omo-planner"]) {
      const hook = decision(gate(dispatch(prompt, worker)));
      assert.equal(hook.permissionDecision, "deny", `${worker}: ${prompt}`);
      assert.match(hook.permissionDecisionReason, /MODES names skill\(s\) that are for omo-implementer only: omo-programming(\/|:)debugging\./, prompt);
      assert.match(hook.permissionDecisionReason, /omo-implementer only/, prompt);
      assert.doesNotMatch(hook.permissionDecisionReason, /omo-research\//, prompt);
    }
  }
});

test("a MODES line naming a main-only skill is denied for every gated worker", () => {
  for (const worker of ["omo-implementer", "omo-researcher", "omo-reviewer", "omo-planner"]) {
    const hook = decision(gate(dispatch("LOAD_SKILLS: none\nMODES: omo-review/review-work", worker)));
    assert.equal(hook.permissionDecision, "deny", worker);
    assert.match(hook.permissionDecisionReason, /MODES names main-only skill\(s\): omo-review\/review-work\./, worker);
    assert.match(hook.permissionDecisionReason, /Never name a main-only skill/, worker);
  }
  const both = decision(gate(dispatch("LOAD_SKILLS: [omo-plan]\nMODES: omo-review/review-work")));
  assert.match(both.permissionDecisionReason, /LOAD_SKILLS names main-only skill\(s\): omo-plan\./);
  assert.match(both.permissionDecisionReason, /MODES names main-only skill\(s\): omo-review\/review-work\./);
});

test("a MODES line of an allowed parent, or one that is not a label, passes", () => {
  assert.equal(gate(dispatch("LOAD_SKILLS: none\nMODES: omo-programming/debugging", "omo-implementer")), "");
  assert.equal(gate(dispatch("LOAD_SKILLS: none\nMODES: omo-programming/debugging", "omo-orchestrator:omo-implementer")), "");
  assert.equal(gate(dispatch("LOAD_SKILLS: none\nMODES: omo-research/security-research, omo-ast-grep/x", "omo-reviewer")), "");
  // Without the colon a line is prose, and only the uppercase `## MODES` heading reads its value from the next line.
  assert.equal(gate(dispatch("LOAD_SKILLS: none\nMODES omo-programming/debugging", "omo-reviewer")), "");
  assert.equal(gate(dispatch("LOAD_SKILLS: none\n## modes\nomo-programming/debugging", "omo-reviewer")), "");
  assert.equal(gate(dispatch("LOAD_SKILLS: none\nThe MODES: line names omo-programming/debugging", "omo-reviewer")), "");
  assert.equal(gate(dispatch("LOAD_SKILLS: none\n## MODES\n## 1. Task\nomo-programming/debugging", "omo-reviewer")), "");
  assert.equal(gate(dispatch("LOAD_SKILLS: none\nMODES: none", "omo-reviewer")), "");
});

test("a MODES line is ignored when the gate is off or the agent is not gated", () => {
  const prompt = "LOAD_SKILLS: none\nMODES: omo-review/review-work";
  assert.equal(gate(dispatch(prompt), { OMO_LOAD_SKILLS_GATE: "off" }), "");
  assert.equal(gate(dispatch(prompt, "omo-orchestrator:omo-oracle")), "");
  assert.equal(run(dispatch(prompt), { env: {}, catalogText: undefined }), "");
});
