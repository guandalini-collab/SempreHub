"""Envio de e-mails (recuperação de senha).

Dois meios, nesta ordem de preferência:
1. Resend (API HTTPS) — necessário em plataformas que bloqueiam SMTP, como o Railway
   nos planos Free/Hobby. Ative com RESEND_API_KEY e EMAIL_REMETENTE.
2. SMTP (Gmail, Titan etc.) — ative com SMTP_HOST e as demais variáveis SMTP_*.
"""

import json
import logging
import smtplib
import ssl
import urllib.error
import urllib.request
from email.message import EmailMessage

from . import config

log = logging.getLogger("semprehub")

_URL_RESEND = "https://api.resend.com/emails"


def resend_configurado() -> bool:
    return bool(config.RESEND_API_KEY and config.EMAIL_REMETENTE)


def smtp_configurado() -> bool:
    return bool(config.SMTP_HOST and config.SMTP_REMETENTE)


def email_configurado() -> bool:
    return resend_configurado() or smtp_configurado()


def enviar_email(destinatario: str, assunto: str, corpo: str) -> bool:
    """Envia o e-mail e devolve True em caso de sucesso. Sem envio configurado, só registra no log."""
    if resend_configurado():
        return _enviar_resend(destinatario, assunto, corpo)
    if smtp_configurado():
        return _enviar_smtp(destinatario, assunto, corpo)
    log.warning("Envio de e-mail não configurado. E-mail para %s não enviado:\n%s", destinatario, corpo)
    return False


def _enviar_resend(destinatario: str, assunto: str, corpo: str) -> bool:
    dados = json.dumps(
        {"from": config.EMAIL_REMETENTE, "to": [destinatario], "subject": assunto, "text": corpo}
    ).encode("utf-8")
    pedido = urllib.request.Request(
        _URL_RESEND,
        data=dados,
        method="POST",
        headers={
            "Authorization": f"Bearer {config.RESEND_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "SempreHub/2.0",
        },
    )
    try:
        with urllib.request.urlopen(pedido, timeout=15) as resposta:
            return 200 <= resposta.status < 300
    except urllib.error.HTTPError as erro:
        log.error("Resend recusou o e-mail para %s: HTTP %s %s", destinatario, erro.code, erro.read()[:500])
    except (urllib.error.URLError, OSError):
        log.exception("Falha ao enviar e-mail pelo Resend para %s", destinatario)
    return False


def _enviar_smtp(destinatario: str, assunto: str, corpo: str) -> bool:
    mensagem = EmailMessage()
    mensagem["From"] = config.SMTP_REMETENTE
    mensagem["To"] = destinatario
    mensagem["Subject"] = assunto
    mensagem.set_content(corpo)

    try:
        if config.SMTP_TLS == "ssl":
            with smtplib.SMTP_SSL(
                config.SMTP_HOST, config.SMTP_PORTA, context=ssl.create_default_context(), timeout=15
            ) as smtp:
                _autenticar_e_enviar(smtp, mensagem)
        else:
            with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORTA, timeout=15) as smtp:
                if config.SMTP_TLS == "starttls":
                    smtp.starttls(context=ssl.create_default_context())
                _autenticar_e_enviar(smtp, mensagem)
        return True
    except (smtplib.SMTPException, OSError):
        log.exception("Falha ao enviar e-mail para %s", destinatario)
        return False


def _autenticar_e_enviar(smtp: smtplib.SMTP, mensagem: EmailMessage) -> None:
    if config.SMTP_USUARIO:
        smtp.login(config.SMTP_USUARIO, config.SMTP_SENHA)
    smtp.send_message(mensagem)
