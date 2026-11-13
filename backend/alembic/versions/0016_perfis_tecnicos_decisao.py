"""preserva contratações por perfil na decisão semanal

Revision ID: 0016_perfis_tecnicos_decisao
Revises: 0015_eventos
Create Date: 2026-11-12
"""

from alembic import op
import sqlalchemy as sa


revision = "0016_perfis_tecnicos_decisao"
down_revision = "0015_eventos"
branch_labels = None
depends_on = None


def upgrade():
    # Alguns bancos locais antigos foram criados diretamente pelo modelo, sem
    # a tabela alembic_version. Neles as colunas já podem existir. A revisão
    # precisa adotá-los sem falhar nem reescrever dados.
    colunas = {coluna["name"] for coluna in sa.inspect(op.get_bind()).get_columns("decisoes")}
    if "contratar_tecnicos" not in colunas:
        op.add_column(
            "decisoes",
            # Rodadas históricas não podem ganhar uma escolha que não existia.
            # NULL significa "dado inexistente no motor daquela rodada"; decisões
            # novas recebem zero pela validação de entrada.
            sa.Column("contratar_tecnicos", sa.Integer(), nullable=True),
        )
    if "contratar_especialistas" not in colunas:
        op.add_column(
            "decisoes",
            sa.Column("contratar_especialistas", sa.Integer(), nullable=True),
        )


def downgrade():
    op.drop_column("decisoes", "contratar_especialistas")
    op.drop_column("decisoes", "contratar_tecnicos")
