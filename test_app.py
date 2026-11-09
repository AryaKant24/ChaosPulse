from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_probes():
    assert client.get("/healthz").status_code == 200
    assert client.get("/readyz").status_code == 200

def test_metrics():
    res = client.get("/metrics")
    assert res.status_code == 200
    assert "http_requests_total" in res.text