from alembic import op

revision = 'b60c561de27a'
down_revision = '49ab6a3e1c39'
branch_labels = None
depends_on = None

def upgrade():
    op.execute("""
        INSERT INTO tenants (id, name, is_active)
        VALUES (1, 'Default Tenant', true)
    """)

def downgrade():
    op.execute("DELETE FROM tenants WHERE id = 1")