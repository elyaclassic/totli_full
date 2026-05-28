"""add previous quantity to stock adjustment items

Revision ID: stock_adj_prev_qty
Revises: stock_movement_track
Create Date: 2026-05-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


revision: str = "stock_adj_prev_qty"
down_revision: Union[str, Sequence[str], None] = "stock_movement_track"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(conn, table: str, column: str) -> bool:
    if conn.dialect.name == "sqlite":
        r = conn.execute(text(f"PRAGMA table_info({table})"))
        return any(row[1] == column for row in r)
    return False


def upgrade() -> None:
    conn = op.get_bind()
    if not _has_column(conn, "stock_adjustment_doc_items", "previous_quantity"):
        op.add_column(
            "stock_adjustment_doc_items",
            sa.Column("previous_quantity", sa.Float(), nullable=True),
        )


def downgrade() -> None:
    conn = op.get_bind()
    if _has_column(conn, "stock_adjustment_doc_items", "previous_quantity"):
        op.drop_column("stock_adjustment_doc_items", "previous_quantity")
