import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import main
from app.models.database import (
    Base,
    Agent,
    AgentLocation,
    Driver,
    DriverLocation,
    Partner,
    User,
)
from app.utils.auth import create_session_token, get_user_from_token


@pytest.fixture()
def db_session(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    original_overrides = dict(main.app.dependency_overrides)
    main.app.dependency_overrides[main.get_db] = override_get_db
    monkeypatch.setattr(main, "SessionLocal", TestingSessionLocal)

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        main.app.dependency_overrides.clear()
        main.app.dependency_overrides.update(original_overrides)


@pytest.fixture()
def client(db_session):
    return TestClient(main.app)


def seed_mobile_subjects(db):
    user = User(
        id=1,
        username="admin",
        password_hash="unused",
        full_name="Admin",
        role="admin",
        is_active=True,
    )
    agent = Agent(
        id=1,
        code="A001",
        full_name="Agent One",
        phone="+998900000001",
        is_active=True,
    )
    driver = Driver(
        id=2,
        code="D002",
        full_name="Driver Two",
        phone="+998900000002",
        vehicle_number="01A001AA",
        is_active=True,
    )
    partner = Partner(
        id=1,
        code="P001",
        name="Sensitive Partner",
        type="customer",
        phone="+998900000003",
        address="Private address",
        is_active=True,
    )
    db.add_all([user, agent, driver, partner])
    db.commit()
    return user, agent, driver, partner


def test_pwa_token_cannot_authenticate_web_api(client, db_session):
    _, agent, _, _ = seed_mobile_subjects(db_session)
    pwa_token = create_session_token(agent.id, "agent")

    response = client.get("/api/agents/locations", cookies={"session_token": pwa_token})

    assert response.status_code == 401


def test_agent_login_mints_agent_token(client, db_session):
    _, agent, _, _ = seed_mobile_subjects(db_session)

    response = client.post(
        "/api/agent/login",
        data={"username": agent.phone, "password": agent.phone},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert get_user_from_token(payload["token"])["user_type"] == "agent"


def test_agent_location_requires_valid_active_agent_token(client, db_session):
    _, agent, driver, _ = seed_mobile_subjects(db_session)
    driver_token = create_session_token(driver.id, "driver")
    agent_token = create_session_token(agent.id, "agent")

    rejected = client.post(
        "/api/agent/location",
        data={
            "latitude": "41.311081",
            "longitude": "69.240562",
            "accuracy": "8",
            "battery": "95",
            "token": driver_token,
        },
    )

    assert rejected.status_code == 200
    assert rejected.json()["success"] is False
    assert db_session.query(AgentLocation).count() == 0

    accepted = client.post(
        "/api/agent/location",
        data={
            "latitude": "41.311081",
            "longitude": "69.240562",
            "accuracy": "8",
            "battery": "95",
            "token": agent_token,
        },
    )

    assert accepted.status_code == 200
    assert accepted.json()["success"] is True
    location = db_session.query(AgentLocation).one()
    assert location.agent_id == agent.id


def test_driver_location_no_longer_accepts_driver_code(client, db_session):
    _, _, driver, _ = seed_mobile_subjects(db_session)

    rejected = client.post(
        "/api/driver/location",
        data={
            "driver_code": driver.code,
            "latitude": "41.311081",
            "longitude": "69.240562",
            "speed": "10",
        },
    )

    assert rejected.status_code == 422
    assert db_session.query(DriverLocation).count() == 0


def test_driver_location_requires_driver_token(client, db_session):
    _, agent, driver, _ = seed_mobile_subjects(db_session)
    agent_token = create_session_token(agent.id, "agent")
    driver_token = create_session_token(driver.id, "driver")

    rejected = client.post(
        "/api/driver/location",
        data={
            "latitude": "41.311081",
            "longitude": "69.240562",
            "accuracy": "7",
            "battery": "90",
            "token": agent_token,
        },
    )

    assert rejected.status_code == 200
    assert rejected.json()["success"] is False
    assert db_session.query(DriverLocation).count() == 0

    accepted = client.post(
        "/api/driver/location",
        data={
            "latitude": "41.311081",
            "longitude": "69.240562",
            "accuracy": "7",
            "battery": "90",
            "token": driver_token,
        },
    )

    assert accepted.status_code == 200
    assert accepted.json()["success"] is True
    location = db_session.query(DriverLocation).one()
    assert location.driver_id == driver.id


def test_agent_partners_rejects_non_agent_tokens(client, db_session):
    _, _, driver, _ = seed_mobile_subjects(db_session)
    driver_token = create_session_token(driver.id, "driver")

    response = client.get(f"/api/agent/partners?token={driver_token}")

    assert response.status_code == 200
    assert response.json() == {"success": False, "error": "Invalid token"}
