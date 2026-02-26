from alembic import op
import sqlalchemy as sa

revision = '1e51b307cc05'
down_revision = 'c196deb0c5a9'
branch_labels = None
depends_on = None


def upgrade():
    # Crear tenant default si no existe
    op.execute("""
        INSERT INTO tenants (id, name, is_active)
        SELECT 1, 'Default Tenant', true
        WHERE NOT EXISTS (
            SELECT 1 FROM tenants WHERE id = 1
        );
    """)

    # Ahora sí poblar sales
    op.execute("""
        UPDATE sales
        SET tenant_id = 1
        WHERE tenant_id IS NULL
    """)


def downgrade():
    op.execute("UPDATE sales SET tenant_id = NULL")