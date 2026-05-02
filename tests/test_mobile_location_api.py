import asyncio


class _FakeQuery:
    def __init__(self, result):
        self._result = result

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self._result


class _FakeDb:
    def __init__(self, query_result=None):
        self.query_result = query_result
        self.added = []
        self.committed = False
        self.rolled_back = False

    def query(self, model):
        return _FakeQuery(self.query_result)

    def add(self, obj):
        self.added.append(obj)
        obj.id = 123

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


def test_agent_location_requires_agent_token(monkeypatch):
    import main

    monkeypatch.setattr(main, "get_user_from_token", lambda token: None)
    db = _FakeDb()

    result = asyncio.run(
        main.agent_location_update(
            latitude=41.0,
            longitude=69.0,
            accuracy=5.0,
            battery=90,
            token="bad-token",
            db=db,
        )
    )

    assert result == {"success": False, "error": "Invalid token"}
    assert db.added == []
    assert not db.committed


def test_agent_location_uses_token_agent_id(monkeypatch):
    import main

    monkeypatch.setattr(
        main,
        "get_user_from_token",
        lambda token: {"user_id": 42, "user_type": "agent"},
    )
    db = _FakeDb(query_result=object())

    result = asyncio.run(
        main.agent_location_update(
            latitude=41.0,
            longitude=69.0,
            accuracy=5.0,
            battery=90,
            token="agent-token",
            db=db,
        )
    )

    assert result == {"success": True, "location_id": 123}
    assert db.added[0].agent_id == 42
    assert db.committed


def test_driver_location_uses_driver_token_type(monkeypatch):
    import main

    monkeypatch.setattr(
        main,
        "get_user_from_token",
        lambda token: {"user_id": 7, "user_type": "driver"},
    )
    db = _FakeDb(query_result=object())

    result = asyncio.run(
        main.driver_location_update(
            latitude=41.0,
            longitude=69.0,
            accuracy=5.0,
            battery=80,
            token="driver-token",
            db=db,
        )
    )

    assert result == {"success": True, "location_id": 123}
    assert db.added[0].driver_id == 7
    assert db.committed


def test_driver_location_route_is_not_shadowed():
    import main

    matching_routes = [
        route
        for route in main.app.routes
        if getattr(route, "path", None) == "/api/driver/location"
        and "POST" in getattr(route, "methods", set())
    ]

    assert len(matching_routes) == 1
    assert matching_routes[0].endpoint is main.driver_location_update
