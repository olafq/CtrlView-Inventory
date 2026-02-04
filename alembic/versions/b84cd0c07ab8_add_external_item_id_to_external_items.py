"""add external_item_id to external_items

Revision ID: b84cd0c07ab8
Revises: 6c630169b7e8
Create Date: 2026-02-03 21:40:50.077656

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b84cd0c07ab8'
down_revision: Union[str, Sequence[str], None] = '6c630169b7e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
