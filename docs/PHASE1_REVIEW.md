# Phase 1 Review

**Status:** Core changes are complete. The Strict Teacher review is complete.

## Work by the agents

### Backend agent

- Added fault expiry to the four fault types.
- Set the default expiry to 60 seconds.
- Set the maximum expiry to 300 seconds.
- Added expiry times to status and control responses.
- Kept fault state local to each process.
- Kept counters when reset clears faults.
- Removed the synthetic histogram sample.
- Rechecked fault state after simulated work delay.

### Test agent

- Added tests for expiry, reset, latency, monkey outcomes, and metrics.
- Added checks for counter values and gauge cleanup.
- Used a controllable monotonic clock.

### Observability agent

- Moved Prometheus into Minikube.
- Added pod discovery for the three ChaosPulse replicas.
- Added namespace-scoped access to list and watch pods.
- Updated `start-lab.ps1` to create the Prometheus ConfigMap and manage both port forwards.
- Added cleanup for the old Docker Prometheus container.

## Strict Teacher review

- Reviewed each bundle and the combined changes.
- Found no missing app routes.
- Found no app handler with an unbounded wait.
- Confirmed that `/api/work` has a bounded delay and decrements its gauge in `finally`.
- Confirmed that controls remain process-local.
- Confirmed that Prometheus targets pod IPs directly.
- Found that second-level expiry times could appear early. The timestamp now reports milliseconds.

## Checks and limits

- `git diff --check` passed.
- PowerShell syntax parsing passed.
- Pytest collected 15 tests but did not finish.
- A separate check showed that the repository Python 3.14 environment blocks while it creates a Windows Proactor event loop. This happens before app code runs.
- No Docker, Minikube, Kubernetes, Prometheus, or chaos operation ran.
- Test, schema, and live target acceptance remain unverified.

## Outcome

The Phase 1 code matches the locked contract by static review. Runtime and test acceptance remain open until the test environment and local cluster can be checked.
