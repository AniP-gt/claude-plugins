# omo-init-deep IND-M Fresh Baseline

## Evaluation Record

- Scenario: `IND-M`, median
- Target: `omo-orchestrator/skills/omo-init-deep/SKILL.md`
- Protocol: `docs/reports/omo-orchestrator-skill-tuning/protocol.md`
- Method: artifact-only simulation from the frozen target and scenario. No disposable fixture was opened, no repository command ran, and no target or protocol file changed.
- Scope boundary: this report covers only `IND-M`. It does not evaluate `IND-E` or any other scenario.

## Simulated Output

The modeled executor accepts the default local update mode and effective depth `3`, then remains in `preview`.

Its preview limits planned managed output to these locations:

```text
.claude/rules/omo-init-deep/
.claude/omo/init-deep.json
```

It identifies `git rev-parse --git-path info/exclude` as the only valid way to obtain the worktree's exclude path. The preview records `HEAD`, branch, and dirty state as observations. Dirty content is a warning only, so unrelated files are neither read as owned output nor changed.

The modeled evidence record has six bounded baseline lanes: structure and module boundaries, entry points and interfaces, conventions and constraints, build and CI, tests, and security-sensitive or generated areas. It may add focused lanes only under the stated scale signals and content-read caps. Any unavailable LSP or ast-grep capability is recorded as unavailable, and metrics that depend on it remain unmeasured. Before an explicit final preview and the required exclude confirmation, it performs no rule, manifest, or exclude write.

## Requirements And Scoring

| Item | Result | Score | Reason |
|---|---|---:|---|
| 1. [critical] Restricts ownership to the two documented managed locations and previews before mutation. | ○ | 1 | The ownership boundary names only the managed rule directory and manifest. The phase order requires `preview` before `generate`, and the confirmation section prohibits the first write until all required confirmations are resolved. |
| 2. Uses the Git-resolved exclude path concept and reports dirty state without touching unrelated files. | ○ | 1 | Discovery requires `git rev-parse --git-path info/exclude`, rejects a constructed path, and calls for recording dirty state. It also says a dirty tree does not permit unrelated changes. |
| 3. Records bounded evidence lanes and leaves unavailable metrics unmeasured. | ○ | 1 | The evidence section specifies six named baseline lanes, bounded focused lanes, file-read caps, and explicit capability gaps. It says not to invent metrics and to leave dependent metrics unmeasured. |

- Success: ○
- Accuracy: 100% (`3 / 3`)
- Scoring basis: modeled execution against the frozen checklist. This is not observed fresh-executor evidence.

## Metadata

| Field | Value | Reason |
|---|---|---|
| `tool_uses` | unmeasured | Artifact-only simulation has no task-result metadata. The protocol forbids estimating this value. |
| `duration_ms` | unmeasured | Artifact-only simulation has no task-result metadata. The protocol forbids estimating this value. |
| Retries | 0 modeled | The simulated path has no repeated judgment. This is a model of the execution path, not executor telemetry. |

## Unclear Points

- No failed critical item. The simulated result passes the frozen critical ownership-and-preview requirement.
- The scenario does not include the synthetic repository evidence packet, so this simulation cannot name actual rule candidates, scores, dirty paths, or the Git-resolved exclude path.
- The prompt requires six evidence lanes but does not give a compact report template that pairs each lane with its evidence, capability state, and measured or unmeasured metrics. An executor must choose that presentation shape.

## Discretion Gaps

- Without fixture contents, the executor must decide how much of the preview to render while avoiding invented candidates and measurements.
- The target allows bounded focused lanes for scale signals, but the scenario does not state which signals are present. The simulation correctly leaves focused-lane selection unresolved.
- The target requires dirty-state reporting but leaves the display form open, such as a summary count, paths, or both.

## Item-Linked Proposal

- Frozen item 3, judgment wording "Records bounded evidence lanes and leaves unavailable metrics unmeasured": add a short preview table shape with `lane`, `evidence`, `capability`, and `metric state` columns. That would make capability gaps and unmeasured metrics easier to report consistently without changing the safety or ownership contract.

## Disposition

This is the fresh baseline record for one scenario, not a convergence result. It introduces no prompt or protocol change and does not support a comparison of tool-use or duration variation until a later observed fresh-executor run provides metadata.
