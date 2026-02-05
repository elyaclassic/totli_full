"""add production_stages and productions.current_stage

Revision ID: add_production_stages
Revises: add_products_image
Create Date: 2026-02-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision: str = "add_production_stages"
down_revision: Union[str, Sequence[str], None] = "add_products_image"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(conn, table: str, column: str) -> bool:
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
    if not _column_exists(conn, "productions", "current_stage"):
        op.add_column("productions", sa.Column("current_stage", sa.Integer(), nullable=True))
    if not _table_exists(conn, "production_stages"):
        op.create_table(
            "production_stages",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("production_id", sa.Integer(), nullable=False),
            sa.Column("stage_number", sa.Integer(), nullable=False),
            sa.Column("machine_id", sa.Integer(), nullable=True),
            sa.Column("operator_id", sa.Integer(), nullable=True),
            sa.Column("started_at", sa.DateTime(), nullable=True),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("quantity_in", sa.Float(), nullable=True),
            sa.Column("quantity_out", sa.Float(), nullable=True),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["production_id"], ["productions.id"]),
            sa.ForeignKeyConstraint(["machine_id"], ["machines.id"]),
            sa.ForeignKeyConstraint(["operator_id"], ["employees.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_production_stages_id"), "production_stages", ["id"], unique=False)
        op.create_index(op.f("ix_production_stages_production_id"), "production_stages", ["production_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_production_stages_production_id"), table_name="production_stages")
    op.drop_index(op.f("ix_production_stages_id"), table_name="production_stages")
    op.drop_table("production_stages")
    op.drop_column("productions", "current_stage")
