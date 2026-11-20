$ErrorActionPreference = "Continue"

Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "  ChaosPulse SRE Lab - Automated Environment Boot   " -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan

# 1. Check Minikube
Write-Host "[1/5] Checking Minikube cluster..." -ForegroundColor Yellow
minikube status | Out-Null
if ($LASTEXITCODE -ne 0) {
    minikube start
} else {
    Write-Host "      Minikube is already running."
    minikube update-context
}

# 2. Deploy Kubernetes manifests
Write-Host "[2/5] Applying Kubernetes manifests (k8s/)..." -ForegroundColor Yellow
docker image inspect chaospulse:1.0 | Out-Null
if ($LASTEXITCODE -ne 0) {
    docker build -t chaospulse:1.0 .
    minikube image load chaospulse:1.0 --overwrite=true
}

$prometheusConfigPath = Join-Path $PSScriptRoot "monitoring\prometheus.yml"
kubectl create configmap chaospulse-prometheus-config `
  --from-file="prometheus.yml=$prometheusConfigPath" `
  --dry-run=client -o yaml | kubectl apply -f -
if ($LASTEXITCODE -ne 0) {
    throw "Failed to create or update the Prometheus configuration ConfigMap."
}

kubectl apply -f k8s/
kubectl rollout status deployment/chaospulse-deploy --timeout=90s
kubectl rollout restart deployment/chaospulse-prometheus
kubectl rollout status deployment/chaospulse-prometheus --timeout=90s

# 3. Start Jenkins
Write-Host "[3/5] Starting Jenkins CI controller (Port 8080)..." -ForegroundColor Yellow
$jenkinsExists = docker ps -a --filter "name=^/jenkins$" --format "{{.Names}}"
if ($jenkinsExists -eq "jenkins") {
    docker start jenkins | Out-Null
} else {
    docker build -t my-jenkins -f ci/Dockerfile.jenkins .
    docker run -d --name jenkins -p 8080:8080 -p 50000:50000 `
      -v jenkins_home:/var/jenkins_home `
      -v /var/run/docker.sock:/var/run/docker.sock `
      --group-add 0 my-jenkins | Out-Null
}

# 4. Prometheus runs in Minikube and discovers ChaosPulse pods directly.
Write-Host "[4/5] Prometheus pod discovery is deployed in Minikube..." -ForegroundColor Yellow
$legacyPrometheus = docker ps -a --filter "name=^/prometheus$" --format "{{.Names}}"
if ($legacyPrometheus -eq "prometheus") {
    docker rm -f prometheus | Out-Null
}

# 5. Start Grafana with persistent storage volume
Write-Host "[5/5] Starting Grafana with persistent storage (Port 3000)..." -ForegroundColor Yellow
$grafanaExists = docker ps -a --filter "name=^/grafana$" --format "{{.Names}}"
if ($grafanaExists -eq "grafana") {
    docker start grafana | Out-Null
} else {
    docker run -d --name grafana -p 3000:3000 `
      -v grafana_data:/var/lib/grafana `
      grafana/grafana | Out-Null
}

Write-Host ""
Write-Host "====================================================" -ForegroundColor Green
Write-Host "  ALL SERVICES ONLINE" -ForegroundColor Green
Write-Host "  War Room UI : http://localhost:8000"
Write-Host "  Jenkins CI  : http://localhost:8080"
Write-Host "  Prometheus  : http://localhost:9090/targets"
Write-Host "  Grafana     : http://localhost:3000  (admin / admin)"
Write-Host "====================================================" -ForegroundColor Green
Write-Host "Starting app and Prometheus port-forwards (Press Ctrl+C to stop)..." -ForegroundColor Cyan

$kubectlCommand = (Get-Command kubectl -ErrorAction Stop).Source
$prometheusForward = Start-Job -Name "chaospulse-prometheus-port-forward" -ArgumentList $kubectlCommand -ScriptBlock {
    param($KubectlCommand)
    while ($true) {
        & $KubectlCommand port-forward svc/chaospulse-prometheus 9090:9090
        Start-Sleep -Seconds 1
    }
}

try {
    while ($true) {
        kubectl port-forward svc/chaospulse-svc 8000:80
        Write-Host "Reconnecting app tunnel..." -ForegroundColor DarkYellow
        Start-Sleep -Seconds 1
    }
}
finally {
    Stop-Job -Job $prometheusForward -ErrorAction SilentlyContinue
    Remove-Job -Job $prometheusForward -Force -ErrorAction SilentlyContinue
}
