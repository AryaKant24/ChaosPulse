import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_chaos_state():
    """Ensure every test starts and ends with a clean, nominal Pod state."""
    client.post("/api/chaos/reset")
    yield
    client.post("/api/chaos/reset")


def test_war_room_ui_and_status():
    """Verify the War Room frontend and /api/status telemetry endpoint respond."""
    ui_res = client.get("/")
    assert ui_res.status_code == 200

    status_res = client.get("/api/status")
    assert status_res.status_code == 200
    data = status_res.json()
    assert "pod" in data
    assert data["ready"] is True
    assert data["healthy"] is True
    assert data["monkey"] is False


def test_liveness_probe_and_self_healing_trigger():
    """Verify /healthz returns 200 when healthy and 500 when poisoned."""
    # Nominal state
    res = client.get("/healthz")
    assert res.status_code == 200
    assert res.json()["status"] == "alive"

    # Poison liveness probe
    client.post("/api/chaos/liveness")
    fail_res = client.get("/healthz")
    assert fail_res.status_code == 500
    assert fail_res.json()["status"] == "unhealthy"


def test_readiness_probe_and_traffic_eviction():
    """Verify /readyz returns 200 when ready and 503 when evicted."""
    # Nominal state
    res = client.get("/readyz")
    assert res.status_code == 200
    assert res.json()["status"] == "ready"

    # Trip readiness probe
    client.post("/api/chaos/readiness")
    fail_res = client.get("/readyz")
    assert fail_res.status_code == 503
    assert fail_res.json()["status"] == "not_ready"


def test_work_endpoint_and_latency_injection():
    """Verify /api/work executes and respects artificial latency offsets."""
    res = client.get("/api/work")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

    # Configure a 100ms latency spike
    lat_res = client.post("/api/chaos/latency?ms=100")
    assert lat_res.status_code == 200
    assert lat_res.json()["state"]["latency_ms"] == 100


def test_prometheus_red_metrics_exposed():
    """Verify /metrics exposes Counter, Gauge, and Histogram metric families."""
    client.get("/api/work")
    res = client.get("/metrics")
    assert res.status_code == 200
    body = res.text

    assert "http_requests_total" in body
    assert "in_flight_requests" in body
    assert "http_request_duration_seconds_bucket" in body