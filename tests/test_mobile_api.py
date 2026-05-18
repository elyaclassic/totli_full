from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.database import (
    Agent,
    AgentLocation,
    Base,
    Driver,
    DriverLocation,
    Partner,
)
from main import app, get_db


def make_client(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'mobile_api.db'}",
        connect_args={"check_same_thread": False},
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    try:
        db.add(Agent(id=1, code="A001", full_name="Agent One", phone="998901234567", is_active=True))
        db.add(Driver(id=1, code="D001", full_name="Driver One", phone="998909876543", is_active=True))
        db.add(
            Partner(
                id=1,
                code="P001",
                name="Partner One",
                type="customer",
                phone="998900000000",
                address="Tashkent",
                is_active=True,
            )
        )
        db.commit()
    finally:
        db.close()

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app), TestingSessionLocal


def test_mobile_agent_login_and_location_work_without_csrf(tmp_path):
    client, TestingSessionLocal = make_client(tmp_path)
    try:
        login = client.post(
            "/api/agent/login",
            data={"username": "998901234567", "password": "998901234567"},
        )
        assert login.status_code == 200
        login_payload = login.json()
        assert login_payload["success"] is True

        response = client.post(
            "/api/agent/location",
            data={
                "latitude": "41.311",
                "longitude": "69.279",
                "accuracy": "8",
                "battery": "87",
                "token": login_payload["token"],
            },
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

        db = TestingSessionLocal()
        try:
            location = db.query(AgentLocation).one()
            assert location.agent_id == 1
            assert location.latitude == 41.311
            assert location.battery == 87
        finally:
            db.close()
    finally:
        app.dependency_overrides.clear()


def test_mobile_driver_login_and_location_use_driver_token(tmp_path):
    client, TestingSessionLocal = make_client(tmp_path)
    try:
        login = client.post(
            "/api/driver/login",
            data={"username": "998909876543", "password": "998909876543"},
        )
        assert login.status_code == 200
        login_payload = login.json()
        assert login_payload["success"] is True

        response = client.post(
            "/api/driver/location",
            data={
                "latitude": "40.100",
                "longitude": "70.200",
                "accuracy": "5",
                "battery": "75",
                "speed": "42",
                "token": login_payload["token"],
            },
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

        db = TestingSessionLocal()
        try:
            location = db.query(DriverLocation).one()
            assert location.driver_id == 1
            assert location.speed == 42
            assert location.battery == 75
        finally:
            db.close()
    finally:
        app.dependency_overrides.clear()


def test_mobile_agent_endpoints_reject_driver_tokens(tmp_path):
    client, TestingSessionLocal = make_client(tmp_path)
    try:
        login = client.post(
            "/api/driver/login",
            data={"username": "998909876543", "password": "998909876543"},
        )
        driver_token = login.json()["token"]

        location = client.post(
            "/api/agent/location",
            data={"latitude": "41.311", "longitude": "69.279", "token": driver_token},
        )
        assert location.status_code == 200
        assert location.json() == {"success": False, "error": "Invalid token"}

        partners = client.get("/api/agent/partners", params={"token": driver_token})
        assert partners.status_code == 200
        assert partners.json() == {"success": False, "error": "Invalid token"}

        db = TestingSessionLocal()
        try:
            assert db.query(AgentLocation).count() == 0
        finally:
            db.close()
    finally:
        app.dependency_overrides.clear()
