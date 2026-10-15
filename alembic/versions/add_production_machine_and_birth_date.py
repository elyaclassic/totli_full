"""add productions.machine_id, productions.operator_id, employees.birth_date

These columns are on the models and are written by production create and the
home page, but they were only applied by one-off scripts. Alembic upgrade
left production create failing with "no such column: productions.machine_id".

Revision ID: add_machine_birth
Revises: merge_heads_01, stock_movement_track
Create Date: 2026-10-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


revision: str = "add_machine_birth"
down_revision: Union[str, Sequence[str], None] = ("merge_heads_01", "stock_movement_track")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(conn, table: str, column: str) -> bool:
    if conn.dialect.name == "sqlite":
        rows = conn.execute(text(f"PRAGMA table_info({table})"))
        return any(row[1] == column for row in rows)
    rows = conn.execute(
        text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :table AND column_name = :column"
        ),
        {"table": table, "column": column},
    )
    return rows.fetchone() is not None


def _table_exists(conn, table: str) -> bool:
    if conn.dialect.name == "sqlite":
        row = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name=:name"),
            {"name": table},
        ).fetchone()
        return row is not None
    row = conn.execute(
        text("SELECT 1 FROM information_schema.tables WHERE table_name = :name"),
        {"name": table},
    ).fetchone()
    return row is not None


def upgrade() -> None:
    conn = op.get_bind()
    if _table_exists(conn, "productions"):
        if not _column_exists(conn, "productions", "machine_id"):
            op.add_column("productions", sa.Column("machine_id", sa.Integer(), nullable=True))
        if not _column_exists(conn, "productions", "operator_id"):
            op.add_column("productions", sa.Column("operator_id", sa.Integer(), nullable=True))
    if _table_exists(conn, "employees") and not _column_exists(conn, "employees", "birth_date"):
        op.add_column("employees", sa.Column("birth_date", sa.Date(), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    if _table_exists(conn, "employees") and _column_exists(conn, "employees", "birth_date"):
        op.drop_column("employees", "birth_date")
    if _table_exists(conn, "productions"):
        if _column_exists(conn, "productions", "operator_id"):
            op.drop_column("productions", "operator_id")
        if _column_exists(conn, "productions", "machine_id"):
            op.drop_column("productions", "machine_id")
