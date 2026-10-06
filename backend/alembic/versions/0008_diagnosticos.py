"""Diagnósticos do sistema preservados por empresa e rodada."""
from alembic import op
import sqlalchemy as sa
revision='0008_diagnosticos'
down_revision='0007_revisao_areas'
branch_labels=None
depends_on=None

def upgrade():
    if 'diagnosticos_estrategicos' not in sa.inspect(op.get_bind()).get_table_names():
        op.create_table('diagnosticos_estrategicos',sa.Column('id',sa.Integer(),primary_key=True),sa.Column('empresa_id',sa.Integer(),sa.ForeignKey('empresas.id'),nullable=False),sa.Column('edicao_id',sa.Integer(),sa.ForeignKey('conteudos_mercado.id'),nullable=False),sa.Column('rodada',sa.Integer(),nullable=False),sa.Column('dados',sa.JSON(),nullable=False),sa.Column('criado_em',sa.DateTime(),nullable=False),sa.UniqueConstraint('empresa_id','rodada','edicao_id',name='uq_diagnostico_estrategico'))
        op.create_index('ix_diagnosticos_estrategicos_empresa_id','diagnosticos_estrategicos',['empresa_id'])

def downgrade():
    raise RuntimeError('Preserve os diagnósticos históricos; restaure um backup planejado.')
