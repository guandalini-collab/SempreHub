"""Separa proprietário e agenda as rodadas pelo calendário acadêmico."""

from alembic import op
import sqlalchemy as sa


# Alembic criou a tabela alembic_version como VARCHAR(32) nas versões
# anteriores. A revisão precisa caber nela para que a atualização funcione em
# bancos já existentes, inclusive o de produção.
revision = "0014_prop_agenda"
down_revision = "0013_boletins_oficiais"
branch_labels = depends_on = None


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        # A enum criada pelo SQLAlchemy usa o nome da classe em minúsculas.
        op.execute("ALTER TYPE papel ADD VALUE IF NOT EXISTS 'PROPRIETARIO'")
    elif bind.dialect.name == "sqlite":
        # SQLite materializa Enum como VARCHAR; é preciso ampliar o tipo para
        # que o esquema reflita o novo papel também nos ambientes locais.
        with op.batch_alter_table("usuarios") as lote:
            lote.alter_column(
                "papel",
                existing_type=sa.String(length=9),
                type_=sa.Enum("ALUNO", "PROFESSOR", "PROPRIETARIO", name="papel"),
                existing_nullable=False,
            )
    colunas = {col["name"] for col in sa.inspect(bind).get_columns("turmas")}
    if "abertura_rodada" not in colunas:
        op.add_column("turmas", sa.Column("abertura_rodada", sa.DateTime(), nullable=True))
    if "agenda_academica" not in colunas:
        op.add_column("turmas", sa.Column("agenda_academica", sa.JSON(), nullable=True))


def downgrade():
    raise RuntimeError("A agenda acadêmica e os papéis de acesso devem ser preservados; restaure um backup planejado.")
