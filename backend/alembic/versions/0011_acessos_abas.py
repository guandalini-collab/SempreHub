"""Registro prospectivo das abas acessadas pelos alunos."""
from alembic import op
import sqlalchemy as sa
revision = '0011_acessos_abas'
down_revision = '0010_prazos'
branch_labels = depends_on = None


def upgrade():
    if 'acessos_abas' not in sa.inspect(op.get_bind()).get_table_names():
        op.create_table('acessos_abas', sa.Column('id',sa.Integer(),primary_key=True),
                        sa.Column('aluno_id',sa.Integer(),sa.ForeignKey('usuarios.id'),nullable=False),
                        sa.Column('empresa_id',sa.Integer(),sa.ForeignKey('empresas.id'),nullable=False),
                        sa.Column('rodada',sa.Integer(),nullable=False),sa.Column('aba',sa.String(80),nullable=False),
                        sa.Column('criado_em',sa.DateTime(),nullable=False))
        op.create_index('ix_acessos_abas_aluno_id','acessos_abas',['aluno_id'])
        op.create_index('ix_acessos_abas_empresa_id','acessos_abas',['empresa_id'])


def downgrade():
    raise RuntimeError('Preserve os registros de participação; restaure um backup planejado.')
