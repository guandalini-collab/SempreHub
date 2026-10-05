"""Versiona sessões para revogá-las após uma redefinição de senha."""

from alembic import op
import sqlalchemy as sa

revision = "0003_versao_sessao"
down_revision = "0002_contas_teste"
branch_labels = None
depends_on = None


def upgrade():
    colunas = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("usuarios")}
    if "versao_sessao" not in colunas:
        op.execute("ALTER TABLE usuarios ADD COLUMN versao_sessao INTEGER NOT NULL DEFAULT 0")


def downgrade():
    raise RuntimeError("Remover a versão de sessão afetaria a revogação de acessos; restaure um backup.")
