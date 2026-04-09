"""add external_title to external_items

Revision ID: e8198c93e386
Revises: 33fe80fd0e3b
Create Date: 2026-04-08 21:16:25.386219

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e8198c93e386'
down_revision: Union[str, Sequence[str], None] = '33fe80fd0e3b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column('external_items', sa.Column('external_title', sa.String(), nullable=True))

def downgrade():
    op.drop_column('external_items', 'external_title')