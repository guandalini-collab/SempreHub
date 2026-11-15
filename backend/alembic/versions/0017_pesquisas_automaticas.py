"""registra a pesquisa automática de mercado por rodada

Revision ID: 0017_pesquisas_automaticas
Revises: 0016_perfis_tecnicos_decisao
Create Date: 2026-11-15
"""

from alembic import op
import sqlalchemy as sa


revision = "0017_pesquisas_automaticas"
down_revision = "0016_perfis_tecnicos_decisao"
branch_labels = None
depends_on = None


def upgrade():
    # Bancos criados diretamente pelos modelos já podem ter a tabela.
    if "pesquisas_automaticas" in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "pesquisas_automaticas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("turma_id", sa.Integer(), sa.ForeignKey("turmas.id"), nullable=False),
        sa.Column("rodada", sa.Integer(), nullable=False),
        sa.Column("situacao", sa.String(length=20), nullable=False),
        sa.Column("tentativas", sa.Integer(), nullable=False),
        sa.Column("mensagem", sa.String(length=2000), nullable=True),
        sa.Column("conteudo_id", sa.Integer(), sa.ForeignKey("conteudos_mercado.id"), nullable=True),
        sa.Column("proxima_tentativa", sa.DateTime(), nullable=True),
        sa.Column("atualizado_em", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("turma_id", "rodada", name="uq_pesquisa_automatica_turma_rodada"),
    )
    op.create_index("ix_pesquisas_automaticas_turma_id", "pesquisas_automaticas", ["turma_id"])


def downgrade():
    op.drop_index("ix_pesquisas_automaticas_turma_id", table_name="pesquisas_automaticas")
    op.drop_table("pesquisas_automaticas")
