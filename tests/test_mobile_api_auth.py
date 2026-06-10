import os
import sys
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import main
import app.models.database as dbm
from app.models.database import Base, Agent, AgentLocation, Driver, DriverLocation
from app.utils.auth import create_session_token


@pytest.fixture()
def mobile_api_client():
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    seed = TestingSessionLocal()
    seed.add(Agent(id=1, code="A1", full_name="Agent One", phone="+100", is_active=True))
    seed.add(Driver(id=1, code="D1", full_name="Driver One", phone="+200", is_active=True))
    seed.commit()
    seed.close()

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    main.app.dependency_overrides[dbm.get_db] = override_get_db
    main.app.dependency_overrides[main.get_db] = override_get_db
    client = TestClient(main.app)
    try:
        yield client, TestingSessionLocal
    finally:
        main.app.dependency_overrides.clear()
        engine.dispose()
        os.remove(db_path)


def test_agent_location_rejects_invalid_token_without_writing(mobile_api_client):
    client, SessionLocal = mobile_api_client

    response = client.post(
        "/api/agent/location",
        data={
            "latitude": 41.1,
            "longitude": 69.2,
            "accuracy": 5,
            "battery": 77,
            "token": "not-a-valid-token",
        },
    )

    db = SessionLocal()
    try:
        assert response.status_code == 200
        assert response.json() == {"success": False, "error": "Invalid token"}
        assert db.query(AgentLocation).count() == 0
    finally:
        db.close()


def test_driver_location_rejects_legacy_driver_code_only_post(mobile_api_client):
    client, SessionLocal = mobile_api_client

    response = client.post(
        "/api/driver/location",
        data={
            "driver_code": "D1",
            "latitude": 41.2,
            "longitude": 69.3,
            "speed": 12,
        },
    )

    db = SessionLocal()
    try:
        assert response.status_code == 422
        assert db.query(DriverLocation).count() == 0
    finally:
        db.close()


def test_mobile_location_tokens_work_without_csrf_cookie(mobile_api_client):
    client, SessionLocal = mobile_api_client
    agent_token = create_session_token(1, "agent")
    driver_token = create_session_token(1, "driver")

    agent_response = client.post(
        "/api/agent/location",
        data={
            "latitude": 41.1,
            "longitude": 69.2,
            "accuracy": 5,
            "battery": 77,
            "token": agent_token,
        },
    )
    driver_response = client.post(
        "/api/driver/location",
        data={
            "latitude": 41.2,
            "longitude": 69.3,
            "accuracy": 6,
            "battery": 66,
            "token": driver_token,
        },
    )

    db = SessionLocal()
    try:
        assert agent_response.status_code == 200
        assert agent_response.json()["success"] is True
        assert driver_response.status_code == 200
        assert driver_response.json()["success"] is True
        assert db.query(AgentLocation).count() == 1
        assert db.query(DriverLocation).count() == 1
    finally:
        db.close()
