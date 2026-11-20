# Phase 3 Review

**Status:** Application and local runtime checks passed. Jenkins tests passed, but manifest validation needed a fix; the job must be rerun.

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

- Jenkins checked out `feat/automated-chaos` at `3ab3d58`.
- The Unit Test stage passed all 15 tests and published `reports/results.xml`.
- Manifest validation failed because `cat k8s/*.yaml` joined separate files without YAML document separators. Kubeconform reported 3 valid resources and 2 parse errors. The Docker image build stage was skipped.
- `Jenkinsfile` now passes each YAML file to the pinned Kubeconform image separately. Local validation passed: deployment 1/1, Prometheus 5/5, and service 1/1.
- Strict Teacher found no blocking issue in the validator fix. A log formatting note was addressed by using `echo` for the filename.
- Jenkins acceptance remains open until the job is rerun with this fix and the validator and Docker image build stages pass.
- No changes were made to the untracked `docs/IMPLEMENTATION_PLAN.md`.

## Outcome

Phase 3 application and local runtime checks passed. Jenkins unit tests passed. The validator fix passed locally, but Jenkins must rerun the pushed fix before CI acceptance is complete.
