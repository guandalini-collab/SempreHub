"""Ingresso independente, liderança e análise financeira do aluno."""
from alembic import op
import sqlalchemy as sa
revision = "0009_ingresso_lideranca"
down_revision = "0008_diagnosticos"
branch_labels = None
depends_on = None

def upgrade():
    db = op.get_bind()
    def faltam(tabela, nomes):
        existentes = {c["name"] for c in sa.inspect(db).get_columns(tabela)}
        return set(nomes) - existentes
    colunas = faltam("turmas", ["visivel_ingresso", "formacao_encerrada"])
    if colunas:
        with op.batch_alter_table("turmas") as b:
            if "visivel_ingresso" in colunas:
                b.add_column(sa.Column("visivel_ingresso", sa.Boolean(), nullable=False, server_default=sa.true()))
            if "formacao_encerrada" in colunas:
                b.add_column(sa.Column("formacao_encerrada", sa.Boolean(), nullable=False, server_default=sa.false()))
    colunas = faltam("empresas", ["lider_id", "proximo_lider_id", "votos_lider"])
    if colunas:
        with op.batch_alter_table("empresas") as b:
            for nome in ("lider_id", "proximo_lider_id"):
                if nome in colunas:
                    b.add_column(sa.Column(nome, sa.Integer(), nullable=True))
                    b.create_foreign_key("fk_empresa_"+nome, "usuarios", [nome], ["id"])
            if "votos_lider" in colunas:
                b.add_column(sa.Column("votos_lider", sa.JSON(), nullable=False, server_default="{}"))
    if faltam("decisoes", ["analise_financeira"]):
        with op.batch_alter_table("decisoes") as b:
            b.add_column(sa.Column("analise_financeira", sa.String(6000), nullable=False, server_default=""))
    if "matriculas_turma" not in sa.inspect(db).get_table_names():
        op.create_table("matriculas_turma",
            sa.Column("aluno_id", sa.Integer(), sa.ForeignKey("usuarios.id"), primary_key=True),
            sa.Column("turma_id", sa.Integer(), sa.ForeignKey("turmas.id"), nullable=False),
            sa.Column("autorizada_turma_id", sa.Integer(), sa.ForeignKey("turmas.id"), nullable=True),
            sa.Column("historico", sa.JSON(), nullable=False))
        op.create_index("ix_matriculas_turma_turma_id", "matriculas_turma", ["turma_id"])
    # Preserva equipes existentes sem substituir uma liderança já registrada.
    db.execute(sa.text("UPDATE empresas SET lider_id = aluno_id WHERE lider_id IS NULL AND turma_id IN (SELECT id FROM turmas WHERE modo_equipe = true)"))
    alunos = list(db.execute(sa.text("SELECT aluno_id, turma_id, empresa_id FROM membros_empresa UNION SELECT aluno_id, turma_id, id AS empresa_id FROM empresas ORDER BY empresa_id DESC")).mappings())
    vistos = set(db.execute(sa.text("SELECT aluno_id FROM matriculas_turma")).scalars())
    table = sa.table("matriculas_turma", sa.column("aluno_id", sa.Integer()), sa.column("turma_id", sa.Integer()), sa.column("historico", sa.JSON()))
    for row in alunos:
        if row["aluno_id"] not in vistos:
            db.execute(table.insert().values(aluno_id=row["aluno_id"], turma_id=row["turma_id"], historico=[]))
            vistos.add(row["aluno_id"])

def downgrade():
    raise RuntimeError("Preserve os vínculos e registros de liderança; restaure um backup planejado.")
