import os
import sys
from pathlib import Path

import pytest

# Banco isolado para os testes
_BANCO = Path(__file__).parent / "teste.db"
# Para testar com PostgreSQL: SEMPREHUB_TESTE_DB=postgresql://... python -m pytest
os.environ["DATABASE_URL"] = os.getenv("SEMPREHUB_TESTE_DB", f"sqlite:///{_BANCO}")
os.environ["SEMPREHUB_CODIGO_DOCENTE"] = "codigo-teste"
# Testes nunca usam serviços de e-mail ou credenciais do .env local.
os.environ["SEMPREHUB_AMBIENTE"] = "desenvolvimento"
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


@pytest.fixture()
def cliente():
    Base.metadata.drop_all(bind=engine)
    with engine.begin() as conexao:
        conexao.execute(text("DROP TABLE IF EXISTS alembic_version"))
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)
    with engine.begin() as conexao:
        conexao.execute(text("DROP TABLE IF EXISTS alembic_version"))


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
