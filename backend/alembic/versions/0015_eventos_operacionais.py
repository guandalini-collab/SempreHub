"""Registra ocorrências operacionais individuais e auditáveis."""

from alembic import op
import sqlalchemy as sa


revision = "0015_eventos"
down_revision = "0014_prop_agenda"
branch_labels = depends_on = None


def upgrade():
    bind = op.get_bind()
    if "eventos_operacionais" in sa.inspect(bind).get_table_names():
        return
    op.create_table(
        "eventos_operacionais",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("turma_id", sa.Integer(), sa.ForeignKey("turmas.id"), nullable=False),
        sa.Column("empresa_id", sa.Integer(), sa.ForeignKey("empresas.id"), nullable=False),
        sa.Column("rodada_inicio", sa.Integer(), nullable=False),
        sa.Column("rodada_fim", sa.Integer(), nullable=False),
        sa.Column("codigo", sa.String(length=64), nullable=False),
        sa.Column("departamento", sa.String(length=32), nullable=False),
        sa.Column("titulo", sa.String(length=160), nullable=False),
        sa.Column("narrativa", sa.String(length=1200), nullable=False),
        sa.Column("probabilidade_base", sa.Float(), nullable=False),
        sa.Column("probabilidade_aplicada", sa.Float(), nullable=False),
        sa.Column("semente", sa.String(length=64), nullable=False),
        sa.Column("fatores", sa.JSON(), nullable=False),
        sa.Column("impacto", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="ATIVO"),
        sa.Column("criado_em", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("empresa_id", "rodada_inicio", "codigo", name="uq_evento_operacional_empresa_rodada_codigo"),
    )
    op.create_index("ix_eventos_operacionais_turma_id", "eventos_operacionais", ["turma_id"])
    op.create_index("ix_eventos_operacionais_empresa_id", "eventos_operacionais", ["empresa_id"])
    op.create_index("ix_eventos_operacionais_rodada_inicio", "eventos_operacionais", ["rodada_inicio"])


def downgrade():
    raise RuntimeError("Eventos operacionais fazem parte do histórico auditável; restaure um backup planejado.")
