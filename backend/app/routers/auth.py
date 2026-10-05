import hashlib
import hmac
import logging
import re
import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import config
from .. import serializacao as ser
from ..correio import email_configurado, enviar_email
from ..database import get_db
from ..models import Papel, TokenRecuperacao, Usuario, agora
from ..schemas import CadastroEntrada, EsqueciSenhaEntrada, LoginEntrada, RedefinirSenhaEntrada
from ..seguranca import criar_token, gerar_hash_senha, usuario_atual, verificar_senha

router = APIRouter(prefix="/api/auth", tags=["autenticação"])
log = logging.getLogger("semprehub")

_FORMATO_EMAIL = re.compile(r"^[a-z0-9._%+\-]+@([a-z0-9\-]+\.)+[a-z]{2,}$")


def normalizar_email(email: str) -> str:
    email = email.strip().lower()
    if not _FORMATO_EMAIL.match(email):
        raise HTTPException(422, "E-mail inválido.")
    return email


def _dominio(email: str) -> str:
    return email.rsplit("@", 1)[-1]


def _lista_dominios(dominios) -> str:
    return " ou ".join("@" + d for d in dominios)


@router.post("/cadastro", status_code=201)
def cadastrar(dados: CadastroEntrada, db: Session = Depends(get_db)):
    email = normalizar_email(dados.email)

    if dados.papel == Papel.ALUNO:
        if _dominio(email) not in config.DOMINIOS_ALUNO:
            raise HTTPException(
                422, f"Use seu e-mail institucional de aluno: {_lista_dominios(config.DOMINIOS_ALUNO)}."
            )
    else:
        if _dominio(email) not in config.DOMINIOS_PROFESSOR:
            raise HTTPException(
                422, f"Para professores, use um e-mail {_lista_dominios(config.DOMINIOS_PROFESSOR)}."
            )
        if not dados.codigo_docente or not hmac.compare_digest(
            dados.codigo_docente.strip(), config.CODIGO_DOCENTE
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


# ---------------------------------------------------------------------------
# Recuperação de senha
# ---------------------------------------------------------------------------
def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@router.post("/esqueci-senha")
def esqueci_senha(dados: EsqueciSenhaEntrada, db: Session = Depends(get_db)):
    """Gera um link de redefinição. A resposta é a mesma exista ou não a conta, para não revelar e-mails."""
    resposta = {
        "mensagem": "Se houver uma conta com este e-mail, enviamos um link para criar uma nova senha. "
        "O link vale por "
        f"{config.RECUPERACAO_VALIDADE_MINUTOS} minutos."
    }
    email = dados.email.strip().lower()
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if usuario is None:
        return resposta

    token = secrets.token_urlsafe(32)
    db.add(
        TokenRecuperacao(
            usuario_id=usuario.id,
            token_hash=_hash_token(token),
            expira_em=agora() + timedelta(minutes=config.RECUPERACAO_VALIDADE_MINUTOS),
        )
    )
    db.commit()

    link = f"{config.URL_PUBLICA}/#/redefinir-senha/{token}"
    corpo = (
        f"Olá, {usuario.nome}.\n\n"
        "Recebemos um pedido para redefinir sua senha no SempreHub. Para criar uma nova senha, acesse:\n\n"
        f"{link}\n\n"
        f"O link vale por {config.RECUPERACAO_VALIDADE_MINUTOS} minutos e só pode ser usado uma vez. "
        "Se você não fez este pedido, ignore esta mensagem.\n\n"
        "SempreHub — Simulador de Empreendedorismo"
    )
    enviado = enviar_email(usuario.email, "SempreHub — redefinição de senha", corpo)

    if not enviado and not email_configurado():
        if config.AMBIENTE != "producao":
            # Sem servidor de e-mail em desenvolvimento: o link aparece na tela para testes locais
            resposta["link_desenvolvimento"] = link
        if usuario.papel == Papel.ALUNO:
            resposta["mensagem"] = (
                "O envio de e-mails ainda não está configurado neste servidor. "
                "Peça ao seu professor para redefinir sua senha pelo painel da turma."
            )
        else:
            resposta["mensagem"] = (
                "O envio de e-mails ainda não está configurado neste servidor. "
                "O link de redefinição foi registrado no log do servidor."
            )
    return resposta


@router.post("/redefinir-senha")
def redefinir_senha(dados: RedefinirSenhaEntrada, db: Session = Depends(get_db)):
    registro = db.query(TokenRecuperacao).filter(TokenRecuperacao.token_hash == _hash_token(dados.token)).first()
    if registro is None or registro.usado_em is not None or registro.expira_em < agora():
        raise HTTPException(400, "Link inválido ou expirado. Peça um novo link de recuperação.")
    usuario = db.get(Usuario, registro.usuario_id)
    usuario.senha_hash = gerar_hash_senha(dados.nova_senha)
    registro.usado_em = agora()
    # Invalida outros links pendentes do mesmo usuário
    db.query(TokenRecuperacao).filter(
        TokenRecuperacao.usuario_id == usuario.id, TokenRecuperacao.usado_em.is_(None)
    ).update({"usado_em": agora()})
    db.commit()
    return {"token": criar_token(usuario), "usuario": ser.usuario(usuario)}
