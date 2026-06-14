from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import main as app_module
from app.models.database import (
    Agent,
    AgentLocation,
    Base,
    Driver,
    DriverLocation,
    Partner,
)
from app.utils.auth import create_session_token


def make_client(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'pwa_api.db'}",
        connect_args={"check_same_thread": False},
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app_module.app.dependency_overrides[app_module.get_db] = override_get_db
    return TestClient(app_module.app), TestingSessionLocal


def test_agent_login_and_location_use_signed_token_without_csrf(tmp_path):
    client, SessionLocal = make_client(tmp_path)
    db = SessionLocal()
    try:
        agent = Agent(code="AG001", full_name="Test Agent", phone="+998901111111", is_active=True)
        db.add(agent)
        db.commit()
        db.refresh(agent)
    finally:
        db.close()

    login_response = client.post(
        "/api/agent/login",
        data={"username": "+998901111111", "password": "+998901111111"},
    )
    assert login_response.status_code == 200
    login_body = login_response.json()
    assert login_body["success"] is True
    assert login_body["user"]["id"] == agent.id
    assert login_body["user"]["user_type"] == "agent"

    location_response = client.post(
        "/api/agent/location",
        data={
            "latitude": "41.311081",
            "longitude": "69.240562",
            "accuracy": "5",
            "battery": "88",
            "token": login_body["token"],
        },
    )
    assert location_response.status_code == 200
    assert location_response.json()["success"] is True

    db = SessionLocal()
    try:
        location = db.query(AgentLocation).one()
        assert location.agent_id == agent.id
        assert location.latitude == 41.311081
        assert location.battery == 88
    finally:
        db.close()
        app_module.app.dependency_overrides.clear()


def test_agent_location_rejects_cross_role_token(tmp_path):
    client, SessionLocal = make_client(tmp_path)
    db = SessionLocal()
    try:
        driver = Driver(code="DR001", full_name="Test Driver", phone="+998902222222", is_active=True)
        db.add(driver)
        db.commit()
        db.refresh(driver)
        driver_token = create_session_token(driver.id, "driver")
    finally:
        db.close()

    response = client.post(
        "/api/agent/location",
        data={
            "latitude": "41.0",
            "longitude": "69.0",
            "token": driver_token,
        },
    )
    assert response.status_code == 200
    assert response.json() == {"success": False, "error": "Invalid token"}

    db = SessionLocal()
    try:
        assert db.query(AgentLocation).count() == 0
    finally:
        db.close()
        app_module.app.dependency_overrides.clear()


def test_driver_location_no_longer_accepts_driver_code_without_token(tmp_path):
    client, SessionLocal = make_client(tmp_path)
    db = SessionLocal()
    try:
        driver = Driver(code="DR002", full_name="Secure Driver", phone="+998903333333", is_active=True)
        db.add(driver)
        db.commit()
        db.refresh(driver)
    finally:
        db.close()

    legacy_response = client.post(
        "/api/driver/location",
        data={
            "driver_code": "DR002",
            "latitude": "41.5",
            "longitude": "69.5",
            "speed": "30",
        },
    )
    assert legacy_response.status_code == 422

    login_response = client.post(
        "/api/driver/login",
        data={"username": "+998903333333", "password": "+998903333333"},
    )
    token = login_response.json()["token"]
    secure_response = client.post(
        "/api/driver/location",
        data={
            "latitude": "41.5",
            "longitude": "69.5",
            "accuracy": "7",
            "battery": "76",
            "speed": "30",
            "token": token,
        },
    )
    assert secure_response.status_code == 200
    assert secure_response.json()["success"] is True

    db = SessionLocal()
    try:
        location = db.query(DriverLocation).one()
        assert location.driver_id == driver.id
        assert location.speed == 30
    finally:
        db.close()
        app_module.app.dependency_overrides.clear()


def test_agent_partners_requires_agent_token(tmp_path):
    client, SessionLocal = make_client(tmp_path)
    db = SessionLocal()
    try:
        agent = Agent(code="AG002", full_name="Partner Agent", phone="+998904444444", is_active=True)
        driver = Driver(code="DR003", full_name="Partner Driver", phone="+998905555555", is_active=True)
        partner = Partner(
            code="P001",
            name="Customer One",
            type="customer",
            phone="+998901234567",
            address="Tashkent",
            is_active=True,
        )
        db.add_all([agent, driver, partner])
        db.commit()
        db.refresh(agent)
        db.refresh(driver)
    finally:
        db.close()

    driver_token = create_session_token(driver.id, "driver")
    driver_response = client.get(f"/api/agent/partners?token={driver_token}")
    assert driver_response.status_code == 200
    assert driver_response.json() == {"success": False, "error": "Invalid token"}

    agent_token = create_session_token(agent.id, "agent")
    agent_response = client.get(f"/api/agent/partners?token={agent_token}")
    assert agent_response.status_code == 200
    body = agent_response.json()
    assert body["success"] is True
    assert body["partners"] == [
        {"id": 1, "name": "Customer One", "phone": "+998901234567", "address": "Tashkent"}
    ]

    app_module.app.dependency_overrides.clear()
