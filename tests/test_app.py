from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

import app.main as main


client = TestClient(main.app)


@pytest.fixture(autouse=True)
def reset_chaos_state():
    """Keep process-local fault state isolated while preserving cumulative metrics."""
    client.post("/api/chaos/reset")
    yield
    client.post("/api/chaos/reset")


@pytest.fixture
def clock(monkeypatch):
    """Provide a monotonic clock that tests can advance without sleeping."""

    class ControllableClock:
        now = 1_000.0

        def __call__(self):
            return self.now

        def advance(self, seconds):
            self.now += seconds

    controllable = ControllableClock()
    monkeypatch.setattr(main, "monotonic_now", controllable)
    return controllable


def _counter_value(status):
    return main.REQUEST_COUNT.labels(
        endpoint="/api/work", status=str(status), pod=main.POD_NAME
    )._value.get()


def _histogram_count():
    return main.REQUEST_LATENCY.labels(
        endpoint="/api/work", pod=main.POD_NAME
    )._count.get()


def _in_flight_value():
    return main.IN_FLIGHT.labels(pod=main.POD_NAME)._value.get()


def _assert_utc_expiry(value):
    assert isinstance(value, str)
    assert value.endswith("Z")
    parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    assert parsed.tzinfo == timezone.utc


def test_fresh_histogram_has_no_synthetic_observation():
    """This is first so it checks the fresh process before any test issues work."""
    assert _histogram_count() == 0


def test_war_room_ui_and_status():
    ui_res = client.get("/")
    assert ui_res.status_code == 200

    status_res = client.get("/api/status")
    assert status_res.status_code == 200
    data = status_res.json()
    assert data["pod"] == main.POD_NAME
    assert data["ready"] is True
    assert data["healthy"] is True
    assert data["monkey"] is False
    assert data["latency_ms"] == 0
    assert set(data["expires_at"]) == {"monkey", "latency", "readiness", "liveness"}
    assert all(expiry is None for expiry in data["expires_at"].values())


def test_fault_duration_default_and_bounds(clock):
    default_res = client.post("/api/chaos/monkey")
    assert default_res.status_code == 200
    expiry = default_res.json()["expires_at"]["monkey"]
    _assert_utc_expiry(expiry)
    remaining = datetime.fromisoformat(expiry[:-1] + "+00:00") - datetime.now(
        timezone.utc
    )
    assert 55 <= remaining.total_seconds() <= 65

    client.post("/api/chaos/reset")
    max_res = client.post("/api/chaos/monkey?duration_s=300")
    assert max_res.status_code == 200
    _assert_utc_expiry(max_res.json()["expires_at"]["monkey"])

    assert client.post("/api/chaos/monkey?duration_s=0").status_code == 422
    assert client.post("/api/chaos/monkey?duration_s=301").status_code == 422


@pytest.mark.parametrize(
    ("action", "query", "status_key", "active_value", "nominal_value", "probe"),
    [
        ("monkey", "", "monkey", True, False, None),
        ("latency", "&ms=125", "latency_ms", 125, 0, None),
        ("readiness", "", "ready", False, True, "/readyz"),
        ("liveness", "", "healthy", False, True, "/healthz"),
    ],
)
def test_each_supported_fault_expires(
    clock, action, query, status_key, active_value, nominal_value, probe
):
    control = client.post(
        f"/api/chaos/{action}?duration_s=2{query}"
    )
    assert control.status_code == 200
    body = control.json()
    assert body["pod"] == main.POD_NAME
    expiry_key = {
        "monkey": "monkey",
        "latency": "latency",
        "readiness": "readiness",
        "liveness": "liveness",
    }[action]
    _assert_utc_expiry(body["expires_at"][expiry_key])
    assert body["state"][status_key] == active_value

    before_expiry = client.get("/api/status").json()
    assert before_expiry[status_key] == active_value
    clock.advance(1.99)
    assert client.get("/api/status").json()[status_key] == active_value

    clock.advance(0.02)
    if probe:
        assert client.get(probe).status_code == 200
    after_expiry = client.get("/api/status").json()
    assert after_expiry[status_key] == nominal_value
    assert after_expiry["expires_at"][expiry_key] is None


def test_work_reconciles_faults_that_expire_during_simulated_delay(
    clock, monkeypatch
):
    def advance_past_expiry(_low, _high):
        clock.advance(2.1)
        return 0.01

    monkeypatch.setattr(main.random, "uniform", advance_past_expiry)
    monkeypatch.setattr(main.random, "random", lambda: 0.1)
    client.post("/api/chaos/monkey?duration_s=2")

    response = client.get("/api/work")

    assert response.status_code == 200
    assert client.get("/api/status").json()["monkey"] is False


