"""Revisão explícita das áreas da decisão, preservada por rodada."""
from alembic import op
import sqlalchemy as sa
revision = '0007_revisao_areas'
down_revision = '0006_mercado'
branch_labels = None
depends_on = None

def upgrade():
    if 'revisao_areas' not in {c['name'] for c in sa.inspect(op.get_bind()).get_columns('decisoes')}:
        op.add_column('decisoes', sa.Column('revisao_areas', sa.JSON(), nullable=True))

def downgrade():
    op.drop_column('decisoes', 'revisao_areas')
