import asyncio

from main import agent_location_update, driver_location_update
from app.models.database import Agent, AgentLocation, Driver, DriverLocation
from app.utils.auth import create_session_token


class DummyQuery:
    def __init__(self, rows):
        self.rows = rows

    def filter(self, *args):
        return self

    def first(self):
        return self.rows[0] if self.rows else None


class DummyDb:
    def __init__(self, rows):
        self.rows = rows
        self.added = []
        self.committed = False
        self.rolled_back = False

    def query(self, model):
        return DummyQuery(self.rows.get(model, []))

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.committed = True
        for idx, obj in enumerate(self.added, start=1):
            obj.id = idx

    def rollback(self):
        self.rolled_back = True


def run(awaitable):
    return asyncio.run(awaitable)


def test_agent_location_uses_authenticated_agent_id():
    token = create_session_token(7, "agent")
    db = DummyDb({Agent: [Agent(id=7, is_active=True)]})

    result = run(agent_location_update(41.3, 69.2, 5, 80, token, db))

    assert result["success"] is True
    assert db.committed is True
    assert len(db.added) == 1
    assert isinstance(db.added[0], AgentLocation)
    assert db.added[0].agent_id == 7


def test_agent_location_rejects_invalid_token_without_writing():
    db = DummyDb({Agent: [Agent(id=7, is_active=True)]})

    result = run(agent_location_update(41.3, 69.2, 5, 80, "invalid", db))

    assert result == {"success": False, "error": "Invalid token"}
    assert db.added == []
    assert db.committed is False


def test_driver_location_accepts_driver_login_token():
    token = create_session_token(11, "driver")
    db = DummyDb({Driver: [Driver(id=11, is_active=True)]})

    result = run(driver_location_update(41.4, 69.3, 4, 70, token, db))

    assert result["success"] is True
    assert db.committed is True
    assert len(db.added) == 1
    assert isinstance(db.added[0], DriverLocation)
    assert db.added[0].driver_id == 11


def test_driver_location_rejects_agent_token_without_writing():
    token = create_session_token(7, "agent")
    db = DummyDb({Driver: [Driver(id=7, is_active=True)]})

    result = run(driver_location_update(41.4, 69.3, 4, 70, token, db))

    assert result == {"success": False, "error": "Invalid token"}
    assert db.added == []
    assert db.committed is False