def test_liveness_and_readiness_probe_codes_while_fault_active(clock):
    client.post("/api/chaos/liveness?duration_s=30")
    assert client.get("/healthz").status_code == 500
    clock.advance(31)
    assert client.get("/healthz").status_code == 200

    client.post("/api/chaos/readiness?duration_s=30")
    assert client.get("/readyz").status_code == 503
    clock.advance(31)
    assert client.get("/readyz").status_code == 200


def test_reset_clears_faults_and_expiries_but_preserves_counters(clock):
    work = client.get("/api/work")
    assert work.status_code == 200

    client.post("/api/chaos/monkey?duration_s=40")
    client.post("/api/chaos/latency?ms=120&duration_s=40")
    client.post("/api/chaos/readiness?duration_s=40")
    client.post("/api/chaos/liveness?duration_s=40")
    before = client.get("/api/status").json()
    before_metrics = (_counter_value(200), _counter_value(500), _histogram_count())

    reset = client.post("/api/chaos/reset")
    assert reset.status_code == 200
    after = client.get("/api/status").json()
    after_metrics = (_counter_value(200), _counter_value(500), _histogram_count())

    assert after["pod"] == before["pod"] == main.POD_NAME
    assert after["monkey"] is False
    assert after["latency_ms"] == 0
    assert after["ready"] is True
    assert after["healthy"] is True
    assert all(expiry is None for expiry in after["expires_at"].values())
    assert after["local_ok"] == before["local_ok"]
    assert after["local_err"] == before["local_err"]
    assert after_metrics == before_metrics


def test_latency_is_clamped_and_measured(clock, monkeypatch):
    below = client.post("/api/chaos/latency?ms=-50")
    assert below.status_code == 200
    assert below.json()["state"]["latency_ms"] == 0

    above = client.post("/api/chaos/latency?ms=6000")
    assert above.status_code == 200
    assert above.json()["state"]["latency_ms"] == 5000
    client.post("/api/chaos/reset")

    monkeypatch.setattr(main.random, "uniform", lambda _low, _high: 0.01)
    configured = client.post("/api/chaos/latency?ms=100")
    assert configured.status_code == 200
    work = client.get("/api/work")
    assert work.status_code == 200
    assert work.json()["latency_ms"] >= 95
    assert work.json()["latency_ms"] < 1000


def test_monkey_success_and_failure_are_deterministic(monkeypatch):
    client.post("/api/chaos/monkey?duration_s=60")
    before_200 = _counter_value(200)
    before_500 = _counter_value(500)
    before_histogram = _histogram_count()
    before_status = client.get("/api/status").json()

    monkeypatch.setattr(main.random, "uniform", lambda _low, _high: 0.01)
    monkeypatch.setattr(main.random, "random", lambda: 0.1)
    failed = client.get("/api/work")
    assert failed.status_code == 500
    assert failed.json()["pod"] == main.POD_NAME
    assert _counter_value(500) == before_500 + 1
    assert _counter_value(200) == before_200
    assert _histogram_count() == before_histogram + 1
    assert _in_flight_value() == 0
    failed_status = client.get("/api/status").json()
    assert failed_status["local_err"] == before_status["local_err"] + 1

    monkeypatch.setattr(main.random, "random", lambda: 0.9)
    succeeded = client.get("/api/work")
    assert succeeded.status_code == 200
    assert _counter_value(200) == before_200 + 1
    assert _counter_value(500) == before_500 + 1
    assert _histogram_count() == before_histogram + 2
    assert _in_flight_value() == 0
    succeeded_status = client.get("/api/status").json()
    assert succeeded_status["local_ok"] == before_status["local_ok"] + 1


def test_work_gauge_is_cleaned_up_when_work_raises(monkeypatch):
    def fail_random_delay(_low, _high):
        raise RuntimeError("simulated delay calculation failure")

    monkeypatch.setattr(main.random, "uniform", fail_random_delay)
    with pytest.raises(RuntimeError, match="simulated delay calculation failure"):
        client.get("/api/work")
    assert _in_flight_value() == 0


def test_invalid_chaos_action_is_rejected():
    response = client.post("/api/chaos/unknown")
    assert response.status_code == 400
    assert response.json()["error"] == "Unknown action: unknown"


def test_metrics_are_exposed():
    before_200 = _counter_value(200)
    before_histogram = _histogram_count()
    response = client.get("/api/work")
    assert response.status_code == 200

    metrics = client.get("/metrics")
    assert metrics.status_code == 200
    assert "http_requests_total" in metrics.text
    assert "in_flight_requests" in metrics.text
    assert "http_request_duration_seconds_bucket" in metrics.text
    assert _counter_value(200) == before_200 + 1
    assert _histogram_count() == before_histogram + 1
    assert _in_flight_value() == 0
