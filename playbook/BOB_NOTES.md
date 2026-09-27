# Bob 2.0 — Spike Notes (Task 1.5)

Answers to the questions in `02_BRD_TRD.md § B12 Q4`.
Verified against Bob 2.0 documentation and a live parallel-subagent trial run during this spike.

---

## 1. How the main agent starts a subagent, and what context it can pass

Bob exposes the `spawn_subagent` tool. It takes two parameters:

| Parameter | Type | Purpose |
|---|---|---|
| `description` | string (required) | Full self-contained instructions for the subagent. Include every file path, code snippet, or gap list the subagent needs — it starts with no parent context. |
| `name` | string (optional) | `"explore"` (read-only, lighter model) or `"general"` (full tools, default model). Use `"general"` for test-writing subagents. |
| `fork_context` | bool (optional) | If `true`, the entire parent conversation history is passed into the subagent. Use when the subagent needs prior decisions or constraints. Default: `false`. |

**What to pass for TestGap:**  
Each subagent's `description` should contain:
- The contents of the source file (or its path, pasted inline)
- The relevant rows from `gaps.json` for that file (function name, missing lines, priority score)
- The path to write the output: `sample_project/tests/generated/test_<module>.py`
- The rule: only use `Faker` for test data, never real data; use the `faker` fixture (not `Faker()` directly)
- A reminder that `faker_seed` fixture in `conftest.py` sets seed 1234 for determinism

---

## 2. Whether subagents run in parallel, and the maximum number at once

**Yes — parallel is confirmed and working.**

Two subagents were started in the same turn during this spike. Both ran concurrently and wrote their files independently. Bob's docs state:

> "Bob can break complex tasks into parallel workstreams by spawning specialized subagents."

**No documented hard limit** on the maximum number of simultaneously active subagents was found in the docs.
The BRD suggests starting with 3–4 (BR-09). Based on the trial, calling `spawn_subagent` multiple times in a single turn triggers parallel execution.

**Practical rule for the playbook:** spawn one subagent per source file listed in `gaps.json`, all in the same turn.
Start with 3–4 to stay within safe context limits. If more source files exist, process them in batches.

---

## 3. Whether the playbook can be saved as a custom mode or rules file

**Yes — both mechanisms are available.**

### Option A — Custom mode (`custom_modes.yaml`)

Bob saves custom modes in `.bob/custom_modes.yaml` (project-scoped) or `~/.bob/settings/custom_modes.yaml` (global).  
A mode can carry:
- `roleDefinition` — the agent's persona and standing instructions
- `customInstructions` — step-by-step playbook text
- `groups` — which tools are allowed
- `allowedSubagents` — which subagent presets the mode may spawn

Example skeleton for a TestGap mode:
```yaml
customModes:
  - slug: testgap-writer
    name: 🧪 TestGap Writer
    roleDefinition: >
      You are the TestGap test-writing agent. You follow the TestGap playbook exactly.
      You never edit files outside sample_project/tests/generated/ or reports/.
    whenToUse: Use to run the full TestGap workflow on a target project.
    customInstructions: |-
      Follow playbook/TESTGAP_PLAYBOOK.md step by step.
    groups:
      - read
      - - edit
        - fileRegex: "sample_project/tests/generated/.*\\.py$|reports/.*"
          description: Generated tests and reports only
      - execute
      - subagent
      - todo
```

### Option B — Mode-specific rules files

Store additional rule files in `.bob/rules-{mode-slug}/`:
```
.bob/
  rules-testgap-writer/
    01-playbook.md      ← full TESTGAP_PLAYBOOK.md content
    02-safety-rules.md  ← file-scope restrictions reminder
```
Files are loaded alphabetically and merged with `customInstructions`.

### Recommendation for TestGap

Use **Option A** (custom mode in `.bob/custom_modes.yaml`) with the playbook text in `customInstructions` or a rules file. This is the cleanest approach: one instruction to switch to `testgap-writer` mode is all the developer needs.

---

## 4. Whether a mode can restrict file edits to a path pattern (FR-12 enforcement)

**Yes — `fileRegex` in the `edit` group enforces this at the tool level.**

From the Bob docs:
```yaml
groups:
  - read
  - - edit
    - fileRegex: "sample_project/tests/generated/.*\\.py$"
      description: Generated test files only
```

With this configuration, Bob **cannot** write to any file outside `sample_project/tests/generated/` — the tool call is blocked before it executes, not just instructed away.

**Conclusion:** FR-12 ("tool must never edit real code") can be **enforced**, not merely requested, by setting `fileRegex` in the custom mode. This upgrades FR-12 from a soft playbook rule to a hard capability constraint.

The `reports/` folder also needs to be writable (for JSON output files). The combined regex to use:
```
sample_project/tests/generated/.*\.py$|reports/.*
```

---

## 5. Parallel trial — evidence

Two `spawn_subagent` calls were issued in the same turn:
- Subagent 1: write `scratch/subagent_1.txt` → content: `subagent 1 was here`
- Subagent 2: write `scratch/subagent_2.txt` → content: `subagent 2 was here`

Both completed successfully and concurrently. Both files confirmed present and correct.
Scratch files were deleted after verification.

---

## 6. Fallback decision (BR-09)

Parallel subagents **are available**. No fallback to sequential is needed.  
BR-09 ("Should run in parallel") is met.

If a future run hits context limits, fall back to batches of 3–4 per turn — still faster than strict sequential.

---

## 7. Summary table

| Question | Answer |
|---|---|
| How to start a subagent | `spawn_subagent(description=..., name="general")` |
| Context passing | Inline in `description`; or `fork_context=True` for full parent history |
| Parallel execution | ✅ Yes — multiple calls in same turn run concurrently |
| Max subagents at once | No hard limit documented; start with 3–4 per batch |
| Playbook as custom mode | ✅ Yes — `.bob/custom_modes.yaml` with `roleDefinition` + `customInstructions` |
| Playbook as rules file | ✅ Yes — `.bob/rules-{slug}/` directory |
| File-edit restriction (`fileRegex`) | ✅ Yes — enforces FR-12 at the tool level, not just by instruction |
