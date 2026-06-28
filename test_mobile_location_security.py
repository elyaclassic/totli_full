from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.database import (
    Agent,
    AgentLocation,
    Base,
    Driver,
    DriverLocation,
    get_db,
)
from app.utils.auth import create_session_token
from main import app


def _make_test_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return engine, sessionmaker(autocommit=False, autoflush=False, bind=engine)


def test_agent_location_uses_signed_token_without_csrf_and_correct_agent():
    engine, TestingSessionLocal = _make_test_db()
    db = TestingSessionLocal()

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        db.add_all([
            Agent(id=1, code="AG001", full_name="Wrong Agent", phone="100", is_active=True),
            Agent(id=2, code="AG002", full_name="Right Agent", phone="200", is_active=True),
        ])
        db.commit()

        client = TestClient(app)
        response = client.post(
            "/api/agent/location",
            data={
                "latitude": "41.311081",
                "longitude": "69.240562",
                "accuracy": "10",
                "battery": "87",
                "token": create_session_token(2, "agent"),
            },
        )

        assert response.status_code == 200
        assert response.json()["success"] is True

        locations = db.query(AgentLocation).all()
        assert len(locations) == 1
        assert locations[0].agent_id == 2
        assert locations[0].battery == 87
    finally:
        app.dependency_overrides.pop(get_db, None)
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_agent_location_rejects_non_agent_token_without_writing():
    engine, TestingSessionLocal = _make_test_db()
    db = TestingSessionLocal()

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        db.add(Agent(id=1, code="AG001", full_name="Agent", phone="100", is_active=True))
        db.commit()

        client = TestClient(app)
        response = client.post(
            "/api/agent/location",
            data={
                "latitude": "41.311081",
                "longitude": "69.240562",
                "token": create_session_token(1, "user"),
            },
        )

        assert response.status_code == 200
        assert response.json() == {"success": False, "error": "Invalid token"}
        assert db.query(AgentLocation).count() == 0
    finally:
        app.dependency_overrides.pop(get_db, None)
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_driver_location_token_endpoint_is_not_shadowed_by_legacy_route():
    engine, TestingSessionLocal = _make_test_db()
    db = TestingSessionLocal()

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        db.add(Driver(
            id=5,
            code="DR005",
            full_name="Driver",
            phone="500",
            vehicle_number="01A001AA",
            is_active=True,
        ))
        db.commit()

        client = TestClient(app)
        response = client.post(
            "/api/driver/location",
            data={
                "latitude": "40.1",
                "longitude": "70.2",
                "accuracy": "8",
                "battery": "66",
                "speed": "25.5",
                "token": create_session_token(5, "driver"),
            },
        )

        assert response.status_code == 200
        assert response.json()["success"] is True

        location = db.query(DriverLocation).one()
        assert location.driver_id == 5
        assert location.speed == 25.5
        assert location.battery == 66
    finally:
        app.dependency_overrides.pop(get_db, None)
        db.close()
        Base.metadata.drop_all(bind=engine)
