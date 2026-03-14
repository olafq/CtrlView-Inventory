"""merge tenant branches

Revision ID: 826a6c22fa91
Revises: c26a41a3cd60, add_tenant_id_core
Create Date: 2026-03-14 09:19:05.419270

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '826a6c22fa91'
down_revision: Union[str, Sequence[str], None] = ('c26a41a3cd60', 'add_tenant_id_core')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
