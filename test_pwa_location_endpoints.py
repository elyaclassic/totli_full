import asyncio

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.database import Base, Agent, AgentLocation, Driver, DriverLocation
from app.utils.auth import create_session_token
from main import agent_location_update, driver_location_update


@pytest.fixture()
def db_session(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'pwa_location.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_agent_location_uses_authenticated_agent_id(db_session):
    first_agent = Agent(code="AG001", full_name="First Agent", phone="+998900000001", is_active=True)
    second_agent = Agent(code="AG002", full_name="Second Agent", phone="+998900000002", is_active=True)
    db_session.add_all([first_agent, second_agent])
    db_session.commit()

    token = create_session_token(second_agent.id, "agent")

    response = asyncio.run(
        agent_location_update(
            latitude=41.311081,
            longitude=69.240562,
            accuracy=8,
            battery=90,
            token=token,
            db=db_session,
        )
    )

    assert response["success"] is True
    location = db_session.query(AgentLocation).one()
    assert location.agent_id == second_agent.id


def test_driver_location_accepts_driver_login_token(db_session):
    driver = Driver(
        code="DR001",
        full_name="Driver One",
        phone="+998901111111",
        vehicle_number="01A001AA",
        is_active=True,
    )
    db_session.add(driver)
    db_session.commit()

    token = create_session_token(driver.id, "driver")

    response = asyncio.run(
        driver_location_update(
            latitude=41.311081,
            longitude=69.240562,
            accuracy=5,
            battery=80,
            token=token,
            db=db_session,
        )
    )

    assert response["success"] is True
    location = db_session.query(DriverLocation).one()
    assert location.driver_id == driver.id


def test_driver_location_rejects_agent_token(db_session):
    driver = Driver(code="DR001", full_name="Driver One", phone="+998901111111", is_active=True)
    db_session.add(driver)
    db_session.commit()

    token = create_session_token(driver.id, "agent")

    response = asyncio.run(
        driver_location_update(
            latitude=41.311081,
            longitude=69.240562,
            accuracy=5,
            battery=80,
            token=token,
            db=db_session,
        )
    )

    assert response == {"success": False, "error": "Invalid token"}
    assert db_session.query(DriverLocation).count() == 0
