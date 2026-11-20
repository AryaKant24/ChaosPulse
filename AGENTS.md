# ChaosPulse Agent Guide

## Project overview

ChaosPulse is a local FastAPI chaos engineering and observability lab. It demonstrates HTTP failure injection, Kubernetes readiness and liveness probes, Prometheus metrics, a browser control room, and a Jenkins image build pipeline.

The project is for research and local demonstration. It is not a hardened production service. Chaos controls currently have no authentication. Keep the lab on a trusted local machine or network.

## Existing architecture and locations

- `app/main.py` creates the FastAPI application, API routes, in-process chaos state, and Prometheus metrics.
- `app/static/index.html` is the War Room UI. It polls `/api/status`, sends chaos controls, and generates browser-side work traffic.
- `tests/test_app.py` contains FastAPI `TestClient` unit tests.
- `Dockerfile` builds the app image. The runtime uses a non-root `appuser` and runs Uvicorn on port 8000.
- `k8s/deployment.yaml` deploys three app replicas with resource limits and liveness/readiness probes.
- `k8s/service.yaml` exposes the replicas with a NodePort service.
- `monitoring/prometheus.yml` configures a static Prometheus scrape target.
- `Jenkinsfile` checks out the repository, runs pytest, publishes a JUnit report, and builds an image.
- `ci/Dockerfile.jenkins` defines the Jenkins controller image.
- `start-lab.ps1` starts Minikube, deploys the Kubernetes manifests, starts Jenkins, Prometheus, and Grafana, then keeps a Kubernetes port-forward running. It removes and recreates the Prometheus container when it runs.
- `README.md` describes setup. Keep it aligned with the actual repository paths and behavior.

## API contract and boundaries

- `GET /` serves the UI. If the static file is missing, it returns a small service status object.
- `GET /api/status` returns the local process pod name, uptime, chaos flags, and local success/error counters.
- `GET /healthz` returns 200 when healthy and 500 when the liveness fault is active. Kubernetes uses this as its liveness probe.
- `GET /readyz` returns 200 when ready and 503 when the readiness fault is active. Kubernetes uses this as its readiness probe.
- `GET /api/work` simulates work. It adds 10–45 ms random delay and the configured latency. With monkey mode enabled, it returns 500 with 50% probability. It updates local counters and Prometheus metrics.
- `GET /metrics` exposes the Prometheus registry in the Prometheus text format.
- `GET|POST /api/chaos/{action}` currently accepts `monkey`, `latency`, `readiness`, `liveness`, and `reset`. The route changes process state. GET mutation is existing behavior; do not treat it as a safe read operation. Preserve or change this contract only when the task asks for it, and update tests and documentation with any contract change.
- `latency` accepts optional integer query parameter `ms`; the current handler clamps values to 0–5000. Without `ms`, it toggles between 0 and 600 ms.
- `reset` clears fault flags but does not clear local request counters or Prometheus counters.

Chaos state and UI counters are stored in a module-level dictionary. They are local to one Python process. A Kubernetes service may route each request to a different pod. A control call and a later status call can therefore refer to different replicas. A reset affects only the process that receives it. A container restart clears its in-memory state.

## Service connections and ports

| Component | Port | Connection and boundary |
|---|---:|---|
| FastAPI container | 8000 | Uvicorn listens on `0.0.0.0:8000` inside the container. |
| Kubernetes Service | 80 → 8000 | Selects pods labeled `app: chaospulse`. |
| Kubernetes NodePort | 30080 | Exposes the Service through the cluster node. |
| Local app forward | localhost:8000 | `start-lab.ps1` forwards `svc/chaospulse-svc` port 80 to local port 8000. The Prometheus container reaches this as `host.docker.internal:8000`. |
| Prometheus | 9090 | Published on the host. Scrapes `http://host.docker.internal:8000/metrics` every five seconds. The current configuration has one static target; it does not discover each Kubernetes pod independently. |
| Grafana | 3000 | Published on the host. The README configures Prometheus as its data source at `http://host.docker.internal:9090`. Dashboard setup is manual. |
| Jenkins web UI | 8080 | Published on the host. |
| Jenkins agent listener | 50000 | Published on the host. |

The UI, Prometheus, and Grafana are separate processes/containers. The UI calls the app. Prometheus scrapes the app. Grafana queries Prometheus. Jenkins runs tests and builds the app image. The documented Jenkins setup mounts the host Docker socket, which gives Jenkins jobs powerful control of the host Docker daemon. Do not run untrusted jobs with that setup.

## Safety rules for chaos experiments

- Confirm the target environment and pod before sending a chaos control. Do not assume a request through the Service will reach a specific pod.
- Do not trigger liveness or readiness faults against a shared or unknown cluster. Liveness faults can restart containers. Readiness faults can remove pods from service traffic.
- For routine checks, use unit tests and read-only checks such as `/healthz`, `/readyz`, `/api/status`, `/metrics`, Prometheus targets, and Kubernetes pod/service status.
- Run tests only with the repository virtual environment: `venv\\Scripts\\python.exe -m pytest` on Windows. Avoid system Python and avoid generating or replacing reports unless the task requests it.
- Before any authorized fault experiment, define the fault, target, duration, expected result, and recovery action. Keep load and latency bounded. Observe the result and reset the target state when safe.
- The current chaos API has no authentication, expiry, audit log, or cluster-wide control semantics. Keep endpoints on a trusted local lab. Do not expose them to the public internet.
- `start-lab.ps1` is not read-only. It can start Minikube, apply Kubernetes manifests, build/load images, start containers, remove and recreate Prometheus, and run a persistent port-forward loop. Run it only when starting or repairing the lab is intended.

## Implementation and validation guidance

- Inspect the affected code and existing tests before editing. Keep changes within the requested scope.
- Preserve the current API contract unless the task explicitly changes it. Update tests and README when behavior or routes change.
- Keep process-local versus per-pod behavior explicit. Do not claim per-replica scraping unless Prometheus configuration and live targets support it.
- Prefer deterministic tests for random behavior by controlling or mocking randomness.
- Validate application changes with the project virtual environment. Validate runtime, Kubernetes, and Prometheus behavior with read-only checks first. Use fault experiments only when the task explicitly authorizes them and the target is known.
- Report changed files, checks run, outcomes, and any operational risk. Do not change files when the user asks for inspection or a plan only.
