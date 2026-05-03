from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.models.database import Agent, AgentLocation, Base, get_db
from app.utils.auth import create_session_token
from main import app


def _client_with_temp_db(tmp_path):
    db_path = tmp_path / "pwa_auth.db"
    engine = create_engine(
        f"sqlite:///{db_path}",
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

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app), TestingSessionLocal


def _csrf_headers(client):
    response = client.get("/login")
    token = response.cookies.get("csrf_token")
    assert token
    return {"X-CSRF-Token": token}


def test_agent_location_rejects_invalid_token_without_writing(tmp_path):
    client, SessionLocal = _client_with_temp_db(tmp_path)
    try:
        with SessionLocal() as db:
            db.add(Agent(id=1, code="A001", full_name="Agent One", phone="100", is_active=True))
            db.commit()

        response = client.post(
            "/api/agent/location",
            data={
                "latitude": "41.3111",
                "longitude": "69.2797",
                "token": "not-a-valid-token",
            },
            headers=_csrf_headers(client),
        )

        assert response.status_code == 200
        assert response.json()["success"] is False
        with SessionLocal() as db:
            assert db.query(AgentLocation).count() == 0
    finally:
        app.dependency_overrides.clear()


def test_agent_location_uses_authenticated_agent_id(tmp_path):
    client, SessionLocal = _client_with_temp_db(tmp_path)
    try:
        with SessionLocal() as db:
            db.add_all([
                Agent(id=1, code="A001", full_name="Agent One", phone="100", is_active=True),
                Agent(id=2, code="A002", full_name="Agent Two", phone="200", is_active=True),
            ])
            db.commit()

        response = client.post(
            "/api/agent/location",
            data={
                "latitude": "41.3111",
                "longitude": "69.2797",
                "token": create_session_token(2, "agent"),
            },
            headers=_csrf_headers(client),
        )

        assert response.status_code == 200
        assert response.json()["success"] is True
        with SessionLocal() as db:
            location = db.query(AgentLocation).one()
            assert location.agent_id == 2
    finally:
        app.dependency_overrides.clear()
