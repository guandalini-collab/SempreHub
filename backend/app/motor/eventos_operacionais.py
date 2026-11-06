"""Riscos operacionais automáticos, individuais e reproduzíveis.

O módulo não deixa o professor escolher ocorrências. Cada sorteio deriva de uma
semente estável (turma, empresa, rodada e código do evento) registrada no banco.
Assim, o evento continua incerto para quem joga, mas pode ser auditado e
reproduzido depois sem inventar números aleatórios no relatório.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from hashlib import sha256
from typing import Any, Callable, Optional

from sqlalchemy.orm import Session

from ..models import Decisao, Empresa, EventoOperacional, Turma
from .calendario import periodo


VERSAO_EVENTOS_OPERACIONAIS = "1.0.0-auditavel"
LIMITE_EVENTOS_SEMANA = 4
LIMITE_CRITICOS_SEMANA = 1


def _aleatorio_unitario(chave: str) -> tuple[float, str]:
    """Número pseudoaleatório estável, entre 0 e 1, e sua semente pública."""
    semente = sha256(chave.encode("utf-8")).hexdigest()
    return int(semente[:16], 16) / float(0xFFFFFFFFFFFFFFFF), semente


def _inteiro(chave: str, minimo: int, maximo: int) -> int:
    valor, _ = _aleatorio_unitario(chave)
    return minimo + int(valor * (maximo - minimo + 1))


def _porte(empresa: Empresa) -> tuple[str, float]:
    faturamento = max(0.0, empresa.faturamento_ano)
    if faturamento <= 360_000:
        return "Microempresa", 1.0
    if faturamento <= 4_800_000:
        return "Pequena empresa", 3.0
    return "Média empresa", 10.0


def _dados_decisao(decisao: Optional[Decisao]) -> dict[str, Any]:
    return (decisao.simulacao or {}) if decisao else {}


def _epoca_inverno(turma: Turma, rodada: int) -> bool:
    cal = periodo(turma.configuracao_simulacao or {}, rodada)
    if not cal:
        return False
    return date.fromisoformat(cal["inicio"]).month in {6, 7, 8}


def _fatores(empresa: Empresa, turma: Turma, decisao: Optional[Decisao], rodada: int) -> dict[str, Any]:
    op = _dados_decisao(decisao)
    funcionarios = max(0, empresa.funcionarios)
    salario = float(op.get("salario") or turma.salario_base)
    beneficio = max(0.0, float(op.get("beneficio", 0)))
    treinamento = max(0.0, float(op.get("treinamento", 0)))
    manutencao = max(0.0, float(op.get("manutencao", 0)))
    return {
        "funcionarios": funcionarios,
        "salario_abaixo_mercado": funcionarios > 0 and salario < turma.salario_base,
        "salario_acima_mercado": funcionarios > 0 and salario > turma.salario_base,
        "beneficio_por_funcionario": beneficio / funcionarios if funcionarios else 0.0,
        "treinamento_por_funcionario": treinamento / funcionarios if funcionarios else 0.0,
        "manutencao_preventiva": manutencao >= 1_000.0,
        "horas_extras": max(0.0, float(op.get("horas_extras", 0))),
        "modal": op.get("modal", "PADRAO"),
        "vendas_a_prazo": max(0.0, float(op.get("vendas_prazo", 0))),
        "marketing": max(0.0, float(decisao.marketing if decisao else 0)),
        "caixa_negativo": empresa.caixa < 0,
        "tem_maquinas": bool((empresa.estado_simulacao or {}).get("maquinas")),
        "tradicional": turma.modo_jogo == "TRADICIONAL",
        "inverno": _epoca_inverno(turma, rodada),
        "networking_baixo": empresa.networking < 30,
    }


def _probabilidade(base: float, risco: float = 1.0, prevencao: float = 1.0) -> float:
    return max(0.0, min(0.90, base * risco * prevencao))


@dataclass(frozen=True)
class RegraEvento:
    codigo: str
    departamento: str
    titulo: str
    narrativa: str
    base: float
    duracao: tuple[int, int]
    critico: bool
    aplicavel: Callable[[dict[str, Any]], bool]
    chance: Callable[[dict[str, Any]], tuple[float, dict[str, Any]]]
    impacto: Callable[[float], dict[str, Any]]


def _sim(condicao: str, probabilidade: float, fatores: dict[str, Any], reducao: float = 0.0) -> tuple[float, dict[str, Any]]:
    return probabilidade, {"condicao": condicao, "prevencao_reduziu": reducao}


EVENTOS: tuple[RegraEvento, ...] = (
    RegraEvento(
        "RH_ASSEDIO_CONCORRENCIA", "RH", "Assédio da concorrência",
        "Uma empresa concorrente ofereceu condições melhores a parte da equipe.", .04, (4, 8), False,
        lambda f: f["funcionarios"] > 0 and f["salario_abaixo_mercado"],
        lambda f: _sim("salário abaixo da referência", _probabilidade(.04, prevencao=.25 if f["beneficio_por_funcionario"] >= 150 else 1), f, .75 if f["beneficio_por_funcionario"] >= 150 else 0),
        lambda porte: {"moral": -15, "capacidade": .85, "custo": round(2_000 * porte, 2)}),
    RegraEvento(
        "RH_ATESTADOS", "RH", "Ausências médicas concentradas",
        "Ausências temporárias reduziram a disponibilidade da equipe na semana.", .03, (1, 1), False,
        lambda f: f["funcionarios"] > 0,
        lambda f: _sim("equipe ativa; risco maior no inverno", _probabilidade(.03, 1.6 if f["inverno"] else 1, .30 if f["beneficio_por_funcionario"] >= 150 else 1), f, .70 if f["beneficio_por_funcionario"] >= 150 else 0),
        lambda porte: {"capacidade": .70, "moral": -6, "custo": round(3_000 * porte, 2)}),
    RegraEvento(
        "RH_CONDUTA_LIDERANÇA", "RH", "Alerta de conduta da liderança",
        "Surgiram sinais de desgaste na liderança que exigem ação de clima e gestão.", .02, (3, 3), False,
        lambda f: f["funcionarios"] >= 2 and f["horas_extras"] > 0,
        lambda f: _sim("horas extras recorrentes", _probabilidade(.02, 1.5), f),
        lambda porte: {"moral": -35, "custo": round(2_000 * porte, 2)}),
    RegraEvento(
        "PRODUCAO_LOTE_INADEQUADO", "Produção", "Lote de matéria-prima inadequado",
        "Uma parte dos insumos recebidos apresentou falhas de qualidade.", .06, (1, 2), False,
        lambda f: f["tradicional"],
        lambda f: _sim("controle de qualidade preventivo insuficiente", _probabilidade(.06, prevencao=.30 if f["treinamento_por_funcionario"] >= 100 else 1), f, .70 if f["treinamento_por_funcionario"] >= 100 else 0),
        lambda porte: {"qualidade": -.25, "cmv": 1.12, "custo": round(1_500 * porte, 2)}),
    RegraEvento(
        "PRODUCAO_QUEBRA_MAQUINA", "Produção", "Quebra súbita de máquina",
        "Um equipamento exigiu reparo corretivo e reduziu a capacidade da operação.", .05, (1, 1), True,
        lambda f: f["tradicional"] and f["tem_maquinas"],
        lambda f: _sim("manutenção preventiva ausente", _probabilidade(.05, prevencao=.20 if f["manutencao_preventiva"] else 1), f, .80 if f["manutencao_preventiva"] else 0),
        lambda porte: {"capacidade": .45, "custo": round(5_000 * porte, 2)}),
    RegraEvento(
        "PRODUCAO_APAGAO", "Produção", "Queda de energia",
        "Uma interrupção elétrica afetou a produção e expôs perdas de processo.", .04, (1, 1), False,
        lambda f: f["tradicional"] and f["tem_maquinas"],
        lambda f: _sim("operação com máquinas", .04, f),
        lambda porte: {"capacidade": .80, "qualidade": -.08, "custo": round(1_000 * porte, 2)}),
    RegraEvento(
        "LOGÍSTICA_BLOQUEIO", "Logística", "Bloqueio na rota logística",
        "A rota de entrega sofreu restrição e exigiu alternativa mais cara.", .03, (1, 2), False,
        lambda f: f["tradicional"],
        lambda f: _sim("operação logística ativa", _probabilidade(.03, prevencao=.50 if f["modal"] == "RAPIDO" else 1), f, .50 if f["modal"] == "RAPIDO" else 0),
        lambda porte: {"frete": 2.50, "satisfacao": -20, "custo": round(1_000 * porte, 2)}),
    RegraEvento(
        "LOGÍSTICA_ROUBO_CARGA", "Logística", "Perda de carga em trânsito",
        "Uma carga foi perdida durante o transporte e precisará ser reposta.", .02, (1, 2), True,
        lambda f: f["tradicional"],
        lambda f: _sim("carga em trânsito", .02, f),
        lambda porte: {"demanda": .88, "satisfacao": -10, "custo": round(3_000 * porte, 2)}),
    RegraEvento(
        "VENDAS_GUERRA_PREÇOS", "Vendas", "Guerra de preços concorrente",
        "Concorrentes reduziram preços temporariamente e elevaram a pressão comercial.", .05, (4, 4), False,
        lambda f: True,
        lambda f: _sim("mercado competitivo", .05, f),
        lambda porte: {"demanda": .75, "custo": 0.0}),
    RegraEvento(
        "VENDAS_PEDIDO_GRANDE", "Vendas", "Pedido corporativo de grande porte",
        "Surgiu uma oportunidade comercial que amplia receita futura, mas pressiona capital de giro.", .03, (12, 12), False,
        lambda f: True,
        lambda f: _sim("oportunidade comercial", .03, f),
        lambda porte: {"demanda": 1.20, "recebimento_atrasado": True, "custo": round(2_000 * porte, 2)}),
    RegraEvento(
        "MARKETING_CPC_ALTO", "Marketing", "Alta no custo de aquisição",
        "O canal pago ficou mais concorrido e o custo de aquisição aumentou temporariamente.", .04, (2, 2), False,
        lambda f: f["marketing"] > 0,
        lambda f: _sim("campanhas ativas", .04, f),
        lambda porte: {"marketing": 1.40, "demanda": .88, "custo": 0.0}),
    RegraEvento(
        "MARKETING_CRISE_REPUTAÇÃO", "Marketing", "Crise de reputação digital",
        "Uma reclamação ganhou alcance e reduziu temporariamente a conversão.", .03, (1, 4), True,
        lambda f: True,
        lambda f: _sim("exposição de marca", .03, f),
        lambda porte: {"demanda": .75, "satisfacao": -30, "custo": round(5_000 * porte, 2)}),
    RegraEvento(
        "FINANÇAS_INADIMPLÊNCIA", "Finanças", "Inadimplência de cliente",
        "Parte das vendas a prazo não entrou no caixa conforme previsto.", .05, (1, 1), False,
        lambda f: f["vendas_a_prazo"] > 0,
        lambda f: _sim("vendas a prazo", .05, f),
        lambda porte: {"recebiveis_perda": .15, "custo": 0.0}),
    RegraEvento(
        "FINANÇAS_CRÉDITO_CARO", "Finanças", "Crédito mais caro",
        "As condições de crédito pioraram e elevaram o custo financeiro temporariamente.", .04, (8, 12), False,
        lambda f: True,
        lambda f: _sim("mercado de crédito", .04, f),
        lambda porte: {"juros_extra": .02, "custo": 0.0}),
)


def _consolidar(ocorrencias: list[EventoOperacional]) -> dict[str, Any]:
    efeito: dict[str, Any] = {"capacidade": 1.0, "demanda": 1.0, "cmv": 1.0, "frete": 1.0, "marketing": 1.0,
                              "moral": 0.0, "satisfacao": 0.0, "qualidade": 0.0, "custo": 0.0,
                              "juros_extra": 0.0, "recebiveis_perda": 0.0, "recebimento_atrasado": False}
    for ocorrencia in ocorrencias:
        for chave, valor in (ocorrencia.impacto or {}).items():
            if chave in {"capacidade", "demanda", "cmv", "frete", "marketing"}:
                efeito[chave] *= float(valor)
            elif chave in {"moral", "satisfacao", "qualidade", "custo", "juros_extra", "recebiveis_perda"}:
                efeito[chave] += float(valor)
            elif chave == "recebimento_atrasado":
                efeito[chave] = efeito[chave] or bool(valor)
    return efeito


def ativos(db: Session, empresa_id: int, rodada: int) -> list[EventoOperacional]:
    return db.query(EventoOperacional).filter(
        EventoOperacional.empresa_id == empresa_id,
        EventoOperacional.rodada_inicio <= rodada,
        EventoOperacional.rodada_fim >= rodada,
        EventoOperacional.status == "ATIVO",
    ).order_by(EventoOperacional.departamento, EventoOperacional.id).all()


def efeitos_ativos(db: Session, empresa_id: int, rodada: int) -> tuple[dict[str, Any], list[EventoOperacional]]:
    ocorrencias = ativos(db, empresa_id, rodada)
    return _consolidar(ocorrencias), ocorrencias


def gerar_para_rodada(db: Session, turma: Turma, empresas: list[Empresa], rodada: int) -> list[EventoOperacional]:
    """Gera eventos da próxima rodada uma única vez, sem intervenção humana."""
    if turma.modo_jogo == "LEGADO" or rodada > turma.total_rodadas:
        return []
    criados: list[EventoOperacional] = []
    for empresa in empresas:
        ja_gerados = db.query(EventoOperacional.id).filter_by(empresa_id=empresa.id, rodada_inicio=rodada).first()
        if ja_gerados:
            continue
        decisao = max(empresa.decisoes, key=lambda d: d.rodada, default=None)
        fatores = _fatores(empresa, turma, decisao, rodada)
        porte_nome, escala = _porte(empresa)
        candidatos = []
        for regra in EVENTOS:
            if not regra.aplicavel(fatores):
                continue
            probabilidade, fundamentos = regra.chance(fatores)
            chave = f"{VERSAO_EVENTOS_OPERACIONAIS}:{turma.id}:{empresa.id}:{rodada}:{regra.codigo}"
            sorteio, semente = _aleatorio_unitario(chave)
            if sorteio < probabilidade:
                candidatos.append((sorteio / max(probabilidade, .000001), regra, probabilidade, fundamentos, semente))
        candidatos.sort(key=lambda item: item[0])
        escolhidos: list[tuple] = []
        criticos = 0
        for candidato in candidatos:
            regra = candidato[1]
            if len(escolhidos) >= LIMITE_EVENTOS_SEMANA or (regra.critico and criticos >= LIMITE_CRITICOS_SEMANA):
                continue
            escolhidos.append(candidato)
            criticos += int(regra.critico)
        codigos_ativos = {e.codigo for e in ativos(db, empresa.id, rodada)}
        for _, regra, probabilidade, fundamentos, semente in escolhidos:
            # Uma ocorrência ainda em curso não pode ser sorteada outra vez.
            if regra.codigo in codigos_ativos:
                continue
            duracao = _inteiro(f"{semente}:duracao", *regra.duracao)
            impacto = regra.impacto(escala)
            registro = EventoOperacional(
                turma_id=turma.id, empresa_id=empresa.id, rodada_inicio=rodada, rodada_fim=rodada + duracao - 1,
                codigo=regra.codigo, departamento=regra.departamento, titulo=regra.titulo, narrativa=regra.narrativa,
                probabilidade_base=regra.base, probabilidade_aplicada=round(probabilidade, 6), semente=semente,
                fatores={**fundamentos, "porte": porte_nome, "escala": escala, "versao": VERSAO_EVENTOS_OPERACIONAIS},
                impacto=impacto,
            )
            db.add(registro)
            criados.append(registro)
    return criados


def encerrar_vencidos(db: Session, turma_id: int, rodada: int) -> None:
    db.query(EventoOperacional).filter(
        EventoOperacional.turma_id == turma_id,
        EventoOperacional.rodada_fim < rodada,
        EventoOperacional.status == "ATIVO",
    ).update({"status": "CONCLUIDO"}, synchronize_session=False)
