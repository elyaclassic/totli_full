"""add previous_balance for balance doc items (revert support)

Revision ID: add_prev_bal
Revises: 7ae4744e1aaf
Create Date: 2026-02-05

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


revision: str = 'add_prev_bal'
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
    if not _has_column(conn, "cash_balance_doc_items", "previous_balance"):
        op.add_column('cash_balance_doc_items', sa.Column('previous_balance', sa.Float(), nullable=True))
    if not _has_column(conn, "partner_balance_doc_items", "previous_balance"):
        op.add_column('partner_balance_doc_items', sa.Column('previous_balance', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('partner_balance_doc_items', 'previous_balance')
    op.drop_column('cash_balance_doc_items', 'previous_balance')
