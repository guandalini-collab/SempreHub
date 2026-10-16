"""Bases informadas para análise, isoladas dos snapshots do motor."""
from alembic import op
import sqlalchemy as sa
revision='0012_observacoes_semanais'
down_revision='0011_acessos_abas'
branch_labels=depends_on=None


def upgrade():
    if 'observacoes_semanais' not in sa.inspect(op.get_bind()).get_table_names():
        op.create_table('observacoes_semanais',sa.Column('id',sa.Integer(),primary_key=True),
                        sa.Column('empresa_id',sa.Integer(),sa.ForeignKey('empresas.id'),nullable=False),
                        sa.Column('rodada',sa.Integer(),nullable=False),sa.Column('dados',sa.JSON(),nullable=False),
                        sa.Column('atualizado_por',sa.Integer(),sa.ForeignKey('usuarios.id'),nullable=False),
                        sa.Column('atualizado_em',sa.DateTime(),nullable=False),
                        sa.UniqueConstraint('empresa_id','rodada',name='uq_observacao_semana'))


def downgrade():
    raise RuntimeError('Preserve as observações; restaure um backup planejado.')
