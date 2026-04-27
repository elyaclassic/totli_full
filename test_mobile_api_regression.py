from fastapi.testclient import TestClient

from app.models.database import Agent, AgentLocation, Driver, DriverLocation, SessionLocal, init_db
from app.utils.auth import create_session_token
from main import app


client = TestClient(app)


def _open_db():
    init_db()
    return SessionLocal()


def _cleanup_agent(db, agent):
    db.query(AgentLocation).filter(AgentLocation.agent_id == agent.id).delete()
    db.delete(agent)
    db.commit()


def _cleanup_driver(db, driver):
    db.query(DriverLocation).filter(DriverLocation.driver_id == driver.id).delete()
    db.delete(driver)
    db.commit()


def _get_or_create_agent(db):
    agent = db.query(Agent).filter(Agent.phone == "+998900000001").first()
    if not agent:
        agent = Agent(code="TESTAG001", full_name="Test Agent", phone="+998900000001", is_active=True)
        db.add(agent)
        db.commit()
        db.refresh(agent)
    return agent


def _get_or_create_driver(db):
    driver = db.query(Driver).filter(Driver.phone == "+998900000002").first()
    if not driver:
        driver = Driver(code="TESTDR001", full_name="Test Driver", phone="+998900000002", is_active=True)
        db.add(driver)
        db.commit()
        db.refresh(driver)
    return driver


def test_agent_location_accepts_signed_mobile_token_without_csrf_cookie():
    db = _open_db()
    try:
        agent = _get_or_create_agent(db)
        token = create_session_token(agent.id, "agent")

        response = client.post(
            "/api/agent/location",
            data={
                "latitude": "41.311081",
                "longitude": "69.240562",
                "accuracy": "10",
                "battery": "95",
                "token": token,
            },
        )

        assert response.status_code == 200
        assert response.json()["success"] is True
        saved = db.query(AgentLocation).filter(AgentLocation.agent_id == agent.id).order_by(AgentLocation.id.desc()).first()
        assert saved is not None
        assert saved.latitude == 41.311081
    finally:
        _cleanup_agent(db, agent)
        db.close()


def test_driver_location_accepts_signed_mobile_token_without_csrf_cookie():
    db = _open_db()
    try:
        driver = _get_or_create_driver(db)
        token = create_session_token(driver.id, "driver")

        response = client.post(
            "/api/driver/location",
            data={
                "latitude": "40.1",
                "longitude": "70.2",
                "accuracy": "5",
                "battery": "88",
                "token": token,
            },
        )

        assert response.status_code == 200
        assert response.json()["success"] is True
        saved = db.query(DriverLocation).filter(DriverLocation.driver_id == driver.id).order_by(DriverLocation.id.desc()).first()
        assert saved is not None
        assert saved.longitude == 70.2
    finally:
        _cleanup_driver(db, driver)
        db.close()


def test_agent_location_rejects_driver_token():
    db = _open_db()
    try:
        driver = _get_or_create_driver(db)
        token = create_session_token(driver.id, "driver")

        response = client.post(
            "/api/agent/location",
            data={
                "latitude": "41.311081",
                "longitude": "69.240562",
                "accuracy": "10",
                "battery": "95",
                "token": token,
            },
        )

        assert response.status_code == 200
        assert response.json() == {"success": False, "error": "Invalid token"}
    finally:
        _cleanup_driver(db, driver)
        db.close()
