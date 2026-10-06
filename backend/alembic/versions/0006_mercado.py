"""Conteúdo de mercado e planos preservados por rodada."""
from alembic import op
import sqlalchemy as sa
revision = "0006_mercado"
down_revision = "0005_simulacao_avancada"
branch_labels = None
depends_on = None

def upgrade():
    conn = op.get_bind()
    if "plano_comercial" not in {c["name"] for c in sa.inspect(conn).get_columns("decisoes")}:
        op.add_column("decisoes", sa.Column("plano_comercial", sa.JSON(), nullable=True))
    if "conteudos_mercado" not in sa.inspect(conn).get_table_names():
        op.create_table("conteudos_mercado",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("turma_id", sa.Integer(), sa.ForeignKey("turmas.id"), nullable=False),
            sa.Column("rodada", sa.Integer(), nullable=False),
            sa.Column("publicado", sa.Boolean(), nullable=False),
            sa.Column("dados", sa.JSON(), nullable=False),
            sa.Column("criado_em", sa.DateTime(), nullable=False))
        op.create_index("ix_conteudos_mercado_turma_id", "conteudos_mercado", ["turma_id"])
    if "relatorios_empresariais" not in sa.inspect(conn).get_table_names():
        op.create_table("relatorios_empresariais",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("empresa_id", sa.Integer(), sa.ForeignKey("empresas.id"), nullable=False),
            sa.Column("rodada", sa.Integer(), nullable=False),
            sa.Column("texto", sa.String(24000), nullable=False),
            sa.Column("criado_em", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("empresa_id", "rodada", name="uq_relatorio_empresarial"))
        op.create_index("ix_relatorios_empresariais_empresa_id", "relatorios_empresariais", ["empresa_id"])

def downgrade():
    raise RuntimeError("Preserve as edições e relatórios; restaure um backup planejado.")
