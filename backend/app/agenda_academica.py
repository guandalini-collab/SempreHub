"""Agenda real das aulas, separada do tempo econômico simulado.

Regra do professor (15/11/2026): cada rodada fica aberta somente durante a aula
(duas aulas de 50 minutos, no máximo 2 horas) e fecha automaticamente no horário
de término. Fora dessa janela o aluno apenas consulta resultados.
"""

from datetime import date, datetime, time, timedelta, timezone
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from fastapi import HTTPException

from .models import agora

BRASILIA = ZoneInfo("America/Sao_Paulo")
NOMES_DIAS = ("segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo")
DURACAO_MAXIMA = timedelta(hours=2)


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


def _instante(valor: str) -> datetime:
    return datetime.fromisoformat(valor.replace("Z", "+00:00")).replace(tzinfo=None)


def _texto(instante: datetime) -> str:
    return instante.isoformat() + "Z"


def criar_agenda(dados, rodada_inicial: int, total_rodadas: int,
                 prorrogacoes: dict | None = None, manter: dict | None = None) -> list[dict]:
    """Cria uma janela de decisão por aula futura: abre no início e fecha no término da aula.

    ``prorrogacoes`` ({"rodada": instante UTC}) estende o fechamento de uma rodada
    escolhida pelo professor (ex.: aula 1 aberta por alguns dias). A rodada
    seguinte abre na primeira aula que começa depois desse fechamento.
    ``manter`` preserva a janela da rodada atual já aberta.
    """
    if getattr(dados, "horario_fim", None) is None:
        raise HTTPException(422, "Informe o horário de término da aula no calendário acadêmico.")
    prorrogacoes = prorrogacoes or {}
    aulas = proximas_aulas(dados.inicio_letivo, dados.fim_letivo, dados.dia_semana, set(dados.recessos))
    aulas = [a for a in aulas if _utc(a, dados.horario_inicio) > agora()]
    agenda, limite, rodada = [], agora(), rodada_inicial
    if manter:
        fecha = _instante(prorrogacoes[str(rodada)]) if str(rodada) in prorrogacoes else _utc(date.fromisoformat(manter["aula"]), dados.horario_fim)
        agenda.append({**manter, "fecha_em": _texto(fecha), "prorrogada": str(rodada) in prorrogacoes})
        limite, rodada = fecha, rodada + 1
    for aula in aulas:
        if rodada > total_rodadas:
            break
        abre = _utc(aula, dados.horario_inicio)
        if abre < limite:
            continue
        fecha = _utc(aula, dados.horario_fim)
        prorrogada = str(rodada) in prorrogacoes
        if prorrogada:
            fecha = _instante(prorrogacoes[str(rodada)])
            if fecha <= abre:
                inicio = abre.replace(tzinfo=timezone.utc).astimezone(BRASILIA).strftime("%d/%m/%Y às %H:%M")
                raise HTTPException(422, f"A extensão da rodada {rodada} termina antes da abertura dela ({inicio}). Escolha um fechamento posterior.")
        agenda.append({"rodada": rodada, "abre_em": _texto(abre), "fecha_em": _texto(fecha), "aula": aula.isoformat(), "prorrogada": prorrogada})
        limite, rodada = fecha, rodada + 1
    if rodada <= total_rodadas:
        faltam = total_rodadas - rodada + 1
        raise HTTPException(
            422,
            f"O calendário não tem aulas suficientes: faltam {faltam} aula(s) para programar todas as rodadas até o fim do período letivo.",
        )
    return agenda


def janela_atual(turma) -> dict | None:
    """Janela da rodada atual que já abriu (não deve ser movida ao reprogramar)."""
    from .equipes import formacao_aberta
    if formacao_aberta(turma):
        return None
    item = next((r for r in (turma.agenda_academica or {}).get("rodadas", []) if r.get("rodada") == turma.rodada_atual), None)
    return item if item and _instante(item["abre_em"]) <= agora() else None


def dados_salvos(agenda: dict) -> SimpleNamespace:
    """Reconstrói a entrada a partir da agenda gravada na turma."""
    return SimpleNamespace(
        inicio_letivo=date.fromisoformat(agenda["inicio_letivo"]),
        fim_letivo=date.fromisoformat(agenda["fim_letivo"]),
        dia_semana=agenda["dia_semana"],
        horario_inicio=time.fromisoformat(agenda["horario_inicio"]),
        horario_fim=time.fromisoformat(agenda["horario_fim"]) if agenda.get("horario_fim") else None,
        recessos=[date.fromisoformat(d) for d in agenda.get("recessos", [])],
    )


def programar(turma, dados) -> None:
    """Grava a agenda e aplica a janela da rodada atual.

    Com a formação de equipes aberta, as datas das rodadas são recalculadas no
    encerramento: a rodada 1 começa na primeira aula depois dele.
    """
    anterior = turma.agenda_academica or {}
    prorrogacoes = {k: v for k, v in (anterior.get("prorrogacoes") or {}).items() if int(k) >= turma.rodada_atual}
    rodadas = criar_agenda(dados, turma.rodada_atual, turma.total_rodadas, prorrogacoes, janela_atual(turma))
    turma.agenda_academica = {
        "inicio_letivo": dados.inicio_letivo.isoformat(),
        "fim_letivo": dados.fim_letivo.isoformat(),
        "dia_semana": dados.dia_semana,
        "dia_descricao": descricao(dados.dia_semana),
        "horario_inicio": dados.horario_inicio.strftime("%H:%M"),
        "horario_fim": dados.horario_fim.strftime("%H:%M"),
        "recessos": sorted(data.isoformat() for data in dados.recessos),
        "rodadas": rodadas,
        "prorrogacoes": prorrogacoes,
    }
    aplicar_proxima_janela(turma)


def aplicar_proxima_janela(turma) -> None:
    """Aplica a próxima janela já planejada após o fechamento de uma rodada."""
    from .equipes import formacao_aberta
    agenda = (turma.agenda_academica or {}).get("rodadas", [])
    proxima = None if formacao_aberta(turma) else next((item for item in agenda if item.get("rodada") == turma.rodada_atual), None)
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
