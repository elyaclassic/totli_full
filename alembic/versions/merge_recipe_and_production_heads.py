"""merge add_recipe_stages and add_prod_max_stage heads

Revision ID: merge_heads_01
Revises: add_recipe_stages, add_prod_max_stage
Create Date: 2026-02-08

"""
from typing import Sequence, Union
from alembic import op

revision: str = "merge_heads_01"
down_revision: Union[str, Sequence[str], None] = ("add_recipe_stages", "add_prod_max_stage")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
