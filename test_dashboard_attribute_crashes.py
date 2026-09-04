"""Dashboards must not crash on real Agent/Driver GPS rows.

Regression: /dashboard/executive queried Agent.name (column is full_name).
/dashboard/delivery ordered DriverLocation.timestamp (column is recorded_at)
and read a non-existent address field. /dashboard/agent did the same for AgentLocation.
"""
from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient

from app.models.database import Agent, AgentLocation, Driver, DriverLocation, SessionLocal
from app.utils.auth import create_session_token
from main import app


def _authed_client():
    client = TestClient(app)
    token = create_session_token(1, "user")
    client.cookies.set("session_token", token)
    return client


def test_executive_dashboard_does_not_crash():
    client = _authed_client()
    r = client.get("/dashboard/executive", headers={"accept": "text/html"})
    assert r.status_code == 200, r.text[:500]
    assert "Rahbariyat Dashboard" in r.text


def test_delivery_dashboard_with_driver_and_gps():
    db = SessionLocal()
    driver = None
    loc = None
    try:
        driver = Driver(code="TST-DRV-1", full_name="Test Haydovchi", is_active=True)
        db.add(driver)
        db.commit()
        db.refresh(driver)
        loc = DriverLocation(
            driver_id=driver.id,
            latitude=41.3,
            longitude=69.2,
            speed=12.0,
            recorded_at=datetime.now(),
        )
        db.add(loc)
        db.commit()

        client = _authed_client()
        r = client.get("/dashboard/delivery", headers={"accept": "text/html"})
        assert r.status_code == 200, r.text[:500]
        assert "Yetkazib berish Dashboard" in r.text
        assert "Test Haydovchi" in r.text
    finally:
        if loc is not None:
            db.delete(loc)
        if driver is not None:
            db.delete(driver)
        db.commit()
        db.close()


def test_dashboard_queries_use_real_column_names():
    """Lock the column names that previously 500'd the HTML dashboards."""
    src = Path("app/routes/dashboard.py").read_text(encoding="utf-8")
    assert "Agent.name" not in src
    assert "Agent.full_name" in src
    assert "DriverLocation.timestamp" not in src
    assert "DriverLocation.recorded_at" in src
    assert "latest_location.address" not in src
    assert "latest_location.latitude" in src
    assert not hasattr(Agent, "name")
    assert hasattr(Agent, "full_name")
    assert not hasattr(DriverLocation, "timestamp")
    assert hasattr(DriverLocation, "recorded_at")
    assert not hasattr(AgentLocation, "address")
    assert not hasattr(DriverLocation, "address")
