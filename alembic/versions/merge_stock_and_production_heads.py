"""merge stock movement and production migration heads

Revision ID: merge_stock_prod_heads
Revises: stock_movement_track, merge_heads_01
Create Date: 2026-07-17

"""
from typing import Sequence, Union


revision: str = "merge_stock_prod_heads"
down_revision: Union[str, Sequence[str], None] = (
    "stock_movement_track",
    "merge_heads_01",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
