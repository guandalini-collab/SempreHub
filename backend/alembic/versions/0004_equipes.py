"""Equipes, cargos, revisões de decisões e participação individual.

As turmas existentes continuam individuais. Esta revisão não recria empresas,
decisões ou resultados e não reinicia suas rodadas ou versões de sessão.
"""

from alembic import op
import sqlalchemy as sa

revision = "0004_equipes"
down_revision = "0003_versao_sessao"
branch_labels = None
depends_on = None


def _novas_tabelas():
    return {
        "membros_empresa": [
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("empresa_id", sa.Integer(), nullable=False),
            sa.Column("turma_id", sa.Integer(), nullable=False),
            sa.Column("aluno_id", sa.Integer(), nullable=False),
            sa.Column("cargos", sa.JSON(), nullable=False),
            sa.Column("criado_em", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"]),
            sa.ForeignKeyConstraint(["turma_id"], ["turmas.id"]),
            sa.ForeignKeyConstraint(["aluno_id"], ["usuarios.id"]),
            sa.UniqueConstraint("turma_id", "aluno_id", name="uq_membro_turma_aluno"),
        ],
        "aprovacoes_decisao": [
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("decisao_id", sa.Integer(), nullable=False),
            sa.Column("empresa_id", sa.Integer(), nullable=False),
            sa.Column("aluno_id", sa.Integer(), nullable=False),
            sa.Column("rodada", sa.Integer(), nullable=False),
            sa.Column("versao", sa.Integer(), nullable=False),
            sa.Column("conteudo", sa.JSON(), nullable=False),
            sa.Column("aprovado_em", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["decisao_id"], ["decisoes.id"]),
            sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"]),
            sa.ForeignKeyConstraint(["aluno_id"], ["usuarios.id"]),
            sa.UniqueConstraint("decisao_id", "versao", "aluno_id", name="uq_aprovacao_decisao_versao_aluno"),
        ],
        "registros_equipe": [
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("empresa_id", sa.Integer(), nullable=False),
            sa.Column("aluno_id", sa.Integer(), nullable=False),
            sa.Column("rodada", sa.Integer(), nullable=False),
            sa.Column("versao", sa.Integer(), nullable=False),
            sa.Column("acao", sa.String(40), nullable=False),
            sa.Column("detalhes", sa.JSON(), nullable=False),
            sa.Column("data", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"]),
            sa.ForeignKeyConstraint(["aluno_id"], ["usuarios.id"]),
        ],
    }


def upgrade():
    conexao = op.get_bind()
    novas = _novas_tabelas()
    inspetor = sa.inspect(conexao)
    for tabela, definicoes in novas.items():
        if inspetor.has_table(tabela):
            existentes = {c["name"] for c in inspetor.get_columns(tabela)}
            esperadas = {c.name for c in definicoes if isinstance(c, sa.Column)}
            if esperadas - existentes:
                raise RuntimeError(f"Banco incompatível: revise a estrutura de {tabela} antes de migrar.")

    for tabela, coluna in (
        ("turmas", sa.Column("modo_equipe", sa.Boolean(), nullable=False, server_default=sa.false())),
        ("empresas", sa.Column("codigo_convite", sa.String(64), nullable=True)),
        ("decisoes", sa.Column("versao", sa.Integer(), nullable=False, server_default="0")),
    ):
        existentes = {c["name"] for c in sa.inspect(conexao).get_columns(tabela)}
        if coluna.name not in existentes:
            op.add_column(tabela, coluna)

    for tabela, definicoes in novas.items():
        if not sa.inspect(conexao).has_table(tabela):
            op.create_table(tabela, *definicoes)

    indices = [("empresas", "codigo_convite", True)]
    indices.extend(("membros_empresa", coluna, False) for coluna in ("empresa_id", "turma_id", "aluno_id"))
    indices.extend(("aprovacoes_decisao", coluna, False) for coluna in ("decisao_id", "empresa_id", "aluno_id"))
    indices.extend(("registros_equipe", coluna, False) for coluna in ("empresa_id", "aluno_id"))
    for tabela, coluna, unico in indices:
        nome = f"ix_{tabela}_{coluna}"
        existentes = {indice["name"] for indice in sa.inspect(conexao).get_indexes(tabela)}
        if nome not in existentes:
            op.create_index(nome, tabela, [coluna], unique=unico)


def downgrade():
    raise RuntimeError("Remover equipes apagaria participação e assinaturas; restaure um backup planejado.")
