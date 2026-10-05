"""Envio de e-mails (recuperação de senha)."""

import logging
import smtplib
import ssl
from email.message import EmailMessage

from . import config

log = logging.getLogger("semprehub")


def smtp_configurado() -> bool:
    return bool(config.SMTP_HOST and config.SMTP_REMETENTE)


def enviar_email(destinatario: str, assunto: str, corpo: str) -> bool:
    """Envia o e-mail e devolve True em caso de sucesso. Sem SMTP configurado, só registra no log."""
    if not smtp_configurado():
        log.warning("SMTP não configurado. E-mail para %s não enviado:\n%s", destinatario, corpo)
        return False

    mensagem = EmailMessage()
    mensagem["From"] = config.SMTP_REMETENTE
    mensagem["To"] = destinatario
    mensagem["Subject"] = assunto
    mensagem.set_content(corpo)

    try:
        if config.SMTP_TLS == "ssl":
            with smtplib.SMTP_SSL(config.SMTP_HOST, config.SMTP_PORTA, context=ssl.create_default_context(), timeout=15) as smtp:
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
