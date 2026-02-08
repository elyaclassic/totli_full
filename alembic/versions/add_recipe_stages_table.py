"""add recipe_stages table

Revision ID: add_recipe_stages
Revises: add_purchase_exp
Create Date: 2026-02-05

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


revision: str = "add_recipe_stages"
down_revision: Union[str, Sequence[str], None] = "add_prev_bal"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(conn, table: str) -> bool:
    if conn.dialect.name == "sqlite":
        r = conn.execute(text(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'"))
        return r.fetchone() is not None
    return False


def upgrade() -> None:
    conn = op.get_bind()
    if _table_exists(conn, "recipe_stages"):
        return
    op.create_table(
        "recipe_stages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("recipe_id", sa.Integer(), nullable=False),
        sa.Column("stage_number", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.ForeignKeyConstraint(["recipe_id"], ["recipes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("recipe_id", "stage_number", name="uq_recipe_stage_number"),
    )
    op.create_index(op.f("ix_recipe_stages_id"), "recipe_stages", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_recipe_stages_id"), table_name="recipe_stages")
    op.drop_table("recipe_stages")
