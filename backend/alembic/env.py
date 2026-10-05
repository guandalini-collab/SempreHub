"""Migrações online, usando a mesma configuração de banco da aplicação."""

from contextlib import nullcontext

from alembic import context
from sqlalchemy import text

from app import models  # noqa: F401 — registra todos os modelos no metadata.
from app.database import Base, engine


def executar(conexao):
    # Uma só migração por banco de cada vez, inclusive em inicializações
    # simultâneas. A revisão e todas as alterações confirmam juntas.
    transacao = nullcontext() if conexao.in_transaction() else conexao.begin()
    with transacao:
        if conexao.dialect.name == "postgresql":
            conexao.execute(text("SELECT pg_advisory_xact_lock(734601298214)"))
        elif conexao.dialect.name == "sqlite":
            # Também torna o DDL transacional no driver sqlite3 legado.
            # Uma conexão externa pode já ter iniciado a transação física.
            if not conexao.connection.driver_connection.in_transaction:
                conexao.exec_driver_sql("BEGIN IMMEDIATE")
        context.configure(
            connection=conexao,
            target_metadata=Base.metadata,
            compare_type=True,
            compare_server_default=True,
            render_as_batch=conexao.dialect.name == "sqlite",
            transactional_ddl=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    raise RuntimeError(
        "Execute as migrações com conexão ao banco, sem --sql: "
        "a adoção inicial precisa verificar a estrutura existente."
    )

conexao = context.config.attributes.get("connection")
if conexao is not None:
    executar(conexao)
else:
    with engine.connect() as conexao:
        executar(conexao)
