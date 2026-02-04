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
    pass