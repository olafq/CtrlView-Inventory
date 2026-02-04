"""sync external_items schema v2

Revision ID: 6c630169b7e8
Revises: 6fca767aedff
Create Date: 2026-02-03 21:15:12.952922

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6c630169b7e8'
down_revision: Union[str, Sequence[str], None] = '6fca767aedff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
