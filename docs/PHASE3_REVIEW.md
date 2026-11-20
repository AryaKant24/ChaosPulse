# Phase 3 Review

**Status:** Phase 3 validation is complete for app, tests, manifests, and Prometheus. Jenkins, browser interaction, and fault experiments remain unchecked.

## Cause of the rollout wait

- Minikube rebooted and recreated the app pod sandboxes.
- The Prometheus image pull took 39 seconds.
- Prometheus loaded its configuration and became Ready.
- The Prometheus Deployment is now 1/1 Available.

## Stale app image and fix

- The live `/api/status` response has no `expires_at` field.
- The live UI has the old pod label.
- The startup script skipped the build when a local `chaospulse:1.0` image already existed.
- The live app did not include the latest backend and UI changes.
- `start-lab.ps1` now rebuilds the app image, loads it into Minikube, and restarts the app Deployment.
- The Strict Teacher reviewed this fix before rollout.
- The current source image was built and loaded into Minikube. The app Deployment restarted and completed its rollout.
- All three new app pods are Ready. The API returns `expires_at`, and the UI serves the new pod snapshot label.

## Validation results

- `/healthz`, `/readyz`, and `/api/status` returned HTTP 200.
- All three app pods were Ready.
- Prometheus showed three distinct pod targets with `up=1`.
- Each target had 120 samples in the last ten minutes. Each `min_over_time(up[10m])` value was 1.
- A read-only query through Grafana returned `up=1` for all three pods.
- The in-flight gauge was 0 for all three pods.
- Three normal `/api/work` requests returned 200 from one pod. Its request counter and histogram count increased from 0 to 3. All gauges returned to 0.
- Kubeconform `v0.6.7` reported 7 valid resources in 3 files.
- The project suite passed: 15 tests passed. The first run found four tests that read a private histogram field. The helper now reads the public Prometheus exposition.
- PowerShell syntax parsing and `git diff --check` passed.

## Strict Teacher review

- Confirmed that the startup-script fix rebuilds and reloads the app image before restarting the Deployment.
- Reviewed the full Phase 3 changes and outcomes after implementation.
- Cleared the startup-script fix and the millisecond expiry timestamp change.

## Limits

- Jenkins was not run. Its configured job targets `*/main`; these commits remain local and were not pushed.
- Browser interaction was not checked. The served UI content was checked through HTTP.
- No liveness or readiness fault experiment ran. No target and duration were agreed for an experiment.
