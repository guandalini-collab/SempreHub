"""Calendário docente: horários UTC no banco, limite em America/Sao_Paulo."""
import logging
from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo
from fastapi import HTTPException
from .models import Turma, StatusTurma, agora
from .equipes import bloquear_turma
BRASILIA = ZoneInfo("America/Sao_Paulo")

def limite_brasilia(data):
    return datetime.combine(data, time(23, 59, 59), BRASILIA).astimezone(timezone.utc).replace(tzinfo=None)

def vencido(turma, instante=None):
    return bool(turma.prazo_rodada and turma.prazo_numero_rodada == turma.rodada_atual and (instante or agora()) >= turma.prazo_rodada)

def validar_salvamento(turma, rodada=None, instante=None):
    if turma.prazo_rodada and (rodada is None or rodada == turma.prazo_numero_rodada) and (instante or agora()) >= turma.prazo_rodada:
        raise HTTPException(403, "Prazo encerrado às 23:59:59 de Brasília. A rodada é encerrada automaticamente; atualize o painel para consultar o próximo mês.")

def fechar_vencidas():
    from .database import SessionLocal
    from .motor.simulacao import processar_rodada
    from .routers.mercado import preparar_relatorios_automaticos
    with SessionLocal() as db:
        ids = [t.id for t in db.query(Turma).filter(Turma.status == StatusTurma.ABERTA, Turma.prazo_rodada <= agora(), Turma.prazo_numero_rodada == Turma.rodada_atual).all()]
    for turma_id in ids:
        try:
            with SessionLocal() as db:
                turma = bloquear_turma(db, turma_id)
                if not vencido(turma) or turma.status != StatusTurma.ABERTA:
                    continue
                evento = processar_rodada(db, turma, forcar=True)
                professor_id, rodada = turma.professor_id, evento.rodada
            preparar_relatorios_automaticos(turma_id, professor_id, rodada)
        except Exception:
            logging.getLogger(__name__).exception("Fechamento automático pendente da turma %s; será repetido sem duplicar rodadas.", turma_id)
