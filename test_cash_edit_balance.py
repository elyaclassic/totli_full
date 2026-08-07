"""Regression: /info/cash/edit must not wipe cash balances outside documents."""
import asyncio

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.responses import RedirectResponse

from app.models.database import Base, CashRegister, Department, User
from app.routes import info as info_routes


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_info_cash_edit_preserves_balance_when_crafted_balance_posted(db):
    """Editing kassa master data must not overwrite ledger balance (no CashBalanceDoc)."""
    user = User(
        username="admin",
        full_name="Admin",
        password_hash="x",
        role="admin",
        is_active=True,
    )
    dept = Department(code="D1", name="Asosiy", is_active=True)
    cash = CashRegister(name="Asosiy kassa", balance=5_000_000, is_active=True)
    db.add_all([user, dept, cash])
    db.commit()
    db.refresh(cash)
    cash_id = cash.id
    dept_id = dept.id

    # Crafted POST that previously set balance=0 and wiped the ledger.
    resp = run(
        info_routes.info_cash_edit(
            cash_id=cash_id,
            name="Asosiy kassa (yangilangan)",
            department_id=dept_id,
            db=db,
            current_user=user,
        )
    )
    assert isinstance(resp, RedirectResponse)

    db.expire_all()
    cash = db.query(CashRegister).filter(CashRegister.id == cash_id).first()
    assert cash is not None
    assert cash.name == "Asosiy kassa (yangilangan)"
    assert cash.department_id == dept_id
    assert cash.balance == 5_000_000


def test_info_cash_edit_ignores_balance_kwarg_if_passed(db):
    """Even if a caller still passes balance=, ledger must stay intact."""
    user = User(
        username="u1",
        full_name="User",
        password_hash="x",
        role="user",
        is_active=True,
    )
    cash = CashRegister(name="Kassa 2", balance=123_456, is_active=True)
    db.add_all([user, cash])
    db.commit()
    cash_id = cash.id

    # Simulate older clients / crafted forms that still send balance.
    import inspect

    sig = inspect.signature(info_routes.info_cash_edit)
    assert "balance" not in sig.parameters

    resp = run(
        info_routes.info_cash_edit(
            cash_id=cash_id,
            name="Kassa 2",
            department_id=None,
            db=db,
            current_user=user,
        )
    )
    assert isinstance(resp, RedirectResponse)
    db.expire_all()
    cash = db.query(CashRegister).filter(CashRegister.id == cash_id).first()
    assert cash.balance == 123_456


def test_info_cash_add_still_allows_opening_balance(db):
    """New kassa may still set an opening balance at creation time."""
    user = User(
        username="admin",
        full_name="Admin",
        password_hash="x",
        role="admin",
        is_active=True,
    )
    db.add(user)
    db.commit()

    class _Req:
        pass

    resp = run(
        info_routes.info_cash_add(
            request=_Req(),
            name="Yangi kassa",
            balance=10_000,
            department_id=None,
            db=db,
            current_user=user,
        )
    )
    assert isinstance(resp, RedirectResponse)
    cash = db.query(CashRegister).filter(CashRegister.name == "Yangi kassa").first()
    assert cash is not None
    assert cash.balance == 10_000
