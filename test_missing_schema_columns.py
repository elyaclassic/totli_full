"""Production create must succeed on a database migrated only by older Alembic revisions."""
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from app.models.database import Production, ensure_runtime_columns


def _old_engine(tmp_path):
    db_path = tmp_path / "old.db"
    engine = create_engine(f"sqlite:///{db_path}")
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE productions (
                    id INTEGER PRIMARY KEY,
                    number VARCHAR(50),
                    date DATETIME,
                    recipe_id INTEGER,
                    warehouse_id INTEGER,
                    output_warehouse_id INTEGER,
                    quantity FLOAT,
                    status VARCHAR(20),
                    current_stage INTEGER,
                    max_stage INTEGER,
                    user_id INTEGER,
                    note TEXT,
                    created_at DATETIME
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE employees (
                    id INTEGER PRIMARY KEY,
                    code VARCHAR(50),
                    full_name VARCHAR(200),
                    is_active BOOLEAN
                )
                """
            )
        )
        conn.execute(
            text(
                "INSERT INTO productions (number, recipe_id, warehouse_id, quantity, status) "
                "VALUES ('PR-KEEP', 1, 1, 3, 'draft')"
            )
        )
        conn.execute(
            text("INSERT INTO employees (code, full_name, is_active) VALUES ('E1', 'Ali', 1)")
        )
    return engine


def _insert_production(engine):
    db = sessionmaker(bind=engine, autoflush=False)()
    try:
        db.add(
            Production(
                number="PR-NEW",
                recipe_id=1,
                warehouse_id=1,
                output_warehouse_id=1,
                quantity=10,
                status="draft",
                current_stage=1,
                max_stage=2,
                machine_id=None,
                operator_id=None,
                note="",
            )
        )
        db.commit()
    finally:
        db.close()


def test_production_insert_fails_until_columns_are_added(tmp_path):
    engine = _old_engine(tmp_path)
    try:
        _insert_production(engine)
        raised = False
    except OperationalError as exc:
        raised = True
        assert "machine_id" in str(exc)
    assert raised

    ensure_runtime_columns(engine)
    _insert_production(engine)

    db = sessionmaker(bind=engine, autoflush=False)()
    try:
        kept = db.query(Production).filter(Production.number == "PR-KEEP").one()
        created = db.query(Production).filter(Production.number == "PR-NEW").one()
        assert kept.quantity == 3
        assert created.quantity == 10
        assert created.machine_id is None
        assert created.operator_id is None
        birth = db.execute(text("SELECT birth_date FROM employees WHERE code = 'E1'")).fetchone()
        assert birth[0] is None
    finally:
        db.close()

    # Second startup must not try to add the columns again.
    ensure_runtime_columns(engine)
    with engine.connect() as conn:
        cols = {row[1] for row in conn.execute(text("PRAGMA table_info(productions)"))}
    assert "machine_id" in cols
    assert "operator_id" in cols


def test_ensure_skips_when_tables_are_absent(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'empty.db'}")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE unrelated (id INTEGER PRIMARY KEY)"))
    ensure_runtime_columns(engine)
    with engine.connect() as conn:
        tables = {row[0] for row in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))}
    assert tables == {"unrelated"}
