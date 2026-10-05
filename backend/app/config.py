"""Configuração do SempreHub lida de variáveis de ambiente.

Em desenvolvimento, os valores padrão permitem rodar sem nenhum ajuste.
Em produção, defina ao menos SEMPREHUB_SECRET_KEY, SEMPREHUB_CODIGO_DOCENTE
e DATABASE_URL (veja o arquivo .env.example na raiz do projeto).
"""

import os
from pathlib import Path
from typing import List


def _lista(valor: str) -> List[str]:
    return [item.strip().lower() for item in valor.split(",") if item.strip()]


def _carregar_dotenv() -> None:
    """Lê um arquivo .env simples (CHAVE=valor) sem depender de bibliotecas externas."""
    for caminho in (Path.cwd() / ".env", Path(__file__).resolve().parents[2] / ".env"):
        if not caminho.is_file():
            continue
        for linha in caminho.read_text(encoding="utf-8").splitlines():
            linha = linha.strip()
            if not linha or linha.startswith("#") or "=" not in linha:
                continue
            chave, valor = linha.split("=", 1)
            os.environ.setdefault(chave.strip(), valor.strip().strip('"').strip("'"))
        break


_carregar_dotenv()

AMBIENTE = os.getenv("SEMPREHUB_AMBIENTE", "desenvolvimento")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./semprehub.db")
# Alguns provedores ainda entregam o prefixo antigo "postgres://".
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

SECRET_KEY = os.getenv("SEMPREHUB_SECRET_KEY", "dev-somente-local-troque-em-producao")
TOKEN_VALIDADE_HORAS = int(os.getenv("SEMPREHUB_TOKEN_HORAS", "12"))

# Domínios aceitos no cadastro
DOMINIOS_ALUNO = _lista(
    os.getenv("SEMPREHUB_DOMINIOS_ALUNO", "aluno.iffarroupilha.edu.br,aluno.iffar.edu.br")
)
DOMINIOS_PROFESSOR = _lista(
    os.getenv("SEMPREHUB_DOMINIOS_PROFESSOR", "iffarroupilha.edu.br,iffar.edu.br,gmail.com")
)
# Código exigido para criar conta de professor (impede que alunos se cadastrem como docentes)
CODIGO_DOCENTE = os.getenv("SEMPREHUB_CODIGO_DOCENTE", "docente-iffar")

# Endereço público do sistema, usado no link de recuperação de senha
URL_PUBLICA = os.getenv("SEMPREHUB_URL_PUBLICA", "http://127.0.0.1:8000").rstrip("/")
RECUPERACAO_VALIDADE_MINUTOS = int(os.getenv("SEMPREHUB_RECUPERACAO_MINUTOS", "60"))

# Envio de e-mail (opcional). Sem SMTP_HOST, o link de recuperação é apenas registrado no log
# do servidor e, em desenvolvimento, mostrado na própria tela.
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORTA = int(os.getenv("SMTP_PORTA", "587"))
SMTP_USUARIO = os.getenv("SMTP_USUARIO", "")
SMTP_SENHA = os.getenv("SMTP_SENHA", "")
SMTP_REMETENTE = os.getenv("SMTP_REMETENTE", SMTP_USUARIO)
SMTP_TLS = os.getenv("SMTP_TLS", "starttls").lower()  # starttls | ssl | nenhum

CORS_ORIGINS = [
    origem.strip()
    for origem in os.getenv(
        "SEMPREHUB_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if origem.strip()
]

# Pasta com o frontend compilado (npm run build). Se existir, o FastAPI a serve em "/".
FRONTEND_DIST = Path(
    os.getenv(
        "SEMPREHUB_FRONTEND_DIST",
        str(Path(__file__).resolve().parents[2] / "frontend" / "dist"),
    )
)

if AMBIENTE == "producao":
    if SECRET_KEY.startswith("dev-"):
        raise RuntimeError("Defina SEMPREHUB_SECRET_KEY antes de rodar em produção.")
    if CODIGO_DOCENTE == "docente-iffar":
        raise RuntimeError("Defina SEMPREHUB_CODIGO_DOCENTE antes de rodar em produção.")
