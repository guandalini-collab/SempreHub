"""Calendário mensal automático (padrão desde 16/11/2026).

Cada rodada corresponde a um mês de operação. A rodada 1 é o mês real em que o
jogo começa: a primeira aula de decisão, quando há agenda acadêmica, ou o dia do
encerramento da formação das equipes. O professor pode escolher outro mês antes
de a primeira rodada ser processada.

Turmas que já usam o calendário semanal continuam semanais, e turmas já
iniciadas no modelo mensal sem datas continuam assim: nada muda no meio do jogo.
"""
from datetime import date, datetime
from zoneinfo import ZoneInfo

from .models import Decisao, Empresa

CALENDARIOS = ("SEMANAL", "MENSAL_CALENDARIO")


def hoje_brasilia() -> date:
    return datetime.now(ZoneInfo("America/Sao_Paulo")).date()


def mes_inicial(turma) -> date:
    rodadas = (turma.agenda_academica or {}).get("rodadas") or []
    primeira = next((r for r in rodadas if r.get("rodada") == turma.rodada_atual), None)
    base = date.fromisoformat(primeira["aula"]) if primeira else hoje_brasilia()
    return base.replace(day=1)


def configurar_mes(db, turma, inicio: date) -> None:
    """Grava o calendário mensal com a edição vigente dos fatores do IBGE."""
    from .motor.avancado import config
    from .motor.sazonalidade_x13 import edicao_vigente
    cfg = config(turma)
    cfg.update(
        periodicidade="MENSAL_CALENDARIO", data_inicio_simulada=inicio.replace(day=1).isoformat(),
        rodada_inicio_calendario=turma.rodada_atual, calendario_automatico=True,
        sazonalidade_pmc=cfg.get("sazonalidade_pmc") or edicao_vigente(db),
    )
    turma.configuracao_simulacao = cfg


def iniciar_calendario(db, turma, confirmar: bool = True) -> bool:
    from .equipes import formacao_aberta
    cfg = dict(turma.configuracao_simulacao or {})
    if (
        cfg.get("calendario_automatico") is False or turma.modo_jogo == "LEGADO"
        or cfg.get("periodicidade") in CALENDARIOS or turma.status.value != "ABERTA"
        or formacao_aberta(turma) or turma.rodada_atual != 1
    ):
        return False
    if confirmar:
        turma = db.query(type(turma)).filter_by(id=turma.id).with_for_update().populate_existing().one()
        if (turma.configuracao_simulacao or {}).get("periodicidade") in CALENDARIOS:
            return False
    if db.query(Decisao).join(Empresa).filter(Empresa.turma_id == turma.id, Decisao.rodada == turma.rodada_atual).first():
        return False
    configurar_mes(db, turma, mes_inicial(turma))
    if confirmar:
        db.commit()
    return True


def ajustar_ao_inicio(db, turma, agenda: bool = False) -> None:
    """Agenda nova ou formação encerrada: o mês da rodada 1 acompanha o início real.

    A agenda acadêmica sempre cria o calendário mensal (como antes criava o
    semanal). Não altera um mês escolhido pelo professor nem uma turma que já
    decidiu.
    """
    cfg = turma.configuracao_simulacao or {}
    if cfg.get("periodicidade") != "MENSAL_CALENDARIO":
        if agenda and cfg.get("periodicidade") != "SEMANAL" and turma.modo_jogo != "LEGADO":
            from .equipes import formacao_aberta
            if turma.rodada_atual == 1 and not formacao_aberta(turma) and not db.query(Decisao).join(Empresa).filter(
                Empresa.turma_id == turma.id, Decisao.rodada == turma.rodada_atual,
            ).first():
                configurar_mes(db, turma, mes_inicial(turma))
            return
        iniciar_calendario(db, turma, confirmar=False)
        return
    if (
        cfg.get("calendario_automatico") is False or turma.rodada_atual != 1
        or db.query(Decisao).join(Empresa).filter(Empresa.turma_id == turma.id, Decisao.rodada == turma.rodada_atual).first()
    ):
        return
    configurar_mes(db, turma, mes_inicial(turma))
