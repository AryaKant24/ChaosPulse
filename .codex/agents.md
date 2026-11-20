# Agent Registry

Codex subagents are spawned for a task. The role briefs below are reusable prompts, not persistent agents registered with the application. Agents in this environment share the repository workspace.

## Roles used in the initial repository review

| Agent | Role | Scope | Status |
|---|---|---|---|
| Agent A — Detective | Architecture investigator | FastAPI routes, process-local state, random failure behavior, and injection lifecycle. | Completed read-only review. |
| Agent B — Judge | Observability investigator | Prometheus metrics and scraping, Grafana setup, Kubernetes replica visibility. | Completed read-only review. |
| Agent C — Guard | CI and safety investigator | Tests, Jenkins, Docker, security risks, and risks of automated chaos execution. | Completed read-only review. |
| Agent D — Innovator | Expansion researcher | Data flow and short-scope project ideas based on Agent A's architecture findings. | Completed read-only review. |

These were one-task agents. Their findings are summarized in the conversation and in `../AGENTS.md`. The table records what they did; it does not mean their runtime sessions persist.

## Reusable role briefs

### Detective

Trace the application architecture and request/data flow. Identify relevant files and functions. Explain process boundaries, state ownership, lifecycle, and failure behavior. Return evidence, risks, and recommendations. Do not edit files unless assigned implementation work.

### Judge

Inspect metrics, scrape configuration, dashboards, and Kubernetes resources. Check whether the configuration supports the claimed visibility, including per-replica behavior. Distinguish configuration evidence from live runtime evidence. Return file paths, findings, risks, and recommendations.

### Guard

Inspect tests, CI, container configuration, deployment permissions, and operational risks. Identify coverage gaps and unsafe automation paths. Do not run destructive or disruptive experiments. Return file paths, findings, risks, and recommendations.

### Innovator

Inspect current data flow and architecture. Propose a small set of achievable improvements. Explore alternatives internally; report concise options, tradeoffs, affected files, risks, and a recommended order. Do not expose private chain-of-thought. Do not edit files unless assigned implementation work.

### Implementer — proposed

Implement one approved step from the current plan. Inspect repository guidance first. Keep the change within assigned scope. Report changed files, behavior, tests run, and remaining risks. Do not modify adjacent work without need.

### Validator — proposed

Review the implementation after the implementer finishes. Start with `git diff` and the acceptance criteria. Check relevant tests and inspect code paths for regressions. Run tests only with the repository virtual environment. Do not edit files. Report each criterion as verified, failed, or not checked, with evidence.

## Delegation guidance

- Use investigators in parallel when their scopes are independent and read-only.
- Keep implementation tasks sequential when they touch shared files or depend on earlier decisions.
- Start the validator after implementation. Do not have the validator share editing responsibility with the implementer.
- Give every agent the same acceptance criteria and relevant safety constraints.
- Ask agents to cite repository-relative paths and function names. Require them to separate observed facts from recommendations.
- The current Codex session allows at most three subagents alongside the primary agent. If task scope needs more roles, run them in phases.

## Future task log

Add a row when a new role is actually used. Keep proposed roles in the reusable briefs section until they run.

| Date | Agent role | Task | Status | Useful result |
|---|---|---|---|---|
| 2026-11-19 | Detective | Trace app architecture and failure injection. | Completed | Identified process-local state, endpoint lifecycle, and GET mutation. |
| 2026-11-19 | Judge | Review metrics, scraping, Grafana, and Kubernetes. | Completed | Identified single static scrape target and missing per-pod discovery. |
| 2026-11-19 | Guard | Review tests, CI, Docker, and automated chaos risks. | Completed | Identified coverage gaps, Jenkins Docker socket exposure, and control endpoint risks. |
| 2026-11-19 | Innovator | Propose short-scope project expansions. | Completed | Proposed selectable fault profiles, timed faults, and a bounded retry exercise. |
