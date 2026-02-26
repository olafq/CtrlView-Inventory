"""add tenant_id to sales

Revision ID: c196deb0c5a9
Revises: b60c561de27a
Create Date: 2026-02-25 23:37:14.290621

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c196deb0c5a9'
down_revision: Union[str, Sequence[str], None] = 'b60c561de27a'
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