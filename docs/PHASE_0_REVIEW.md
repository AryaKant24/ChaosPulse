# ChaosPulse v2 — Phase 0 Review

**Status:** Phase 0 reviewed and locked by the user for Phase 1 implementation.
**Scope:** Read-only review of fault recovery, replica observability, and test/CI coverage.
**Runtime or fault experiments:** None. No tests or live Docker, Minikube, Prometheus, or Kubernetes checks were run.

## 1. Review outcome

Phase 0 confirms the plan's main findings and recommends these implementation directions:

1. Add bounded expiry for process-local fault state, report its expiry, and retain Kubernetes restart recovery for liveness faults.
2. Run Prometheus in Minikube with Kubernetes pod discovery so every ChaosPulse replica is a distinct target.
3. Expand deterministic unit coverage and keep Kubernetes behavior in opt-in integration checks against a confirmed disposable cluster.
4. Freeze the API, scrape, and file ownership contracts below before Phase 1 begins.

These are design recommendations, not evidence of current runtime behavior. The current setup was inspected from repository files only.

## 2. Evidence reviewed

| Area | Repository evidence | Finding |
|---|---|---|
| Fault state | `app/main.py`: module-level `state`; `get_status`, `healthz`, `readyz`, `do_work`, and `trigger_chaos` read or mutate it | State is local to one Python process. Faults currently have no expiry. Reset clears fault flags but preserves counters. |
| Liveness recovery | `k8s/deployment.yaml`: liveness probe checks `/healthz` every five seconds | Kubernetes may restart a liveness-failed process before an application timer could expire the fault. A restarted process starts with nominal in-memory state. |
| Control/status | `app/main.py`; `app/static/index.html` | Responses include a pod identity, but status has no expiry fields and the UI polls status separately from a control response. |
| Scraping | `monitoring/prometheus.yml`; `k8s/deployment.yaml`; `k8s/service.yaml`; `start-lab.ps1` | Docker Prometheus has one static target at `host.docker.internal:8000`, reached through a port-forward to a load-balanced Service. This cannot provide one target per pod. |
| Metrics | `app/main.py` | Work metrics include a `pod` label, but labels do not create Prometheus targets. Histogram initialization adds a synthetic 5 ms observation. |
| Tests | `tests/test_app.py` | Five in-process tests cover basic UI/status, probe codes, latency configuration, and metric family presence. They do not prove Kubernetes restart/eviction behavior. |
| CI | `Jenkinsfile`; `requirements.txt` | Jenkins' “Lint & Unit Test” stage only runs pytest; it does not create `reports/` before writing the JUnit file. No manifest validation or image smoke check is configured. |
| Operations | `start-lab.ps1` | Startup applies Kubernetes resources, may build/load an image, starts containers, removes/recreates Prometheus, and holds a port-forward loop. It is an exclusive runtime operation. |

## 3. Proposed API and behavior contract

This contract preserves process-local state and current reset counter semantics. The user accepted the proposed values and fields below for Phase 1.

### Fault lifecycle

- Use one `expire_state(now)` path before status, control, work, and probe handlers read or change fault state. Use monotonic deadlines internally.
- Give each enabled fault a bounded lifetime. Proposed default: **60 seconds**; proposed maximum: **300 seconds**. A request may choose `duration_s` from 1 through 300. Reject values outside the range with the framework's normal validation response rather than silently extending the maximum.
- Apply expiry to `monkey`, nonzero `latency`, `readiness`, and `liveness`. Disabling a toggle clears its deadline. `latency?ms=0` clears its deadline. An omitted duration uses the default.
- Expose an `expires_at` mapping with fixed fault keys and UTC ISO-8601 timestamps or `null` for inactive faults in both `/api/status` and the control response. Keep existing top-level flag fields and the control response's `state` field for compatibility. Include `pod` on both responses; expiry belongs to that process only.
- Reset clears every active fault and expiry on the process handling the request. It does not reset local request counters or Prometheus counters.
- If Kubernetes restarts a process after a liveness fault, its in-memory fault and deadline disappear as the process starts nominal. Do not attribute that recovery to the expiry timer.
- Keep controls process-local. A request through the Service may reach any replica. A response identifies the receiving pod; it does not imply cluster-wide control.

### Metrics and scrape topology

