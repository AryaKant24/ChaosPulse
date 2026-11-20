# ChaosPulse

ChaosPulse is a local FastAPI chaos and observability lab. It demonstrates bounded HTTP fault injection, Kubernetes probes, per-pod Prometheus metrics, a browser control room, and a Jenkins build pipeline. It is for research and local demonstration. It has no authentication. Keep it on a trusted machine or network.

## Components

- FastAPI app: `app/main.py`; serves the UI in `app/static/index.html`.
- Kubernetes app: three replicas, a NodePort Service, and liveness/readiness probes in `k8s/`.
- Prometheus: runs in Minikube, discovers ChaosPulse pods in the `default` namespace, and scrapes each pod IP on port 8000 every five seconds.
- Grafana: runs in Docker and queries the host-published Prometheus port.
- Jenkins: runs tests, validates Kubernetes YAML with Kubeconform, and builds the app image.

See [AGENTS.md](AGENTS.md) for the API contract, service boundaries, and safety rules.

## Requirements

- Windows with PowerShell, Docker Desktop, Minikube, and `kubectl`.
- Python 3.10 or newer for local development. The app image uses Python 3.11.

## Start the local lab

From PowerShell, run:

```powershell
.\start-lab.ps1
```

The script has side effects. It starts Minikube if needed; builds and loads `chaospulse:1.0`; updates the Prometheus ConfigMap; applies `k8s/`; restarts the app and Prometheus deployments; starts Jenkins and Grafana containers if needed; builds the custom Jenkins image from `ci/Dockerfile.jenkins` if the Jenkins container does not exist; removes an old Docker-hosted Prometheus container; and keeps app and Prometheus port forwards running. Press Ctrl+C to stop the forwards. Do not run the script for a read-only check.

The script builds the app image on every start. This makes Minikube use the current checkout instead of an old local image.

| Service | Address | Notes |
|---|---|---|
| ChaosPulse UI and API | `http://localhost:8000` | Forwarded to `chaospulse-svc` in Minikube. |
| Prometheus | `http://localhost:9090` | In Minikube; use `/targets` to inspect pod targets. |
| Grafana | `http://localhost:3000` | Docker container; configure its Prometheus data source as `http://host.docker.internal:9090`. New Grafana storage uses the default `admin` / `admin` login. |
| Jenkins | `http://localhost:8080` | Docker container; the agent listener uses port 50000. |

The Kubernetes Service exposes port 80 to app container port 8000 and NodePort 30080. The local app forward uses port 8000. Prometheus reaches the app pods directly; it does not scrape through the load-balanced Service.

## Check the lab

Use read-only commands first:

```powershell
kubectl get pods -o wide
kubectl get services
kubectl get endpoints chaospulse-svc
kubectl rollout status deployment/chaospulse-deploy
```

Open `http://localhost:8000` for the War Room. The status card shows the pod that returned the latest state snapshot. The local counters belong to that pod. A control request, later status request, and work request pass through the Service and can reach different pods.

## API

| Route | Purpose |
|---|---|
| `GET /` | Serves the War Room UI. If the static file is missing, returns a small service status object. |
| `GET /api/status` | Returns pod identity, uptime, local counters, fault state, and fault expiry timestamps. |
| `GET /healthz` | Returns 200 while healthy, or 500 while the liveness fault is active. |
| `GET /readyz` | Returns 200 while ready, or 503 while the readiness fault is active. |
| `GET /api/work` | Simulates work with 10–45 ms random delay plus configured latency. Monkey mode returns 500 with 50% probability. |
| `GET /metrics` | Exposes Prometheus metrics. |
| `GET` or `POST /api/chaos/{action}` | Sets or clears `monkey`, `latency`, `readiness`, and `liveness` faults, or clears faults with `reset`. |

Faults expire after 60 seconds by default. `duration_s` accepts 1–300 seconds. Latency accepts optional integer `ms`, clamped to 0–5000. Without `ms`, the latency action toggles between 0 and 600 ms. Expiry and state are local to the pod that receives the control. Reset clears fault flags and expiry values on that pod; it does not reset counters. The existing GET control route changes state, so it is not a safe read operation.

## Metrics and dashboards

Prometheus discovers running pods labeled `app: chaospulse` in the `default` namespace. Its service account has a namespace-scoped Role that can list and watch pods. Each pod is an independent target with `pod` and `namespace` labels.

Metrics include `http_requests_total`, `http_request_duration_seconds`, and `in_flight_requests`. Example PromQL queries:

```promql
sum by (pod, status) (rate(http_requests_total{endpoint="/api/work"}[1m]))
```

```promql
histogram_quantile(0.95, sum by (le, pod) (rate(http_request_duration_seconds_bucket{endpoint="/api/work"}[5m])))
```

Grafana dashboards are created manually. The Grafana container connects to Prometheus at `http://host.docker.internal:9090`.

## Local development and tests

In PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe -m pytest
```

Use the repository virtual environment. Do not run tests with system Python or overwrite CI reports unless requested.

## Jenkins pipeline

Configure a Jenkins Pipeline job to use this repository, the desired branch, and `Jenkinsfile`. The pipeline has four stages:

1. Checkout the selected branch.
2. Run pytest and publish `reports/results.xml`.
3. Validate each `k8s/*.yaml` file separately with the pinned Kubeconform `v0.6.7` image and strict schema checks.
4. Build `chaospulse:${BUILD_NUMBER}`.

The Jenkins controller image is defined in `ci/Dockerfile.jenkins`. The documented setup mounts the host Docker socket so Jenkins can run Docker builds and Kubeconform. This gives jobs broad control of the host Docker daemon. Run only trusted jobs with this setup. Jenkins packages are installed by the controller image and are not pinned to the versions in `requirements.txt`.

## Fault experiment safety

Do not inject faults into a shared or unknown cluster. Confirm the local Minikube environment first. The app Service can route a control to any pod. If an experiment needs an exact pod, use a pod-specific port-forward and verify the pod identity before sending the control. Define the fault, target, duration, expected response, and recovery check before a test. Liveness faults can restart a container; readiness faults remove a pod from Service traffic. Use bounded load and confirm the target returns to nominal state.
