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
)
from app.utils.auth import create_session_token


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = session_local()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    main.app.dependency_overrides[main.get_db] = override_get_db
    try:
        yield TestClient(main.app)
    finally:
        main.app.dependency_overrides.clear()


def test_agent_location_rejects_invalid_token(client, db_session):
    response = client.post(
        "/api/agent/location",
        data={
            "latitude": 41.311081,
            "longitude": 69.240562,
            "accuracy": 10,
            "battery": 90,
            "token": "not-a-valid-token",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"success": False, "error": "Invalid token"}
    assert db_session.query(AgentLocation).count() == 0


def test_agent_location_uses_token_agent_id(client, db_session):
    agent = Agent(id=42, code="A42", full_name="Agent 42", phone="+998901234242", is_active=True)
    db_session.add(agent)
    db_session.commit()

    response = client.post(
        "/api/agent/location",
        data={
            "latitude": 41.311081,
            "longitude": 69.240562,
            "accuracy": 10,
            "battery": 90,
            "token": create_session_token(agent.id, "agent"),
        },
    )

    assert response.status_code == 200
    assert response.json()["success"] is True
    location = db_session.query(AgentLocation).one()
    assert location.agent_id == agent.id


def test_driver_location_uses_token_route(client, db_session):
    driver = Driver(id=7, code="D7", full_name="Driver 7", phone="+998901234007", is_active=True)
    db_session.add(driver)
    db_session.commit()

    response = client.post(
        "/api/driver/location",
        data={
            "latitude": 40.0,
            "longitude": 70.0,
            "accuracy": 5,
            "battery": 80,
            "token": create_session_token(driver.id, "driver"),
        },
    )

    assert response.status_code == 200
    assert response.json()["success"] is True
    location = db_session.query(DriverLocation).one()
    assert location.driver_id == driver.id


def test_agent_partners_rejects_driver_token(client, db_session):
    driver = Driver(id=8, code="D8", full_name="Driver 8", phone="+998901234008", is_active=True)
    db_session.add_all([
        driver,
        Partner(code="P1", name="Sensitive Partner", type="customer", is_active=True),
    ])
    db_session.commit()

    response = client.get(
        "/api/agent/partners",
        params={"token": create_session_token(driver.id, "driver")},
    )

    assert response.status_code == 200
    assert response.json() == {"success": False, "error": "Invalid token"}
