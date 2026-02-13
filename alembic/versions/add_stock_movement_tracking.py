"""add stock_movements table for tracking each operation with document

Revision ID: stock_movement_track
Revises: dept_warehouse_cash
Create Date: 2026-02-12

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


revision: str = 'stock_movement_track'
down_revision: Union[str, Sequence[str], None] = 'dept_warehouse_cash'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(conn, table: str) -> bool:
    """SQLite uchun jadval mavjudligini tekshirish"""
    if conn.dialect.name == "sqlite":
        r = conn.execute(text(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'"))
        return r.fetchone() is not None
    return False


def upgrade() -> None:
    conn = op.get_bind()
    
    if not _has_table(conn, "stock_movements"):
        op.create_table(
            "stock_movements",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("stock_id", sa.Integer(), nullable=True),
            sa.Column("warehouse_id", sa.Integer(), nullable=False),
            sa.Column("product_id", sa.Integer(), nullable=False),
            sa.Column("operation_type", sa.String(50), nullable=False),
            sa.Column("document_type", sa.String(50), nullable=False),
            sa.Column("document_id", sa.Integer(), nullable=False),
            sa.Column("document_number", sa.String(100), nullable=True),
            sa.Column("quantity_change", sa.Float(), nullable=False),
            sa.Column("quantity_after", sa.Float(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["stock_id"], ["stocks.id"]),
            sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"]),
            sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_stock_movements_id"), "stock_movements", ["id"], unique=False)
        op.create_index(op.f("ix_stock_movements_warehouse_id"), "stock_movements", ["warehouse_id"], unique=False)
        op.create_index(op.f("ix_stock_movements_product_id"), "stock_movements", ["product_id"], unique=False)
        op.create_index(op.f("ix_stock_movements_document_type"), "stock_movements", ["document_type"], unique=False)
        op.create_index(op.f("ix_stock_movements_document_id"), "stock_movements", ["document_id"], unique=False)
        op.create_index(op.f("ix_stock_movements_created_at"), "stock_movements", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_stock_movements_created_at"), table_name="stock_movements")
    op.drop_index(op.f("ix_stock_movements_document_id"), table_name="stock_movements")
    op.drop_index(op.f("ix_stock_movements_document_type"), table_name="stock_movements")
    op.drop_index(op.f("ix_stock_movements_product_id"), table_name="stock_movements")
    op.drop_index(op.f("ix_stock_movements_warehouse_id"), table_name="stock_movements")
    op.drop_index(op.f("ix_stock_movements_id"), table_name="stock_movements")
    op.drop_table("stock_movements")
