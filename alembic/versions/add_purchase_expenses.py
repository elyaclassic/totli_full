"""add purchase_expenses and total_expenses

Revision ID: add_purchase_exp
Revises: 7ae4744e1aaf
Create Date: 2026-02-06

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = 'add_purchase_exp'
down_revision = 'add_prod_output_wh'
branch_labels = None
depends_on = None


def _has_column(conn, table: str, column: str) -> bool:
    if conn.dialect.name == "sqlite":
        r = conn.execute(text(f"PRAGMA table_info({table})"))
        return any(row[1] == column for row in r)
    return False


def _table_exists(conn, table: str) -> bool:
    if conn.dialect.name == "sqlite":
        r = conn.execute(text(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'"))
        return r.fetchone() is not None
    return False


def upgrade() -> None:
    conn = op.get_bind()
    if not _has_column(conn, "purchases", "total_expenses"):
        op.add_column("purchases", sa.Column("total_expenses", sa.Float(), nullable=True))
        op.execute(text("UPDATE purchases SET total_expenses = 0 WHERE total_expenses IS NULL"))
    if not _table_exists(conn, "purchase_expenses"):
        op.create_table(
            "purchase_expenses",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("purchase_id", sa.Integer(), nullable=True),
            sa.Column("name", sa.String(200), nullable=True),
            sa.Column("amount", sa.Float(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["purchase_id"], ["purchases.id"]),
        )


def downgrade() -> None:
    op.drop_table("purchase_expenses")
    op.drop_column("purchases", "total_expenses")
