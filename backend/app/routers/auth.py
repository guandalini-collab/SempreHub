import hmac
import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import serializacao as ser
from ..config import CODIGO_DOCENTE, DOMINIOS_ALUNO, DOMINIOS_PROFESSOR
from ..database import get_db
from ..models import Papel, Usuario
from ..schemas import CadastroEntrada, LoginEntrada
from ..seguranca import criar_token, gerar_hash_senha, usuario_atual, verificar_senha

router = APIRouter(prefix="/api/auth", tags=["autenticação"])

_FORMATO_EMAIL = re.compile(r"^[a-z0-9._%+\-]+@([a-z0-9\-]+\.)+[a-z]{2,}$")


def _dominio(email: str) -> str:
    return email.rsplit("@", 1)[-1]


@router.post("/cadastro", status_code=201)
def cadastrar(dados: CadastroEntrada, db: Session = Depends(get_db)):
    email = dados.email.strip().lower()
    if not _FORMATO_EMAIL.match(email):
        raise HTTPException(422, "E-mail inválido.")

    if dados.papel == Papel.ALUNO:
        if _dominio(email) not in DOMINIOS_ALUNO:
            raise HTTPException(
                422,
                "Use seu e-mail institucional de aluno: " + " ou ".join("@" + d for d in DOMINIOS_ALUNO) + ".",
            )
    else:
        if _dominio(email) not in DOMINIOS_PROFESSOR:
            raise HTTPException(
                422,
                "Use seu e-mail institucional de servidor: "
                + " ou ".join("@" + d for d in DOMINIOS_PROFESSOR)
                + ".",
            )
        if not dados.codigo_docente or not hmac.compare_digest(
            dados.codigo_docente.strip(), CODIGO_DOCENTE
        ):
            raise HTTPException(403, "Código de cadastro docente inválido.")

    if db.query(Usuario).filter(Usuario.email == email).first():
        raise HTTPException(409, "Já existe uma conta com este e-mail.")

    usuario = Usuario(
        nome=dados.nome.strip(),
        email=email,
        senha_hash=gerar_hash_senha(dados.senha),
        papel=dados.papel,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return {"token": criar_token(usuario), "usuario": ser.usuario(usuario)}


@router.post("/login")
def entrar(dados: LoginEntrada, db: Session = Depends(get_db)):
    email = dados.email.strip().lower()
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if usuario is None or not verificar_senha(dados.senha, usuario.senha_hash):
        raise HTTPException(401, "E-mail ou senha incorretos.")
    return {"token": criar_token(usuario), "usuario": ser.usuario(usuario)}


@router.get("/eu")
def eu(usuario: Usuario = Depends(usuario_atual)):
    return ser.usuario(usuario)
