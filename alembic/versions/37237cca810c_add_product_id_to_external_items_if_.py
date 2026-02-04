"""add product_id to external_items if missing

Revision ID: 37237cca810c
Revises: 77b490205e53
Create Date: 2026-02-03 21:00:10.947882

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = '37237cca810c'
down_revision: Union[str, Sequence[str], None] = '77b490205e53'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    columns = [col["name"] for col in inspector.get_columns("external_items")]

    if "product_id" not in columns:
        op.add_column(
            "external_items",
            sa.Column(
                "product_id",
                sa.Integer(),
                sa.ForeignKey("products.id"),
                nullable=True,
            ),
        )


def downgrade():
    pass