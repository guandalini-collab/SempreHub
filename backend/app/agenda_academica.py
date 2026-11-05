"""Agenda real das aulas, separada do tempo econômico semanal simulado."""

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import HTTPException

from .models import agora

BRASILIA = ZoneInfo("America/Sao_Paulo")
NOMES_DIAS = ("segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo")


def _utc(data: date, horario) -> datetime:
    return datetime.combine(data, horario, BRASILIA).astimezone(timezone.utc).replace(tzinfo=None)


def proximas_aulas(inicio: date, fim: date, dia_semana: int, recessos: set[date]) -> list[date]:
    atual = inicio + timedelta(days=(dia_semana - inicio.weekday()) % 7)
    datas = []
    while atual <= fim:
        if atual not in recessos:
            datas.append(atual)
        atual += timedelta(days=7)
    return datas


def criar_agenda(dados, rodada_inicial: int, total_rodadas: int) -> list[dict]:
    """Cria uma janela de decisão por semana letiva.

    A rodada abre no encontro da semana e encerra no início do encontro seguinte.
    Dessa forma o professor não precisa programar prazos individualmente, e os
    alunos dispõem de uma semana entre os encontros para trabalhar.
    """
    aulas = proximas_aulas(dados.inicio_letivo, dados.fim_letivo, dados.dia_semana, set(dados.recessos))
    aulas = [a for a in aulas if _utc(a, dados.horario_inicio) > agora()]
    quantidade = total_rodadas - rodada_inicial + 1
    if len(aulas) < quantidade:
        raise HTTPException(
            422,
            f"O calendário possui {len(aulas)} aula(s) futura(s) disponível(is), mas são necessárias {quantidade} para programar todas as rodadas.",
        )
    agenda = []
    for deslocamento in range(quantidade):
        abre = _utc(aulas[deslocamento], dados.horario_inicio)
        # Para a última rodada, conserva uma semana inteira de trabalho.
        fecha = _utc(aulas[deslocamento + 1], dados.horario_inicio) if deslocamento + 1 < len(aulas) else abre + timedelta(days=7)
        agenda.append({
            "rodada": rodada_inicial + deslocamento,
            "abre_em": abre.isoformat() + "Z",
            "fecha_em": fecha.isoformat() + "Z",
            "aula": aulas[deslocamento].isoformat(),
        })
    return agenda


def aplicar_proxima_janela(turma) -> None:
    """Aplica a próxima janela já planejada após o fechamento de uma rodada."""
    agenda = (turma.agenda_academica or {}).get("rodadas", [])
    proxima = next((item for item in agenda if item.get("rodada") == turma.rodada_atual), None)
    if not proxima:
        turma.abertura_rodada = None
        turma.prazo_rodada = None
        turma.prazo_numero_rodada = None
        return
    turma.abertura_rodada = datetime.fromisoformat(proxima["abre_em"].replace("Z", "+00:00")).replace(tzinfo=None)
    turma.prazo_rodada = datetime.fromisoformat(proxima["fecha_em"].replace("Z", "+00:00")).replace(tzinfo=None)
    turma.prazo_numero_rodada = turma.rodada_atual


def descricao(dia_semana: int) -> str:
    return NOMES_DIAS[dia_semana]
