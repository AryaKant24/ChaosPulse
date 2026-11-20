# Skill Registry

This registry tracks Codex skills that are relevant to work in this repository. A skill can be globally installed and used without being stored in `.codex/`. This file records project use; it does not install or activate skills.

## Recorded skills

| Skill | Source | Status for ChaosPulse | Use or trigger |
|---|---|---|---|
| `openai-docs` | Codex system skill | Used for a Codex capability question in this project conversation. Not a ChaosPulse implementation skill. | Use when the task asks how Codex features, agents, skills, or app behavior work. Prefer current official documentation when available. |
| `computer-use` | Codex computer-use plugin | Available in the environment; not used for the repository review or implementation planning. | Use only when the task needs interaction with a Windows application or browser UI. Prefer CLI or API checks for repository and service work. |
| Spreadsheet, document, presentation, and visualization skills | Codex bundled skills | Not used for the current ChaosPulse work. | Use only if a task requires authoring or inspecting those artifact types. |

## Project-specific skills

No project-owned Codex skill exists yet.

When a reusable workflow becomes necessary, create a focused skill and record:

- **Name and location:** Use `.codex/skills/<skill-name>/SKILL.md` for a repository-owned skill.
- **Purpose:** State the recurring task that the skill supports.
- **Trigger:** State when an agent should use it and when it should not.
- **Inputs and outputs:** Name required repository files, commands, and expected deliverables.
- **Safety boundaries:** Include the relevant rules from `../AGENTS.md`.
- **Validation:** Describe how to verify the skill's output without claiming checks that were not run.
- **Status and owner:** Mark it as proposed, active, or retired. Record who maintains it.

Keep skill instructions task-specific. Keep general repository rules in `../AGENTS.md` instead of duplicating them in every skill.

## Usage log

| Date | Skill | Task | Outcome |
|---|---|---|---|
| 2026-11-20 | `openai-docs` | Checked Codex capability guidance while planning agent use. | The local manual fetch failed because this environment could not resolve `developers.openai.com`. No current documentation claim was verified from the network. |