- Remove the synthetic histogram observation. A new process must expose histogram count zero until `/api/work` records a real request.
- Keep metric labels bounded to fixed endpoint, status, pod, action, probe, and outcome values. Do not add arbitrary user input or request IDs as labels.
- Run Prometheus in Minikube and discover pods with Kubernetes pod discovery. Relabel to retain only `app=chaospulse` pods and scrape the application metrics port 8000 at `/metrics`.
- Use the minimum RBAC needed to list/watch pods. Prefer a namespace-scoped Role and RoleBinding when Prometheus and the app share a namespace; document any wider scope if deployment requires it.
- Expose Prometheus to the host through a managed port-forward on host port 9090. Grafana may remain Docker-hosted initially and use `http://host.docker.internal:9090` as its data source.
- Do not use a load-balanced Service target as evidence of per-pod discovery.

### Test and validation contract

- Use a controllable clock for expiry tests and mocked randomness for both monkey outcomes.
- Cover TTL defaults/bounds, each expiring fault, expiry before/after deadlines, reset/deadline semantics, unchanged counters on reset, latency bounds and measured delay, exact metric increments, histogram observations, and gauge cleanup on success and failure paths.
- Keep unit tests in-process. They cannot establish Kubernetes restart, readiness endpoint removal, or Prometheus target discovery.
- Run the suite serially with `venv\\Scripts\\python.exe -m pytest -p no:cacheprovider` on Windows, only after implementation edits are stable. Do not write/replace JUnit reports locally unless requested.
- Jenkins should call its pytest-only stage “Unit Test” unless a linter is added, create the report directory before pytest, and publish JUnit results even after test failure. Linting, manifest validation, and image smoke checks remain separate decisions requiring pinned tools and isolated execution.
- Later runtime acceptance is read-only first. The per-pod scrape check must show three distinct ready targets with `up == 1` continuously for at least ten minutes. A readiness test and any liveness fault experiment require a confirmed disposable local cluster and an agreed target, duration, expected result, and recovery action.

## 4. Lock-in contract for implementation

The following locks are mandatory for every subsequent phase. They are designed to prevent conflicting edits, stale interfaces, test races, and simultaneous control of shared runtime services.

### 4.1 Ownership and file locks

| Work bundle | Exclusive write scope | Dependency / release condition |
|---|---|---|
| Backend lifecycle and metrics | `app/main.py` | One backend owner for the entire bundle. API/status schema is frozen before UI work starts. |
| Deterministic application tests | `tests/test_app.py` | One test owner. Tests may be authored against the frozen contract while backend code is edited, but no test run starts until both owners stop editing. |
| Per-pod scrape topology | `monitoring/`, Prometheus-related `k8s/` resources and RBAC, related `start-lab.ps1` changes | One observability owner owns this complete coupled bundle. No other writer edits these paths/resources during the phase. |
| UI operator feedback | `app/static/index.html` only | Starts after backend response fields are frozen. One UI owner. No concurrent backend/UI interface changes. |
| CI changes | `Jenkinsfile` and specifically approved CI dependency/config files | One CI owner; any added tool and version must be approved in the selected path before editing. |
| Documentation | `README.md`, `AGENTS.md`, `.codex/` records | One documentation owner, after behavior/topology/CI contracts pass validation. |
| Integration and acceptance record | A designated Phase 3 validator; read-only | Starts only after all implementation edits stop. Does not share write ownership with implementers. |

No agent or contributor edits files outside their assigned scope. Before a phase begins, the primary agent records the owner for each selected bundle and the exact paths in the task. If scope crosses a lock, work pauses until the primary agent reassigns the whole affected bundle; no workaround or parallel edit is allowed.

### 4.2 Interface and phase gates

1. This review is the Phase 0 proposal. The user explicitly accepts or revises the API, TTL values, scrape topology, and selected implementation paths before Phase 1 starts.
2. The primary agent records the accepted contract in the active work instructions. Backend and tests use the same version. UI work remains locked until the backend response contract is stable.
3. A contract change pauses every dependent lane. The primary agent updates the contract and acceptance criteria, then explicitly releases the affected owners to resume.
4. Each phase has one selected path and one named owner per write bundle. Unselected work remains out of scope until a later path is selected.
5. Before a phase is presented as ready to close, run the read-only Strict Teacher review: inspect each bundle independently and the integrated diff, and run applicable checks through the repository virtual environment. Resolve blocking findings or report what remains unverified. Only then record acceptance evidence and present the next paths to the user. No phase transition is inferred from elapsed time or partial results.

