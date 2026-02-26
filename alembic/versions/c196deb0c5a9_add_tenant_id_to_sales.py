from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = 'c196deb0c5a9'
down_revision = 'b60c561de27a'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    columns = [col["name"] for col in inspector.get_columns("sales")]

    if "tenant_id" not in columns:
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