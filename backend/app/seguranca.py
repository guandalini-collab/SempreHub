"""Senhas, tokens de acesso e dependências de autenticação."""

import base64
import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .config import SECRET_KEY, TOKEN_VALIDADE_HORAS
from .database import get_db
from .models import Papel, TokenRecuperacao, Usuario, agora

_ITERACOES = 260_000
_ALGORITMO_JWT = "HS256"
_bearer = HTTPBearer(auto_error=False)


def gerar_hash_senha(senha: str) -> str:
    sal = os.urandom(16)
    derivada = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), sal, _ITERACOES)
    return "pbkdf2_sha256${}${}${}".format(
        _ITERACOES,
        base64.b64encode(sal).decode(),
        base64.b64encode(derivada).decode(),
    )


def verificar_senha(senha: str, hash_salvo: str) -> bool:
    try:
        _, iteracoes, sal_b64, derivada_b64 = hash_salvo.split("$")
        sal = base64.b64decode(sal_b64)
        esperada = base64.b64decode(derivada_b64)
    except ValueError:
        return False
    calculada = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), sal, int(iteracoes))
    return hmac.compare_digest(calculada, esperada)


def criar_token(usuario: Usuario) -> str:
    expira = datetime.now(timezone.utc) + timedelta(hours=TOKEN_VALIDADE_HORAS)
    carga = {
        "sub": str(usuario.id), "papel": usuario.papel.value,
        "exp": expira, "ver": usuario.versao_sessao,
    }
    return jwt.encode(carga, SECRET_KEY, algorithm=_ALGORITMO_JWT)


def trocar_senha(db: Session, usuario: Usuario, nova_senha: str) -> None:
    """Troca a senha e revoga sessões e links de recuperação na mesma transação."""
    db.query(Usuario).filter(Usuario.id == usuario.id).update(
        {
            Usuario.senha_hash: gerar_hash_senha(nova_senha),
            Usuario.versao_sessao: Usuario.versao_sessao + 1,
        },
        synchronize_session="fetch",
    )
    db.query(TokenRecuperacao).filter(
        TokenRecuperacao.usuario_id == usuario.id,
        TokenRecuperacao.usado_em.is_(None),
    ).update({TokenRecuperacao.usado_em: agora()}, synchronize_session="fetch")


def usuario_atual(
    credenciais: HTTPAuthorizationCredentials = Depends(_bearer),
    db: Session = Depends(get_db),
) -> Usuario:
    nao_autorizado = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Sessão expirada ou inválida. Entre novamente.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credenciais is None:
        raise nao_autorizado
    try:
        carga = jwt.decode(credenciais.credentials, SECRET_KEY, algorithms=[_ALGORITMO_JWT])
        usuario_id = int(carga["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise nao_autorizado
    usuario = db.get(Usuario, usuario_id)
    if usuario is None:
        raise nao_autorizado
    # Tokens emitidos antes desta mudança pertencem à versão inicial (zero).
    # Continuam válidos até expirar ou até a primeira redefinição de senha.
    versao_token = carga.get("ver", 0)
    if type(versao_token) is not int or versao_token != usuario.versao_sessao:
        raise nao_autorizado
    return usuario


def exigir_professor(usuario: Usuario = Depends(usuario_atual)) -> Usuario:
    if usuario.papel != Papel.PROFESSOR:
        raise HTTPException(status_code=403, detail="Acesso restrito a professores.")
    return usuario


def exigir_aluno(usuario: Usuario = Depends(usuario_atual)) -> Usuario:
    if usuario.papel != Papel.ALUNO:
        raise HTTPException(status_code=403, detail="Acesso restrito a alunos.")
    return usuario
