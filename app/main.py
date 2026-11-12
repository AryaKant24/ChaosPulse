import asyncio
import os
import random
import socket
import time
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Query, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    REGISTRY,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

app = FastAPI(
    title="ChaosPulse SRE War Room",
    description="Cloud-Native Chaos Engineering & Prometheus Telemetry Microservice",
    version="2.0.0",
)

POD_NAME = os.getenv("HOSTNAME", socket.gethostname())
START_TIME = time.time()
STATIC_DIR = Path(__file__).resolve().parent / "static"

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# In-memory chaos state per Pod replica
state = {
    "monkey": False,         # Injects 50% HTTP 500 errors on /api/work
    "latency_ms": 0,         # Artificial delay added to /api/work (ms)
    "ready": True,           # Controls /readyz (Kubernetes Readiness Probe)
    "healthy": True,         # Controls /healthz (Kubernetes Liveness Probe)
    "local_ok": 0,           # Local Pod 200 counter for War Room UI
    "local_err": 0,          # Local Pod 500 counter for War Room UI
}


def get_or_create_counter(name: str, doc: str, labelnames: list[str]) -> Counter:
    if name in REGISTRY._names_to_collectors:
        return REGISTRY._names_to_collectors[name]  # type: ignore[return-value]
    return Counter(name, doc, labelnames)


def get_or_create_gauge(name: str, doc: str, labelnames: list[str]) -> Gauge:
    if name in REGISTRY._names_to_collectors:
        return REGISTRY._names_to_collectors[name]  # type: ignore[return-value]
    return Gauge(name, doc, labelnames)


def get_or_create_histogram(
    name: str, doc: str, labelnames: list[str], buckets: tuple[float, ...]
) -> Histogram:
    if name in REGISTRY._names_to_collectors:
        return REGISTRY._names_to_collectors[name]  # type: ignore[return-value]
    return Histogram(name, doc, labelnames, buckets=buckets)


# Prometheus RED Metrics
REQUEST_COUNT = get_or_create_counter(
    "http_requests_total",
    "Total HTTP requests processed by ChaosPulse",
    ["endpoint", "status", "pod"],
)
IN_FLIGHT = get_or_create_gauge(
    "in_flight_requests",
    "Number of HTTP requests currently in flight",
    ["pod"],
)
REQUEST_LATENCY = get_or_create_histogram(
    "http_request_duration_seconds",
    "HTTP request latency distribution in seconds",
    ["endpoint", "pod"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

# Pre-initialize time series so /metrics immediately exposes all families for pytest & Grafana
REQUEST_COUNT.labels(endpoint="/api/work", status="200", pod=POD_NAME).inc(0)
REQUEST_COUNT.labels(endpoint="/api/work", status="500", pod=POD_NAME).inc(0)
IN_FLIGHT.labels(pod=POD_NAME).set(0)
REQUEST_LATENCY.labels(endpoint="/api/work", pod=POD_NAME).observe(0.005)


@app.get("/", include_in_schema=False)
async def root():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return JSONResponse({"service": "ChaosPulse", "pod": POD_NAME, "status": "running"})


@app.get("/api/status")
async def get_status():
    """Returns live Pod identity, probe statuses, and chaos flags for the War Room UI."""
    return {
        "pod": POD_NAME,
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "monkey": state["monkey"],
        "latency_ms": state["latency_ms"],
        "ready": state["ready"],
        "healthy": state["healthy"],
        "local_ok": state["local_ok"],
        "local_err": state["local_err"],
    }


@app.get("/healthz")
async def healthz():
    """Kubernetes Liveness Probe: returns 500 when poisoned to trigger a container restart."""
    if not state["healthy"]:
        return JSONResponse(
            status_code=500,
            content={"status": "unhealthy", "pod": POD_NAME, "probe": "liveness"},
        )
    return {"status": "alive", "pod": POD_NAME}


@app.get("/readyz")
async def readyz():
    """Kubernetes Readiness Probe: returns 503 to evict Pod from Service endpoints."""
    if not state["ready"]:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "pod": POD_NAME, "probe": "readiness"},
        )
    return {"status": "ready", "pod": POD_NAME}


@app.get("/api/work")
async def do_work():
    """Simulates workload execution and records Prometheus Counter, Gauge, and Histogram metrics."""
    IN_FLIGHT.labels(pod=POD_NAME).inc()
    start = time.perf_counter()
    try:
        # Base jitter (10-45ms) + optional artificial latency spike
        base_delay = random.uniform(0.01, 0.045)
        extra_delay = state["latency_ms"] / 1000.0
        await asyncio.sleep(base_delay + extra_delay)

        # Chaos Monkey: 50% chance of throwing HTTP 500 when enabled
        if state["monkey"] and random.random() < 0.5:
            state["local_err"] += 1
            REQUEST_COUNT.labels(endpoint="/api/work", status="500", pod=POD_NAME).inc()
            duration = time.perf_counter() - start
            REQUEST_LATENCY.labels(endpoint="/api/work", pod=POD_NAME).observe(duration)
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "message": "Chaos Monkey sabotaged request!",
                    "pod": POD_NAME,
                    "latency_ms": round(duration * 1000, 1),
                },
            )

        state["local_ok"] += 1
        REQUEST_COUNT.labels(endpoint="/api/work", status="200", pod=POD_NAME).inc()
        duration = time.perf_counter() - start
        REQUEST_LATENCY.labels(endpoint="/api/work", pod=POD_NAME).observe(duration)
        return {
            "status": "ok",
            "pod": POD_NAME,
            "latency_ms": round(duration * 1000, 1),
        }
    finally:
        IN_FLIGHT.labels(pod=POD_NAME).dec()


@app.post("/api/chaos/{action}")
@app.get("/api/chaos/{action}")
async def trigger_chaos(
    action: str,
    ms: Optional[int] = Query(default=None, description="Optional latency in ms"),
):
    """Toggles or resets chaos modes for the current Pod replica."""
    if action == "monkey":
        state["monkey"] = not state["monkey"]
    elif action == "latency":
        if ms is not None:
            state["latency_ms"] = max(0, min(ms, 5000))
        else:
            state["latency_ms"] = 0 if state["latency_ms"] > 0 else 600
    elif action == "readiness":
        state["ready"] = not state["ready"]
    elif action == "liveness":
        state["healthy"] = not state["healthy"]
    elif action == "reset":
        state["monkey"] = False
        state["latency_ms"] = 0
        state["ready"] = True
        state["healthy"] = True
    else:
        return JSONResponse(status_code=400, content={"error": f"Unknown action: {action}"})

    return {
        "action": action,
        "pod": POD_NAME,
        "state": state,
    }


@app.get("/metrics")
async def metrics():
    """Prometheus scrape endpoint."""
    return Response(generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)