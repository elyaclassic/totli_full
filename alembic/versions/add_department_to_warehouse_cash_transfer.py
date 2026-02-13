"""add department_id to warehouses and cash_registers, workflow to transfers

Revision ID: dept_warehouse_cash
Revises: add_prev_bal
Create Date: 2026-02-12

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


revision: str = 'dept_warehouse_cash'
down_revision: Union[str, Sequence[str], None] = 'add_prev_bal'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(conn, table: str, column: str) -> bool:
    """SQLite uchun ustun mavjudligini tekshirish"""
    if conn.dialect.name == "sqlite":
        r = conn.execute(text(f"PRAGMA table_info({table})"))
        return any(row[1] == column for row in r)
    return False


def upgrade() -> None:
    conn = op.get_bind()
    is_sqlite = conn.dialect.name == "sqlite"
    
    # 1. Warehouses jadvaliga department_id qo'shish
    if not _has_column(conn, "warehouses", "department_id"):
        op.add_column('warehouses', sa.Column('department_id', sa.Integer(), nullable=True))
        # SQLite da foreign key constraint'lar oddiy qo'shilmaydi, lekin SQLAlchemy modelda relationship bor
        if not is_sqlite:
            try:
                op.create_foreign_key('fk_warehouses_department', 'warehouses', 'departments', ['department_id'], ['id'])
            except Exception:
                pass  # Agar constraint mavjud bo'lsa, o'tkazib yuborish
    
    # 2. Cash_registers jadvaliga department_id qo'shish
    if not _has_column(conn, "cash_registers", "department_id"):
        op.add_column('cash_registers', sa.Column('department_id', sa.Integer(), nullable=True))
        if not is_sqlite:
            try:
                op.create_foreign_key('fk_cash_registers_department', 'cash_registers', 'departments', ['department_id'], ['id'])
            except Exception:
                pass
    
    # 3. Warehouse_transfers jadvaliga workflow maydonlarini qo'shish
    if not _has_column(conn, "warehouse_transfers", "approved_by_user_id"):
        op.add_column('warehouse_transfers', sa.Column('approved_by_user_id', sa.Integer(), nullable=True))
        if not is_sqlite:
            try:
                op.create_foreign_key('fk_transfers_approved_by', 'warehouse_transfers', 'users', ['approved_by_user_id'], ['id'])
            except Exception:
                pass
    
    if not _has_column(conn, "warehouse_transfers", "approved_at"):
        op.add_column('warehouse_transfers', sa.Column('approved_at', sa.DateTime(), nullable=True))
    
    # Status default qiymatini yangilash (pending_approval qo'shilishi mumkin)
    # SQLite da ALTER COLUMN qo'llab-quvvatlanmaydi, shuning uchun bu qo'shimcha kod kerak emas


def downgrade() -> None:
    # Teskari o'zgarishlar
    op.drop_constraint('fk_transfers_approved_by', 'warehouse_transfers', type_='foreignkey')
    op.drop_column('warehouse_transfers', 'approved_at')
    op.drop_column('warehouse_transfers', 'approved_by_user_id')
    
    op.drop_constraint('fk_cash_registers_department', 'cash_registers', type_='foreignkey')
    op.drop_column('cash_registers', 'department_id')
    
    op.drop_constraint('fk_warehouses_department', 'warehouses', type_='foreignkey')
    op.drop_column('warehouses', 'department_id')
