import asyncio

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.database import Agent, AgentLocation, Base
from app.utils.auth import create_session_token
from main import agent_location_update


def _session_with_temp_db(tmp_path):
    db_path = tmp_path / "pwa_auth.db"
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return TestingSessionLocal


def test_agent_location_rejects_invalid_token_without_writing(tmp_path):
    SessionLocal = _session_with_temp_db(tmp_path)
    with SessionLocal() as db:
        db.add(Agent(id=1, code="A001", full_name="Agent One", phone="100", is_active=True))
        db.commit()

        response = asyncio.run(
            agent_location_update(
                latitude=41.3111,
                longitude=69.2797,
                token="not-a-valid-token",
                db=db,
            )
        )

        assert response["success"] is False
        assert db.query(AgentLocation).count() == 0


def test_agent_location_uses_authenticated_agent_id(tmp_path):
    SessionLocal = _session_with_temp_db(tmp_path)
    with SessionLocal() as db:
        db.add_all(
            [
                Agent(id=1, code="A001", full_name="Agent One", phone="100", is_active=True),
                Agent(id=2, code="A002", full_name="Agent Two", phone="200", is_active=True),
            ]
        )
        db.commit()

        response = asyncio.run(
            agent_location_update(
                latitude=41.3111,
                longitude=69.2797,
                token=create_session_token(2, "agent"),
                db=db,
            )
        )

        assert response["success"] is True
        location = db.query(AgentLocation).one()
        assert location.agent_id == 2
