"""populate tenant_id in sales

Revision ID: 1e51b307cc05
Revises: c196deb0c5a9
Create Date: 2026-02-25 23:38:13.791110

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1e51b307cc05'
down_revision: Union[str, Sequence[str], None] = 'c196deb0c5a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.execute("UPDATE sales SET tenant_id = 1 WHERE tenant_id IS NULL")

def downgrade():
    op.execute("UPDATE sales SET tenant_id = NULL")
