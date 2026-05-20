from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import main as app_main
from app.models.database import Base, Agent, AgentLocation, Driver, DriverLocation
from app.utils.auth import create_session_token


def _make_client(db_session):
    def override_get_db():
        yield db_session

    app_main.app.dependency_overrides[app_main.get_db] = override_get_db
    return TestClient(app_main.app)


def _make_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return engine, SessionLocal()


def test_agent_location_uses_signed_mobile_token_actor_without_csrf():
    engine, db = _make_session()
    client = _make_client(db)
    try:
        first_agent = Agent(code="A001", full_name="First Agent", phone="+100", is_active=True)
        second_agent = Agent(code="A002", full_name="Second Agent", phone="+200", is_active=True)
        db.add_all([first_agent, second_agent])
        db.commit()
        db.refresh(first_agent)
        db.refresh(second_agent)

        token = create_session_token(second_agent.id, "agent")
        response = client.post(
            "/api/agent/location",
            data={
                "latitude": "41.311081",
                "longitude": "69.240562",
                "accuracy": "5",
                "battery": "88",
                "token": token,
            },
        )

        assert response.status_code == 200
        assert response.json()["success"] is True
        location = db.query(AgentLocation).one()
        assert location.agent_id == second_agent.id
        assert location.agent_id != first_agent.id
    finally:
        app_main.app.dependency_overrides.clear()
        client.close()
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_driver_location_accepts_signed_mobile_token_without_shadow_route_or_csrf():
    engine, db = _make_session()
    client = _make_client(db)
    try:
        driver = Driver(
            code="D001",
            full_name="Mobile Driver",
            phone="+300",
            vehicle_number="01A001AA",
            is_active=True,
        )
        db.add(driver)
        db.commit()
        db.refresh(driver)

        token = create_session_token(driver.id, "driver")
        response = client.post(
            "/api/driver/location",
            data={
                "latitude": "41.311081",
                "longitude": "69.240562",
                "accuracy": "7",
                "battery": "64",
                "token": token,
            },
        )

        assert response.status_code == 200
        assert response.json()["success"] is True
        location = db.query(DriverLocation).one()
        assert location.driver_id == driver.id
    finally:
        app_main.app.dependency_overrides.clear()
        client.close()
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
