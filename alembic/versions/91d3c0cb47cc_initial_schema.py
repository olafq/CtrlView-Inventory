"""initial clean schema"""

from alembic import op
import sqlalchemy as sa

revision = "91d3c0dc47cc"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # --------------------
    # Channels
    # --------------------
    op.create_table(
        "channels",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String, nullable=False, unique=True),
        sa.Column("type", sa.String, nullable=False),
    )

    # --------------------
    # Products
    # --------------------
    op.create_table(
        "products",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("sku", sa.String, nullable=False, unique=True),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("description", sa.String),
        sa.Column("cost", sa.Numeric(12, 2)),
        sa.Column("stock_total", sa.Integer, nullable=False, default=0),
        sa.Column("stock_reserved", sa.Integer, nullable=False, default=0),
        sa.Column("stock_available", sa.Integer, nullable=False, default=0),
        sa.Column("low_stock_threshold", sa.Integer, nullable=False, default=0),
        sa.Column("is_active", sa.Boolean, nullable=False, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --------------------
    # External Items
    # --------------------
    op.create_table(
        "external_items",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "product_id",
            sa.Integer,
            sa.ForeignKey("products.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "channel_id",
            sa.Integer,
            sa.ForeignKey("channels.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("external_item_id", sa.String, nullable=False, index=True),
        sa.Column("external_sku", sa.String),
        sa.Column("price", sa.Numeric(12, 2)),
        sa.Column("stock", sa.Integer, nullable=False, default=0),
        sa.Column("is_active", sa.Boolean, nullable=False, default=True),
        sa.Column("status", sa.String),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint(
            "channel_id",
            "external_item_id",
            name="uq_external_item_channel",
        ),
    )

    # --------------------
    # MercadoLibre Auth
    # --------------------
    op.create_table(
        "mercadolibre_auth",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "channel_id",
            sa.Integer,
            sa.ForeignKey("channels.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("ml_user_id", sa.Integer, nullable=False),
        sa.Column("access_token", sa.String, nullable=False),
        sa.Column("refresh_token", sa.String, nullable=False),
        sa.Column("token_type", sa.String),
        sa.Column("scope", sa.String),
        sa.Column("expires_at", sa.DateTime, nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table("mercadolibre_auth")
    op.drop_table("external_items")
    op.drop_table("products")
    op.drop_table("channels")
