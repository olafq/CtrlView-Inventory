"""add slug to tenants

Revision ID: c26a41a3cd60
Revises: 290d9327e565
Create Date: 2026-02-26 19:32:15.823353

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c26a41a3cd60'
down_revision: Union[str, Sequence[str], None] = '290d9327e565'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # 1️⃣ Agregar columna como nullable primero
    op.add_column(
        "tenants",
        sa.Column("slug", sa.String(), nullable=True)
    )

    # 2️⃣ Poblar slug para tenants existentes
    op.execute("""
        UPDATE tenants
        SET slug = 'default'
        WHERE slug IS NULL
    """)

    # 3️⃣ Hacerla NOT NULL
    op.alter_column(
        "tenants",
        "slug",
        existing_type=sa.String(),
        nullable=False
    )

    # 4️⃣ Crear índice único
    op.create_index(
        "ix_tenants_slug",
        "tenants",
        ["slug"],
        unique=True
    )

    op.create_index(
        "ix_tenants_slug",
        "tenants",
        ["slug"],
        unique=True
    )


def downgrade():
    op.drop_index("ix_tenants_slug", table_name="tenants")
    op.drop_column("tenants", "slug")