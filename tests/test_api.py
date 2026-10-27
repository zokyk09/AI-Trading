import pytest
from fastapi.testclient import TestClient
from backend.main import app


def test_health(monkeypatch):
    monkeypatch.setenv("AI_TRADING_SKIP_MT5_INIT", "1")
    response = TestClient(app).get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "Online"
