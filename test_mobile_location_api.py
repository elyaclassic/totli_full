import asyncio

import httpx

from app.models.database import (
    Agent,
    AgentLocation,
    Base,
    Driver,
    DriverLocation,
    SessionLocal,
    engine,
)
from main import app


def _post(path, data):
    async def _send():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.post(path, data=data)

    return asyncio.run(_send())


def setup_module():
    Base.metadata.create_all(bind=engine)


def _clear_mobile_test_data():
    db = SessionLocal()
    try:
        db.query(AgentLocation).filter(AgentLocation.agent_id.in_([9101, 9102])).delete(synchronize_session=False)
        db.query(DriverLocation).filter(DriverLocation.driver_id == 9201).delete(synchronize_session=False)
        db.query(Agent).filter(Agent.id.in_([9101, 9102])).delete(synchronize_session=False)
        db.query(Driver).filter(Driver.id == 9201).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()


def setup_function():
    _clear_mobile_test_data()


def teardown_function():
    _clear_mobile_test_data()


def test_agent_location_requires_valid_agent_token_and_uses_token_identity():
    db = SessionLocal()
    try:
        db.add_all(
            [
                Agent(id=9101, code="MOB-A1", full_name="Mobile Agent 1", phone="+998901001001", is_active=True),
                Agent(id=9102, code="MOB-A2", full_name="Mobile Agent 2", phone="+998901001002", is_active=True),
            ]
        )
        db.commit()
    finally:
        db.close()

    login_response = _post(
        "/api/agent/login",
        data={"username": "+998901001002", "password": "+998901001002"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["token"]

    response = _post(
        "/api/agent/location",
        data={"latitude": 41.31, "longitude": 69.24, "accuracy": 5, "battery": 88, "token": token},
    )
    assert response.status_code == 200
    assert response.json()["success"] is True

    db = SessionLocal()
    try:
        assert db.query(AgentLocation).filter(AgentLocation.agent_id == 9101).count() == 0
        saved = db.query(AgentLocation).filter(AgentLocation.agent_id == 9102).one()
        assert saved.latitude == 41.31
        assert saved.longitude == 69.24
    finally:
        db.close()


def test_driver_location_rejects_legacy_driver_code_without_token():
    db = SessionLocal()
    try:
        db.add(Driver(id=9201, code="DRV-9201", full_name="Mobile Driver", phone="+998902002001", is_active=True))
        db.commit()
    finally:
        db.close()

    response = _post(
        "/api/driver/location",
        data={"driver_code": "DRV-9201", "latitude": 41.31, "longitude": 69.24, "speed": 20},
    )
    assert response.status_code == 422

    db = SessionLocal()
    try:
        assert db.query(DriverLocation).filter(DriverLocation.driver_id == 9201).count() == 0
    finally:
        db.close()
