"""add productions.output_warehouse_id (eski bazalar uchun)

Revision ID: add_prod_output_wh
Revises: add_production_stages
Create Date: 2026-02-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision: str = "add_prod_output_wh"
down_revision: Union[str, Sequence[str], None] = "add_production_stages"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(conn, table: str, column: str) -> bool:
    if conn.dialect.name == "sqlite":
        r = conn.execute(text(f"PRAGMA table_info({table})"))
        return any(row[1] == column for row in r)
    return False


def upgrade() -> None:
    conn = op.get_bind()
    if not _column_exists(conn, "productions", "output_warehouse_id"):
        op.add_column(
            "productions",
            sa.Column("output_warehouse_id", sa.Integer(), nullable=True),
        )


def downgrade() -> None:
    op.drop_column("productions", "output_warehouse_id")
