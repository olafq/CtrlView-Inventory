"""sync external_items schema

Revision ID: 6fca767aedff
Revises: 37237cca810c
Create Date: 2026-02-03 21:14:29.133985

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6fca767aedff'
down_revision: Union[str, Sequence[str], None] = '37237cca810c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # agregar columnas que faltan
    op.add_column(
        "external_items",
        sa.Column("external_item_id", sa.String(), nullable=False),
    )

    op.add_column(
        "external_items",
        sa.Column("external_sku", sa.String(), nullable=True),
    )

    op.add_column(
        "external_items",
        sa.Column("product_id", sa.Integer(), nullable=False),
    )

    # foreign key a products
    op.create_foreign_key(
        "fk_external_items_product",
        "external_items",
        "products",
        ["product_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # unique constraint canal + item
    op.create_unique_constraint(
        "uq_external_item_channel",
        "external_items",
        ["channel_id", "external_item_id"],
    )