### 4.3 Shared test, Git, and runtime locks

- **Tests:** One test runner at a time. Do not run pytest while `app/main.py` or `tests/test_app.py` is being edited. Use only the repository virtual environment; avoid parallel test execution because module-level state is shared. Use no report output by default.
- **Git:** The primary agent alone stages, commits, or performs shared branch operations while assigned implementation work is active. Contributors do not stage or commit shared workspace changes.
- **Runtime:** One named runtime operator at a time for Docker, Minikube, Kubernetes, Prometheus, Grafana, and host ports. `start-lab.ps1` is an exclusive operation and cannot overlap another runtime check. Code review and local unit-test authoring must not operate the lab.
- **Fault experiments:** No liveness/readiness chaos during routine validation. Before any authorized experiment, record the environment, exact pod/target, fault, duration, expected behavior, and recovery action. Do not proceed against a shared or unknown cluster.
- **Validation:** The validator is read-only and reviews the complete diff against the accepted criteria after implementation stops. Fixes return to an explicitly assigned implementation pass; the validator rechecks after the pass.

## 5. Phase map and recommended next path

| Phase | Candidate path | Outcome | Connection to overall development |
|---|---|---|---|
| 1 — Core | Backend lifecycle/metrics, deterministic tests, and scrape topology under the three separate ownership bundles | Fault expiry, trustworthy metrics, and per-pod scrape configuration | Implements the P0/P1 foundations needed by the UI and later runtime verification. Unit tests run after backend and test edits stabilize. |
| 1 — Narrow | Backend lifecycle and tests first; defer scrape topology | Safe, testable fault recovery | Resolves the P0 risk before topology changes, but postpones replica observability and requires a later Phase 1 pass. |
| 1 — Observability first | Scrape topology and removal of the synthetic metric sample | Per-pod Prometheus design and accurate histogram behavior | Establishes the target topology early; fault lifecycle remains a separate follow-on bundle. |
| 2 — UI | Update process/pod identity, local-state labels, control response feedback, and expiry | Operator displays which pod handled each response and its local expiry state | Depends on the Phase 1 backend contract and avoids claiming cluster-wide control. |
| 2 — CI | Correct stage/report behavior; optionally add approved pinned tools | CI results accurately describe executed checks | Can proceed independently after Phase 1 contracts; adds no live-lab operations. |
| 3 — Validation | Read-only diff/test/config review, then read-only runtime checks | Evidence against accepted criteria and a recorded gap list | Confirms implementation across code, Kubernetes discovery, and Prometheus without conflating unit and integration evidence. |
| 4 — Documentation | Update setup, ports, topology, safety boundary, and script effects | Reproducible instructions matching accepted implementation | Closes the loop after behavior and topology are stable. |

**Recommended next path:** Phase 1 core bundles in parallel only after the user locks the contract: backend owns `app/main.py`, test author owns `tests/test_app.py`, observability owner owns the monitoring/Kubernetes/script bundle. Keep test execution and all runtime operations serialized behind the gates above. This follows the implementation plan and produces the foundations required by Phase 2 UI/CI work.

## 6. User lock-in record

The user selected **Phase 1 core bundles in parallel**, as the implementation plan intends, and accepted these implementation decisions:

- Fault duration: 60-second default, 300-second maximum, `duration_s` request parameter, and `expires_at` response mapping.
- Scrape topology: in-cluster Prometheus with per-pod discovery, exposed to the host through a managed port-forward.
- Phase 1 bundles: backend (`app/main.py`), tests (`tests/test_app.py`), and observability (`monitoring/`, Prometheus-related Kubernetes resources, and related `start-lab.ps1` changes) proceed in parallel under exclusive file ownership.
- Jenkins, linting, manifest validation, image smoke checks, UI, and documentation are deferred to their later planned phases. This Phase 1 authorization does not include those bundles.

No implementation may cross the ownership scopes or skip the test/runtime gates in Section 4. The primary agent will record the assigned owner for each bundle before work begins.

## 7. Review provenance

This review used three read-only scopes: fault lifecycle and recovery; metrics and scrape topology; tests, CI, and safety. Reviewers inspected repository source and configuration only. No files other than this Phase 0 artifact were changed as part of the review. No unit tests, live-service requests, chaos actions, or cluster operations were performed.
