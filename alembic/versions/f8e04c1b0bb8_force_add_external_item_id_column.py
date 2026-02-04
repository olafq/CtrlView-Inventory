from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

revision = "force_external_item_id"
down_revision = "6fca767aedff"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)

    columns = [col["name"] for col in inspector.get_columns("external_items")]

    if "external_item_id" not in columns:
        op.add_column(
            "external_items",
            sa.Column("external_item_id", sa.String(), nullable=False),
        )
        op.create_index(
            "ix_external_items_external_item_id",
            "external_items",
            ["external_item_id"],
        )


def downgrade():
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)

    columns = [col["name"] for col in inspector.get_columns("external_items")]

    if "external_item_id" in columns:
        op.drop_index(
            "ix_external_items_external_item_id",
            table_name="external_items",
        )
        op.drop_column("external_items", "external_item_id")
