"""Document numbers must stay unique after a same-day delete."""
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.models.database import Base, Purchase, Production
from app.utils import doc_numbers
from app.utils.doc_numbers import next_doc_number, set_unique_doc_number


def _session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False)()


def _day(when):
    return when.strftime("%Y%m%d")


def test_count_based_number_collides_after_deleting_earlier_doc():
    """The old count+1 formula reuses a number that is still stored."""
    db = _session()
    today = datetime(2026, 9, 27, 11, 0, 0)
    day = _day(today)
    db.add(Purchase(number=f"P-{day}-0001", date=today, total=1, status="draft"))
    db.add(Purchase(number=f"P-{day}-0002", date=today, total=10, status="draft"))
    db.commit()
    first = db.query(Purchase).filter(Purchase.number == f"P-{day}-0001").one()
    db.delete(first)
    db.commit()

    count = db.query(Purchase).filter(
        Purchase.date >= today.replace(hour=0, minute=0, second=0)
    ).count()
    reused = f"P-{day}-{str(count + 1).zfill(4)}"
    assert reused == f"P-{day}-0002"
    db.add(Purchase(number=reused, date=today, total=3, status="draft"))
    try:
        db.commit()
        raised = False
    except IntegrityError:
        db.rollback()
        raised = True
    assert raised

    created = Purchase(number="", date=today, total=3, status="draft")
    db.add(created)
    number = set_unique_doc_number(db, created, Purchase, "P", when=today)
    db.commit()
    assert number == f"P-{day}-0003"
    assert created.total == 3
    assert db.query(Purchase).filter(Purchase.number == number).count() == 1


def test_production_number_width_and_prefix_do_not_clash():
    db = _session()
    today = datetime(2026, 9, 27, 15, 30, 0)
    day = _day(today)
    db.add(Production(number=f"PR-{day}-001", date=today, quantity=1, status="draft"))
    db.add(Production(number=f"PR-{day}-002", date=today, quantity=1, status="draft"))
    db.commit()
    db.delete(db.query(Production).filter(Production.number == f"PR-{day}-001").one())
    db.commit()

    created = Production(number="", date=today, quantity=2, status="draft")
    db.add(created)
    number = set_unique_doc_number(db, created, Production, "PR", width=3, when=today)
    db.commit()
    assert number == f"PR-{day}-003"

    purchase = Purchase(number="", date=today, total=1, status="draft")
    db.add(purchase)
    assert set_unique_doc_number(db, purchase, Purchase, "P", when=today) == f"P-{day}-0001"


def test_next_number_follows_highest_suffix_not_row_count():
    db = _session()
    today = datetime(2026, 9, 27, 12, 0, 0)
    day = _day(today)
    db.add(Purchase(number=f"P-{day}-0002", date=today, total=1, status="draft"))
    db.commit()
    assert next_doc_number(db, Purchase, "P", when=today) == f"P-{day}-0003"
    assert doc_numbers.next_doc_number(db, Purchase, "P", width=3, when=today) == f"P-{day}-003"
