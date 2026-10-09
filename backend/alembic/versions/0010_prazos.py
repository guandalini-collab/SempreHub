"""Prazo opcional e vinculado à rodada, sem modificar registros existentes."""
from alembic import op
import sqlalchemy as sa
revision = "0010_prazos"
down_revision = "0009_ingresso_lideranca"
branch_labels = depends_on = None

def upgrade():
    existentes = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("turmas")}
    with op.batch_alter_table("turmas") as b:
        for nome, tipo in [("prazo_rodada", sa.DateTime()), ("prazo_numero_rodada", sa.Integer())]:
            if nome not in existentes:
                b.add_column(sa.Column(nome, tipo, nullable=True))

def downgrade():
    raise RuntimeError("Preserve os prazos registrados; restaure um backup planejado.")
