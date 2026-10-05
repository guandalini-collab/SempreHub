"""Identifica o professor que criou uma conta de teste."""

from alembic import op
import sqlalchemy as sa

revision = "0002_contas_teste"
down_revision = "0001_base"
branch_labels = None
depends_on = None


def upgrade():
    colunas = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("usuarios")}
    if "criado_por_id" not in colunas:
        # FK inline compatível com SQLite, sem reconstruir a tabela de usuários.
        op.execute("ALTER TABLE usuarios ADD COLUMN criado_por_id INTEGER REFERENCES usuarios(id)")


def downgrade():
    raise RuntimeError("Esta revisão preserva contas existentes; restaure um backup para voltar.")
