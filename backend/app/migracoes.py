"""Criação do banco e ajustes simples de esquema em bancos já existentes.

`create_all` cria tabelas novas, mas não acrescenta colunas a tabelas antigas. Aqui ficam
as colunas adicionadas depois da primeira versão, para que um banco já em uso continue
funcionando sem perder dados. Quando o projeto crescer, convém migrar para o Alembic.
"""

from sqlalchemy import inspect, text

from .database import Base, engine

# (tabela, coluna, definição SQL compatível com SQLite e PostgreSQL)
COLUNAS_ADICIONADAS = [
    ("usuarios", "criado_por_id", "INTEGER REFERENCES usuarios(id)"),
    ("usuarios", "versao_sessao", "INTEGER NOT NULL DEFAULT 0"),
]


def preparar_banco() -> None:
    Base.metadata.create_all(bind=engine)
    inspetor = inspect(engine)
    with engine.begin() as conexao:
        for tabela, coluna, definicao in COLUNAS_ADICIONADAS:
            existentes = {c["name"] for c in inspetor.get_columns(tabela)}
            if coluna not in existentes:
                conexao.execute(text(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {definicao}"))
