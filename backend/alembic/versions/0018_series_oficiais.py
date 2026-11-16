"""guarda séries oficiais calculadas (sazonalidade da PMC/IBGE)

Revision ID: 0018_series_oficiais
Revises: 0017_pesquisas_automaticas
Create Date: 2026-11-16
"""

from alembic import op
import sqlalchemy as sa


revision = "0018_series_oficiais"
down_revision = "0017_pesquisas_automaticas"
branch_labels = None
depends_on = None


def upgrade():
    if "series_oficiais" in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "series_oficiais",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("chave", sa.String(length=60), nullable=False, unique=True),
        sa.Column("dados", sa.JSON(), nullable=True),
        sa.Column("tentado_em", sa.DateTime(), nullable=True),
        sa.Column("erro", sa.String(length=500), nullable=True),
    )


def downgrade():
    op.drop_table("series_oficiais")
