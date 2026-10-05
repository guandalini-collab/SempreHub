"""Estado e snapshots opcionais dos motores tradicional e startup.

Todas as turmas existentes permanecem no motor LEGADO. Nenhuma decisão,
resultado, assinatura, conta ou rodada anterior é alterada nesta revisão.
"""

from alembic import op
import sqlalchemy as sa

revision = "0005_simulacao_avancada"
down_revision = "0004_equipes"
branch_labels = None
depends_on = None


def upgrade():
    conexao = op.get_bind()
    colunas = (
        ("turmas", sa.Column("modo_jogo", sa.String(20), nullable=False, server_default="LEGADO")),
        ("turmas", sa.Column("cenario", sa.String(10), nullable=False, server_default="ZERO")),
        ("turmas", sa.Column("configuracao_simulacao", sa.JSON(), nullable=True)),
        ("turmas", sa.Column("versao_motor", sa.Integer(), nullable=False, server_default="1")),
        ("empresas", sa.Column("estado_simulacao", sa.JSON(), nullable=True)),
        ("decisoes", sa.Column("simulacao", sa.JSON(), nullable=True)),
        ("resultados", sa.Column("detalhes_simulacao", sa.JSON(), nullable=True)),
    )
    for tabela, coluna in colunas:
        existentes = {c["name"] for c in sa.inspect(conexao).get_columns(tabela)}
        if coluna.name not in existentes:
            op.add_column(tabela, coluna)


def downgrade():
    raise RuntimeError(
        "Remover os motores avançados apagaria estoques e memória financeira; "
        "restaure um backup planejado."
    )
