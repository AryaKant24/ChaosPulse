# ChaosPulse Codex Project Notes

This folder records Codex workflows that are specific to the ChaosPulse repository. It is a project log and prompt library. It does not install skills, configure Codex globally, or create persistent runtime agents.

## Purpose

- Record skills used or considered for this repository.
- Record agent roles used for repository investigations.
- Keep reusable role briefs for future implementation and review tasks.
- Make it clear which roles were actually run and which are only proposed.

## Contents

- [Skill registry](skills.md) records relevant Codex skills and their use status.
- [Agent registry](agents.md) records the subagents used in the initial repository review and reusable agent role briefs.

## Project context

ChaosPulse is a local FastAPI chaos engineering lab. See the repository-level [AGENTS.md](../AGENTS.md) for architecture, API contract, service connections, ports, and safety rules. See [README.md](../README.md) for user setup instructions.

## Maintenance rules

- Update these records when a skill materially contributes to a ChaosPulse task or when a project-specific skill is created.
- Record skill source, purpose, trigger, status, and any repository-specific constraints. Do not copy globally installed skill files into this repository unless a task explicitly requires a project-owned skill.
- Record agent role, task, status, useful output, and whether the role is reusable.
- Mark proposed roles as proposed. Do not describe them as agents that have run.
- Keep reusable agent briefs narrow. Give each agent a distinct scope and ask for file paths, evidence, risks, and recommendations.
- Use a separate read-only validator after implementation work. The validator must inspect the diff and relevant tests. It must not edit files unless explicitly assigned a repair task.
- Agents share this repository workspace. Do not run agents in parallel when they may edit the same files. Parallelize independent read-only reviews or disjoint implementation tasks.
- Follow `../AGENTS.md` for test, runtime, and chaos safety rules.

## Change log

| Date | Change |
|---|---|
| 2026-11-20 | Added this project-specific skill and agent registry after the initial ChaosPulse review. |
