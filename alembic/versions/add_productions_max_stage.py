"""add productions.max_stage

Revision ID: add_prod_max_stage
Revises: add_recipe_stages
Create Date: 2026-02-08

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


revision: str = "add_prod_max_stage"
down_revision: Union[str, Sequence[str], None] = "add_purchase_exp"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(conn, table: str, column: str) -> bool:
    if conn.dialect.name == "sqlite":
        r = conn.execute(text(f"PRAGMA table_info({table})"))
        return any(row[1] == column for row in r)
    return False


def upgrade() -> None:
    conn = op.get_bind()
    if _has_column(conn, "productions", "max_stage"):
        return
    op.add_column("productions", sa.Column("max_stage", sa.Integer(), nullable=True))
    conn.execute(text("UPDATE productions SET max_stage = 4 WHERE max_stage IS NULL"))


def downgrade() -> None:
    op.drop_column("productions", "max_stage")
