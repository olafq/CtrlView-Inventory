"""make tenant_id not null in sales

Revision ID: 290d9327e565
Revises: 1e51b307cc05
Create Date: 2026-02-25 23:38:58.169749

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '290d9327e565'
down_revision: Union[str, Sequence[str], None] = '1e51b307cc05'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.alter_column(
        "sales",
        "tenant_id",
        existing_type=sa.Integer(),
        nullable=False
    )

def downgrade():
    op.alter_column(
        "sales",
        "tenant_id",
        existing_type=sa.Integer(),
        nullable=True
    )