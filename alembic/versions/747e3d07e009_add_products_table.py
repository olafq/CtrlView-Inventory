"""add products table

Revision ID: 747e3d07e009
Revises: 23b763ad1409
Create Date: 2026-02-03 20:23:24.872659

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '747e3d07e009'
down_revision: Union[str, Sequence[str], None] = '23b763ad1409'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade():
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sku", sa.String(), nullable=False, unique=True, index=True),
        sa.Column("name", sa.String()),
        sa.Column("description", sa.Text()),
        sa.Column("cost", sa.Numeric()),
        sa.Column("stock_total", sa.Integer(), default=0),
        sa.Column("stock_reserved", sa.Integer(), default=0),
        sa.Column("stock_available", sa.Integer(), default=0),
        sa.Column("low_stock_threshold", sa.Integer(), default=0),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
    )


def downgrade():
    op.drop_table("products")