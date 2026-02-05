"""add orders.price_type_id

Revision ID: add_price_type_orders
Revises: 7ae4744e1aaf
Create Date: 2026-02-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


revision: str = 'add_price_type_orders'
down_revision: Union[str, Sequence[str], None] = '7ae4744e1aaf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(conn, table: str, column: str) -> bool:
    if conn.dialect.name == "sqlite":
        r = conn.execute(text(f"PRAGMA table_info({table})"))
        return any(row[1] == column for row in r)
    return False


def upgrade() -> None:
    conn = op.get_bind()
    if not _has_column(conn, "orders", "price_type_id"):
        op.add_column('orders', sa.Column('price_type_id', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('orders', 'price_type_id')
