from fastapi.testclient import TestClient

from app.models.database import Agent, AgentLocation, Driver, DriverLocation, SessionLocal
from app.utils.auth import create_session_token
from main import app


client = TestClient(app)


def _cleanup(db, *objects):
    for obj in objects:
        if obj is not None:
            db.delete(obj)
    db.commit()


def test_agent_location_rejects_invalid_token_without_writing():
    db = SessionLocal()
    before = db.query(AgentLocation).count()
    try:
        response = client.post(
            "/api/agent/location",
            data={
                "latitude": "41.311081",
                "longitude": "69.240562",
                "accuracy": "10",
                "battery": "90",
                "token": "not-a-valid-token",
            },
        )
        assert response.status_code == 200
        assert response.json()["success"] is False
        assert db.query(AgentLocation).count() == before
    finally:
        db.close()


def test_agent_location_uses_signed_agent_token_user_id():
    db = SessionLocal()
    db.query(AgentLocation).filter(
        AgentLocation.agent.has(Agent.code == "PYTEST_AGENT_LOCATION")
    ).delete(synchronize_session=False)
    db.query(Agent).filter(Agent.code == "PYTEST_AGENT_LOCATION").delete()
    db.commit()
    agent = Agent(
        code="PYTEST_AGENT_LOCATION",
        full_name="Pytest Agent Location",
        phone="+998900000001",
        is_active=True,
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    token = create_session_token(agent.id, "agent")
    location = None
    try:
        response = client.post(
            "/api/agent/location",
            data={
                "latitude": "41.311081",
                "longitude": "69.240562",
                "accuracy": "10",
                "battery": "90",
                "token": token,
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        location = db.query(AgentLocation).filter(AgentLocation.id == body["location_id"]).one()
        assert location.agent_id == agent.id
    finally:
        _cleanup(db, location, agent)
        db.close()


def test_driver_location_requires_signed_driver_token():
    db = SessionLocal()
    db.query(DriverLocation).filter(
        DriverLocation.driver.has(Driver.code == "PYTEST_DRIVER_LOCATION")
    ).delete(synchronize_session=False)
    db.query(Driver).filter(Driver.code == "PYTEST_DRIVER_LOCATION").delete()
    db.commit()
    driver = Driver(
        code="PYTEST_DRIVER_LOCATION",
        full_name="Pytest Driver Location",
        phone="+998900000002",
        vehicle_number="TEST-001",
        is_active=True,
    )
    db.add(driver)
    db.commit()
    db.refresh(driver)
    token = create_session_token(driver.id, "driver")
    before = db.query(DriverLocation).count()
    location = None
    try:
        spoofed = client.post(
            "/api/driver/location",
            data={
                "driver_code": driver.code,
                "latitude": "41.311081",
                "longitude": "69.240562",
                "speed": "20",
            },
        )
        assert spoofed.status_code == 422
        assert db.query(DriverLocation).count() == before

        response = client.post(
            "/api/driver/location",
            data={
                "latitude": "41.311081",
                "longitude": "69.240562",
                "accuracy": "10",
                "battery": "90",
                "token": token,
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        location = db.query(DriverLocation).filter(DriverLocation.id == body["location_id"]).one()
        assert location.driver_id == driver.id
    finally:
        _cleanup(db, location, driver)
        db.close()
