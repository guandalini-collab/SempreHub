"""Consultas oficiais com histórico imutável e controle de execução."""
from alembic import op
import sqlalchemy as sa
revision='0013_boletins_oficiais'
down_revision='0012_observacoes_semanais'
branch_labels=depends_on=None


def upgrade():
    nomes=sa.inspect(op.get_bind()).get_table_names()
    if 'boletins_oficiais' not in nomes:
        op.create_table('boletins_oficiais',sa.Column('id',sa.Integer(),primary_key=True),sa.Column('dados',sa.JSON(),nullable=False),sa.Column('consultado_em',sa.DateTime(),nullable=False))
    if 'consultas_oficiais' not in nomes:
        op.create_table('consultas_oficiais',sa.Column('id',sa.Integer(),primary_key=True),sa.Column('tentado_em',sa.DateTime()),sa.Column('ocupado_ate',sa.DateTime()),sa.Column('estado',sa.String(80),nullable=False),sa.Column('erro',sa.String(500)))


def downgrade():
    raise RuntimeError('O histórico de fontes oficiais deve ser preservado.')
