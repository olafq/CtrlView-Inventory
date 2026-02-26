"""seed default tenant

Revision ID: b60c561de27a
Revises: 49ab6a3e1c39
Create Date: 2026-02-25 19:25:58.684708

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b60c561de27a'
down_revision: Union[str, Sequence[str], None] = '49ab6a3e1c39'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade():
    op.execute("""
        INSERT INTO tenants (id, name, slug, is_active)
        VALUES (1, 'default', 'default', true)
        ON CONFLICT (id) DO NOTHING
    """)

def downgrade():
    op.execute("DELETE FROM tenants WHERE id = 1")