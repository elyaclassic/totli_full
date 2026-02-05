"""add products.image

Revision ID: add_products_image
Revises: add_price_type_orders
Create Date: 2026-02-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision: str = "add_products_image"
down_revision: Union[str, Sequence[str], None] = "add_price_type_orders"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(conn, table: str, column: str) -> bool:
    if conn.dialect.name == "sqlite":
        r = conn.execute(text(f"PRAGMA table_info({table})"))
        return any(row[1] == column for row in r)
    return False


def upgrade() -> None:
    conn = op.get_bind()
    if _column_exists(conn, "products", "image"):
        return
    op.add_column("products", sa.Column("image", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("products", "image")
