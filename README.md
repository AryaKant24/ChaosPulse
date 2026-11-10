# ChaosPulse — Cloud-Native SRE & Chaos-Engineering Microservice

ChaosPulse is a production-grade, lightweight FastAPI microservice engineered to simulate failure states, expose native Prometheus telemetry, and run through a complete local DevOps and SRE pipeline (Docker, Jenkins, Minikube Kubernetes, Prometheus, and Grafana).

---

## Prerequisites & System Requirements

* **Docker Desktop** (with Kubernetes and `host.docker.internal` enabled)
* **Minikube & kubectl** installed for local cluster orchestration
* **Python 3.10+** and `pytest` for local testing

---

## Project Directory Structure

```text
chaospulse/
├── app.py                # FastAPI microservice with /metrics, /healthz, /readyz, and chaos triggers
├── test_app.py           # Pytest automated test suite
├── Dockerfile            # Multi-stage, non-root runtime container build
├── Dockerfile.jenkins    # Custom Jenkins controller image with Python & Docker CLI
├── Jenkinsfile           # Declarative CI pipeline definition (Checkout -> Test -> Build)
├── k8s-deployment.yaml   # 3-replica Kubernetes Deployment with Liveness & Readiness probes
├── k8s-service.yaml      # Kubernetes NodePort Service for internal and external load balancing
└── prometheus.yml        # Prometheus scrape configuration targeting the app

```

---

## Step-by-Step Setup & Execution Guide

### 1. Local Development & Testing

Run and test the FastAPI application locally before containerizing:

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install fastapi uvicorn prometheus-client httpx pytest

# Run unit tests
pytest --junitxml=reports/results.xml

```

---

### 2. CI/CD Pipeline Setup (Jenkins)

Build and run the custom Jenkins controller supporting Docker-in-Docker socket binding and Python testing:

```bash
# Build custom Jenkins image with Python & Docker CLI
docker build -t my-jenkins -f Dockerfile.jenkins .

# Run Jenkins with persistent storage and host Docker daemon access
docker run -d --name jenkins -p 8080:8080 -p 50000:50000 -v jenkins_home:/var/jenkins_home -v /var/run/docker.sock:/var/run/docker.sock --group-add 0 my-jenkins

```

1. Open **`http://localhost:8080`** in your browser.
2. Retrieve the initial admin password from your terminal:
```bash
docker exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword

```


3. Create a new **Pipeline** job named `chaospulse-pipeline`, configure it to use **Pipeline script from SCM**, point it to your GitHub repository, and specify `Jenkinsfile`.
4. Click **Build Now** to execute automated code linting, unit testing with JUnit reports, and immutable image tagging (`chaospulse:${BUILD_NUMBER}`).

---

### 3. Kubernetes Orchestration (Minikube)

Deploy a highly available, multi-replica instance of ChaosPulse managed by automated health probes:

```bash
# Start Minikube cluster
minikube start

# Load locally built image into Minikube's container runtime
minikube image load chaospulse:1.0

# Apply Kubernetes manifests (Deployment with 3 replicas + NodePort Service)
kubectl apply -f k8s-deployment.yaml -f k8s-service.yaml

# Forward local port to cluster service
kubectl port-forward svc/chaospulse-svc 8000:80

```

* Access the interactive War Room UI at **`http://localhost:8000`**.
* Verify probe self-healing and traffic eviction:
```bash
kubectl get pods -o wide
kubectl get endpoints chaospulse-svc

```



---

### 4. Observability Stack (Prometheus & Grafana)

#### Prometheus Scraping

Run Prometheus configured via a local bind mount (`prometheus.yml`):

```bash
docker run -d --name prometheus -p 9090:9090 -v "${PWD}/prometheus.yml:/etc/prometheus/prometheus.yml" prom/prometheus

```

* Verify targets are healthy at **`http://localhost:9090/targets`**.
* Run PromQL expressions (e.g., `sum by (status) (rate(http_requests_total[1m]))`) at **`http://localhost:9090/graph`**.

#### Grafana Dashboards

Launch Grafana and link Prometheus as a data source:

```bash
docker run -d --name grafana -p 3000:3000 grafana/grafana

```

1. Log in to **`http://localhost:3000`** (`admin` / `admin`).
2. Add a new **Prometheus** data source with connection URL: `[http://host.docker.internal:9090](http://host.docker.internal:9090)`.
3. Import or build panels for **Request Rate** and **p95 Tail Latency** using Prometheus metrics (`http_requests_total` and `http_request_duration_seconds_bucket`).