# Phase 3 Review

**Status:** Implementation and local runtime checks passed. Jenkins has not run on this branch.

## Changes

- Updated `start-lab.ps1` to rebuild and load the app image before restarting the deployment. This prevents Minikube from running a stale local image.
- Read histogram counts from the public Prometheus exposition in tests.
- Kept fault state, expiry, and request counters local to each pod.

## Strict Teacher review

- Reviewed the Phase 3 changes and their integration after implementation.
- Approved the startup image rebuild fix and the expiry timestamp precision fix.
- Found no unbounded app endpoint. The work gauge is cleaned up when a request raises an error.

## Checks

- Project suite: 15 tests passed with the repository virtual environment.
- Kubeconform `v0.6.7`: 7 resources in 3 files passed strict validation.
- PowerShell syntax parsing and `git diff --check` passed.
- Local Minikube: all 3 app pods Ready; `/healthz`, `/readyz`, `/api/status`, and `/metrics` returned 200.
- Prometheus and Grafana showed all 3 app pod targets as up. Request counters and histogram samples increased for work requests; in-flight gauges returned to 0.
- Browser: dashboard loaded on a direct pod port-forward. `/api/work` returned 200 with the pod name.
- Invalid controls returned 400 or 422 and left fault state unchanged.
- Monkey and 100 ms latency faults expired and returned to nominal state. Readiness returned 503 during the fault and 200 after expiry.
- Liveness returned 500 and caused one container restart. The pod recovered, and the deployment returned to 3/3 Ready.
- The four Phase 3 commits were pushed to `origin/feat/automated-chaos` through `af79b07`.

## Jenkins status and limits

- The local `chaospulse-pipeline` job selects `*/main`, so it does not select the pushed feature branch.
- Jenkins is running, but its API rejects anonymous access. Automatic review rejected use of the container's initial admin password for authentication. No Jenkins credential was used, and the job was not triggered.
- Jenkins acceptance is open until an authorized Jenkins login or job trigger is available and the job is configured to build `feat/automated-chaos`.
- No changes were made to the untracked `docs/IMPLEMENTATION_PLAN.md`.

## Outcome

Phase 3 application, manifest, and local runtime checks passed. Jenkins validation remains open. Do not treat CI acceptance as complete until the pushed branch passes the Jenkins pipeline.
