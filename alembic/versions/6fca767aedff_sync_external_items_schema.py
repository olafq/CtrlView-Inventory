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
    op.add_column(
        "external_items",
        sa.Column("external_item_id", sa.String(), nullable=False),
    )
    op.create_index(
        "ix_external_items_external_item_id",
        "external_items",
        ["external_item_id"],
    )


def downgrade():
    op.drop_index("ix_external_items_external_item_id", table_name="external_items")
    op.drop_column("external_items", "external_item_id")