from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "add_tenant_id_core"
down_revision = "b60c561de27a"
branch_labels = None
depends_on = None


def upgrade():

    # -------------------------
    # CHANNELS
    # -------------------------
    op.add_column(
        "channels",
        sa.Column("tenant_id", sa.Integer(), nullable=True)
    )

    op.create_foreign_key(
        "fk_channels_tenant",
        "channels",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="CASCADE"
    )

    op.execute("UPDATE channels SET tenant_id = 1")

    op.alter_column(
        "channels",
        "tenant_id",
        nullable=False
    )

    op.create_unique_constraint(
        "uq_channels_tenant_name",
        "channels",
        ["tenant_id", "name"]
    )

    # -------------------------
    # PRODUCTS
    # -------------------------
    op.add_column(
        "products",
        sa.Column("tenant_id", sa.Integer(), nullable=True)
    )

    op.create_foreign_key(
        "fk_products_tenant",
        "products",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="CASCADE"
    )

    op.execute("UPDATE products SET tenant_id = 1")

    op.alter_column(
        "products",
        "tenant_id",
        nullable=False
    )

    op.create_unique_constraint(
        "uq_products_tenant_sku",
        "products",
        ["tenant_id", "sku"]
    )

    # -------------------------
    # EXTERNAL ITEMS
    # -------------------------
    op.add_column(
        "external_items",
        sa.Column("tenant_id", sa.Integer(), nullable=True)
    )

    op.create_foreign_key(
        "fk_external_items_tenant",
        "external_items",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="CASCADE"
    )

    op.execute("UPDATE external_items SET tenant_id = 1")

    op.alter_column(
        "external_items",
        "tenant_id",
        nullable=False
    )

    op.create_unique_constraint(
        "uq_external_item_tenant_channel_item",
        "external_items",
        ["tenant_id", "channel_id", "external_item_id"]
    )

    # -------------------------
    # MERCADOLIBRE AUTH
    # -------------------------
    op.add_column(
        "mercadolibre_auth",
        sa.Column("tenant_id", sa.Integer(), nullable=True)
    )

    op.create_foreign_key(
        "fk_ml_auth_tenant",
        "mercadolibre_auth",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="CASCADE"
    )

    op.execute("UPDATE mercadolibre_auth SET tenant_id = 1")

    op.alter_column(
        "mercadolibre_auth",
        "tenant_id",
        nullable=False
    )

    op.create_unique_constraint(
        "uq_ml_auth_tenant_channel",
        "mercadolibre_auth",
        ["tenant_id", "channel_id"]
    )

    # -------------------------
    # STOCK MOVEMENTS
    # -------------------------
    op.add_column(
        "stock_movements",
        sa.Column("tenant_id", sa.Integer(), nullable=True)
    )

    op.create_foreign_key(
        "fk_stock_movements_tenant",
        "stock_movements",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="CASCADE"
    )

    op.execute("UPDATE stock_movements SET tenant_id = 1")

    op.alter_column(
        "stock_movements",
        "tenant_id",
        nullable=False
    )

    # -------------------------
    # CATALOG IMPORT RUNS
    # -------------------------
    op.add_column(
        "catalog_import_runs",
        sa.Column("tenant_id", sa.Integer(), nullable=True)
    )

    op.create_foreign_key(
        "fk_catalog_import_runs_tenant",
        "catalog_import_runs",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="CASCADE"
    )

    op.execute("UPDATE catalog_import_runs SET tenant_id = 1")

    op.alter_column(
        "catalog_import_runs",
        "tenant_id",
        nullable=False
    )


def downgrade():
    pass