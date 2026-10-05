"""Atualiza o banco pelas revisões versionadas antes de iniciar a API."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy.engine import Engine

from .database import engine


def configuracao_alembic() -> Config:
    backend = Path(__file__).resolve().parents[1]
    configuracao = Config(str(backend / "alembic.ini"))
    configuracao.set_main_option("script_location", str(backend / "alembic"))
    return configuracao


def preparar_banco(banco: Engine = None) -> None:
    # A conexão passa fora do ConfigParser: URLs e credenciais não são gravadas
    # no alembic.ini nem precisam de interpolação/escape.
    with (banco if banco is not None else engine).connect() as conexao:
        configuracao = configuracao_alembic()
        configuracao.attributes["connection"] = conexao
        command.upgrade(configuracao, "head")
