"""merge heads

Revision ID: ca73f4c45ab5
Revises: b84cd0c07ab8, force_external_item_id
Create Date: 2026-02-03 21:55:48.829194

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ca73f4c45ab5'
down_revision: Union[str, Sequence[str], None] = ('b84cd0c07ab8', 'force_external_item_id')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
