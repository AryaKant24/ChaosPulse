# Phase 3 Review

**Status:** Read-only validation is complete. The Strict Teacher cleared the startup-script fix. The running app still uses the old image.

## Cause of the rollout wait

- Minikube rebooted and recreated the app pod sandboxes.
- The Prometheus image pull took 39 seconds.
- Prometheus loaded its configuration and became Ready.
- The Prometheus Deployment is now 1/1 Available.

## Stale app image

- The live `/api/status` response has no `expires_at` field.
- The live UI has the old pod label.
- The startup script skipped the build when a local `chaospulse:1.0` image already existed.
- The live app therefore did not include the latest backend and UI changes.
- `start-lab.ps1` now rebuilds the app image, loads it into Minikube, and restarts the app Deployment.
- The script was not run. The current app stays up. The new image will deploy on a later startup.

## Validation results

- `/healthz`, `/readyz`, and `/api/status` returned HTTP 200.
- All three app pods were Ready.
- Prometheus showed three distinct pod targets with `up=1`.
- Each target had 120 samples in the last ten minutes. Each `min_over_time(up[10m])` value was 1.
- A read-only query through Grafana returned `up=1` for all three pods.
- The in-flight gauge was 0 for all three pods.
- Kubeconform `v0.6.7` reported 7 valid resources in 3 files.
- PowerShell syntax parsing and `git diff --check` passed.

## Strict Teacher review

- Confirmed that the startup-script fix rebuilds and reloads the app image before restarting the Deployment.
- Confirmed that the script change did not alter the running cluster.
- Reviewed the supplied 10-minute scrape and manifest results. The Strict Teacher did not run these checks.

## Limits

- Pytest remains unverified. Python 3.14 event-loop creation blocks before app code in this environment.
- Jenkins and browser behavior were not checked.
- The current app image is old. The new app code has not been verified in Kubernetes.
- No chaos experiment ran.
