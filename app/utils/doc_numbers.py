"""Unique daily document numbers.

Counting rows and adding one reuses a number after an earlier same-day
document is deleted while a later one is still stored. The number column is
unique, so the next create raises IntegrityError. HTML errors then drop the
session. Allocate from the highest existing suffix instead.
"""
from datetime import datetime


def next_doc_number(db, model, prefix: str, width: int = 4, when: datetime = None) -> str:
    """Return prefix-YYYYMMDD-N, where N is one past the highest suffix stored for that day."""
    when = when or datetime.now()
    stem = f"{prefix}-{when.strftime('%Y%m%d')}-"
    rows = db.query(model.number).filter(model.number.like(stem + "%")).all()
    max_n = 0
    for (num,) in rows:
        suffix = (num or "")[len(stem):]
        if suffix.isdigit():
            max_n = max(max_n, int(suffix))
    return f"{stem}{str(max_n + 1).zfill(width)}"


def set_unique_doc_number(db, obj, model, prefix: str, width: int = 4, when: datetime = None) -> str:
    """Assign obj.number from the current max suffix and flush it.

    The object must already be pending in the session. A concurrent insert can
    still collide; that raises IntegrityError instead of reusing a stored number.
    """
    obj.number = next_doc_number(db, model, prefix, width=width, when=when)
    db.flush()
    return obj.number
