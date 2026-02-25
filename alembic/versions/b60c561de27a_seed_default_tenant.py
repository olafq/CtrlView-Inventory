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
    op.add_column(
        "sales",
        sa.Column("tenant_id", sa.Integer(), nullable=True)
    )

    op.create_foreign_key(
        "fk_sales_tenant",
        "sales",
        "tenants",
        ["tenant_id"],
        ["id"],
    )

def downgrade():
    op.drop_constraint("fk_sales_tenant", "sales", type_="foreignkey")
    op.drop_column("sales", "tenant_id")