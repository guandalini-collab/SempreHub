import os
import sys
import tempfile
from pathlib import Path

import pytest

# Banco isolado para os testes. O PID torna o arquivo exclusivo de cada
# execução (inclusive em execuções simultâneas ou com xdist), evitando que uma
# fixture apague as tabelas enquanto outra ainda está atendendo uma requisição.
# Para testar com PostgreSQL: SEMPREHUB_TESTE_DB=postgresql://... python -m pytest
_BANCO_EXTERNO = os.getenv("SEMPREHUB_TESTE_DB")
_BANCO = Path(tempfile.gettempdir()) / f"semprehub-pytest-{os.getpid()}.db"
os.environ["DATABASE_URL"] = _BANCO_EXTERNO or f"sqlite:///{_BANCO}"
os.environ["SEMPREHUB_CODIGO_DOCENTE"] = "codigo-teste"
# Testes nunca usam serviços de e-mail ou credenciais do .env local.
os.environ["SEMPREHUB_AMBIENTE"] = "desenvolvimento"
os.environ["SEMPREHUB_CALENDARIO_TESTE"] = "1"
os.environ["SMTP_HOST"] = ""
os.environ["RESEND_API_KEY"] = ""
os.environ["EMAIL_REMETENTE"] = ""
os.environ["OPENAI_API_KEY"] = ""
os.environ["SEMPREHUB_OPENAI_API_KEY"] = ""
os.environ["SEMPREHUB_FRONTEND_DIST"] = str(Path(__file__).parent / "sem-frontend")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def limpar_banco_temporario_ao_final():
    """Remove somente o SQLite descartável criado por esta execução."""
    yield
    if _BANCO_EXTERNO:
        return
    engine.dispose()
    for caminho in (_BANCO, Path(f"{_BANCO}-journal"), Path(f"{_BANCO}-wal"), Path(f"{_BANCO}-shm")):
        caminho.unlink(missing_ok=True)


@pytest.fixture()
def cliente():
    Base.metadata.drop_all(bind=engine)
    with engine.begin() as conexao:
        conexao.execute(text("DROP TABLE IF EXISTS alembic_version"))
        conexao.execute(text("DROP TABLE IF EXISTS semprehub_manutencao_backup"))
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)
    with engine.begin() as conexao:
        conexao.execute(text("DROP TABLE IF EXISTS alembic_version"))
        conexao.execute(text("DROP TABLE IF EXISTS semprehub_manutencao_backup"))


def cadastrar(cliente, nome, email, papel="ALUNO", codigo=None):
    resposta = cliente.post(
        "/api/auth/cadastro",
        json={"nome": nome, "email": email, "senha": "senha-segura", "papel": papel, "codigo_docente": codigo},
    )
    assert resposta.status_code == 201, resposta.text
    return {"Authorization": f"Bearer {resposta.json()['token']}"}


@pytest.fixture()
def professor(cliente):
    return cadastrar(cliente, "Prof. Teste", "prof@iffarroupilha.edu.br", "PROFESSOR", "codigo-teste")
