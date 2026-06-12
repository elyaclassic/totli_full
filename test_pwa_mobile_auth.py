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
    Partner,
    get_db,
)
from app.utils.auth import create_session_token
from main import app


def make_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = testing_session()

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    return client, db


def close_client(client, db):
    client.close()
    db.close()
    app.dependency_overrides.clear()


def test_agent_location_uses_signed_token_identity_without_csrf_cookie():
    client, db = make_client()
    try:
        first_agent = Agent(code="A1", full_name="Wrong Agent", phone="100", is_active=True)
        signed_agent = Agent(code="A2", full_name="Signed Agent", phone="200", is_active=True)
        db.add_all([first_agent, signed_agent])
        db.commit()

        token = create_session_token(signed_agent.id, "agent")
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
        assert response.json()["success"] is True
        location = db.query(AgentLocation).one()
        assert location.agent_id == signed_agent.id
    finally:
        close_client(client, db)


def test_driver_location_uses_pwa_token_route_without_csrf_cookie():
    client, db = make_client()
    try:
        driver = Driver(
            code="D1",
            full_name="Driver One",
            phone="300",
            vehicle_number="01A001AA",
            is_active=True,
        )
        db.add(driver)
        db.commit()

        token = create_session_token(driver.id, "driver")
        response = client.post(
            "/api/driver/location",
            data={
                "latitude": "41.311081",
                "longitude": "69.240562",
                "accuracy": "10",
                "battery": "80",
                "token": token,
            },
        )

        assert response.status_code == 200
        assert response.json()["success"] is True
        location = db.query(DriverLocation).one()
        assert location.driver_id == driver.id
    finally:
        close_client(client, db)


def test_driver_token_cannot_read_agent_partner_list():
    client, db = make_client()
    try:
        driver = Driver(
            code="D1",
            full_name="Driver One",
            phone="300",
            vehicle_number="01A001AA",
            is_active=True,
        )
        partner = Partner(
            code="P1",
            name="Customer",
            type="customer",
            phone="400",
            address="Tashkent",
            is_active=True,
        )
        db.add_all([driver, partner])
        db.commit()

        token = create_session_token(driver.id, "driver")
        response = client.get(f"/api/agent/partners?token={token}")

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is False
        assert "partners" not in body
    finally:
        close_client(client, db)
