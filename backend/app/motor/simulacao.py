"""Motor de simulação do SempreHub.

Ao fechar uma rodada, o professor dispara `processar_rodada`, que:
1. aplica o evento macroeconômico da rodada à turma;
2. consolida a decisão de cada empresa (repete a anterior se o aluno não enviou);
3. calcula a atratividade de cada empresa e divide a demanda do mercado;
4. apura o demonstrativo de resultado, tributos, juros e caixa;
5. atualiza atributos comportamentais e a fase da empresa;
6. avança a turma para a rodada seguinte.
"""

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from ..models import (
    ClasseDornelas,
    Decisao,
    Empresa,
    EventoRodada,
    FaseAtual,
    RegimeTributario,
    Resultado,
    StatusTurma,
    TipoEntradaGem,
    Turma,
)
from . import eventos as ev
from .tributos import (
    FATOR_CLT,
    MAX_FUNCIONARIOS_MEI,
    TOLERANCIA_TETO_MEI,
    aliquota_efetiva_simples,
    calcular_imposto,
)

# ---------------------------------------------------------------------------
# Constantes de comportamento do mercado
# ---------------------------------------------------------------------------
ELASTICIDADE_PRECO_ESCOLHA = 2.0  # quanto o preço relativo pesa na escolha entre empresas
ELASTICIDADE_PRECO_MERCADO = 0.8  # quanto o preço médio altera o tamanho total do mercado
PESO_MARCA = 0.30
PESO_QUALIDADE = 0.25
RETENCAO_MARCA = 0.80  # parte da marca que permanece de um mês para o outro
RETENCAO_QUALIDADE = 0.90
REAPROVEITAMENTO_DEMANDA = 0.50  # parte dos clientes não atendidos que compra de outra empresa
PENALIDADE_MEIO_TERMO = 0.70  # Porter: preço baixo com gasto alto em diferenciação
PENALIDADE_PREMIUM_SEM_BASE = 0.80  # Porter: preço alto sem marca nem qualidade
LIMIAR_PREMIUM_MARCA_QUALIDADE = 3.0
ROYALTIES_FRANQUIA = 0.05
QUEDA_PRODUTIVIDADE_AUTOEFICACIA_BAIXA = 0.10
AUTOEFICACIA_BAIXA = 30.0


@dataclass
class _Calculo:
    empresa: Empresa
    decisao: Decisao
    alertas: List[str] = field(default_factory=list)
    caixa_inicio: float = 0.0
    emprestimo: float = 0.0
    amortizacao: float = 0.0
    rescisoes: float = 0.0
    capacidade: float = 0.0
    atratividade: float = 0.0
    demanda: float = 0.0
    vendas: float = 0.0


# ---------------------------------------------------------------------------
# Perfil inicial
# ---------------------------------------------------------------------------
def perfil_inicial(tipo: TipoEntradaGem, classe: ClasseDornelas) -> Dict[str, float]:
    """Atributos de partida conforme a motivação (GEM) e o tipo de empreendedor (Dornelas)."""
    perfil = {
        "autoeficacia": 60.0 if tipo == TipoEntradaGem.OPORTUNIDADE else 45.0,
        "necessidade_realizacao": 60.0 if tipo == TipoEntradaGem.OPORTUNIDADE else 50.0,
        "networking": 20.0,
        "marca": 0.0,
        "qualidade": 0.0,
    }
    if classe == ClasseDornelas.SERIAL:
        perfil["networking"] = 35.0
        perfil["autoeficacia"] += 5
    elif classe == ClasseDornelas.FRANQUIA:
        perfil["marca"] = 4.0  # marca do franqueador; em troca paga royalties
    elif classe == ClasseDornelas.CORPORATIVO:
        perfil["qualidade"] = 3.0
    elif classe == ClasseDornelas.SOCIAL:
        perfil["networking"] = 30.0
        perfil["necessidade_realizacao"] += 5
    return perfil


def _limitar(valor: float, minimo: float = 0.0, maximo: float = 100.0) -> float:
    return max(minimo, min(maximo, valor))


# ---------------------------------------------------------------------------
# Decisões
# ---------------------------------------------------------------------------
def decisao_vigente(db: Session, empresa: Empresa, rodada: int, turma: Turma) -> Decisao:
    """Decisão enviada para a rodada ou, se não houver, repetição da última (sem ações pontuais)."""
    decisao = (
        db.query(Decisao).filter(Decisao.empresa_id == empresa.id, Decisao.rodada == rodada).first()
    )
    if decisao:
        return decisao

    anterior = (
        db.query(Decisao)
        .filter(Decisao.empresa_id == empresa.id, Decisao.rodada < rodada)
        .order_by(Decisao.rodada.desc())
        .first()
    )
    decisao = Decisao(
        empresa_id=empresa.id,
        rodada=rodada,
        preco=anterior.preco if anterior else turma.preco_referencia,
        marketing=anterior.marketing if anterior else 0.0,
        pd=anterior.pd if anterior else 0.0,
        networking=anterior.networking if anterior else 0.0,
        contratar=0,
        demitir=0,
        emprestimo=0.0,
        amortizacao=0.0,
        regime_solicitado=None,
        automatica=1,
    )
    db.add(decisao)
    db.flush()
    return decisao


# ---------------------------------------------------------------------------
# Rodada
# ---------------------------------------------------------------------------
def processar_rodada(
    db: Session, turma: Turma, escolha_evento: str = "SORTEAR", rng: Optional[random.Random] = None
) -> EventoRodada:
    if turma.status != StatusTurma.ABERTA:
        raise ValueError("A turma já foi encerrada.")
    empresas = list(turma.empresas)
    if not empresas:
        raise ValueError("Não há empresas na turma para processar a rodada.")

    rng = rng or random.Random()
    rodada = turma.rodada_atual
    evento = ev.escolher_evento(escolha_evento, turma.probabilidade_evento, rng)

    # 1. Efeitos macroeconômicos
    multiplicador_demanda = 1.0
    if evento.codigo == "GREVE_LOGISTICA":
        turma.cmv_multiplicador = 1 + ev.AUMENTO_CMV_GREVE
        turma.cmv_rodadas_restantes = ev.DURACAO_GREVE_RODADAS
    elif evento.codigo == "ALTA_SELIC":
        turma.taxa_juros_mensal += ev.VARIACAO_SELIC
    elif evento.codigo == "QUEDA_SELIC":
        turma.taxa_juros_mensal = max(ev.TAXA_JUROS_MINIMA, turma.taxa_juros_mensal - ev.VARIACAO_SELIC)
    elif evento.codigo == "DEMANDA_AQUECIDA":
        multiplicador_demanda = 1 + ev.VARIACAO_DEMANDA
    elif evento.codigo == "RETRACAO_ECONOMICA":
        multiplicador_demanda = 1 - ev.VARIACAO_DEMANDA

    multiplicador_cmv = turma.cmv_multiplicador if turma.cmv_rodadas_restantes > 0 else 1.0
    novo_ano = rodada > 1 and (rodada - 1) % 12 == 0

    # 2. Preparação de cada empresa
    calculos: List[_Calculo] = []
    for empresa in empresas:
        decisao = decisao_vigente(db, empresa, rodada, turma)
        c = _Calculo(empresa=empresa, decisao=decisao, caixa_inicio=empresa.caixa)
        if decisao.automatica:
            c.alertas.append("Nenhuma decisão enviada: o sistema repetiu as decisões do mês anterior.")
        if novo_ano:
            empresa.faturamento_ano = 0.0
            empresa.das_mei_pago_ano = 0.0

        _aplicar_mudanca_regime(empresa, decisao, turma, c)
        _aplicar_pessoal(empresa, decisao, turma, c)
        _aplicar_financiamento(empresa, decisao, turma, c)

        empresa.marca = RETENCAO_MARCA * empresa.marca + math.sqrt(max(0.0, decisao.marketing) / 1000)
        empresa.qualidade = RETENCAO_QUALIDADE * empresa.qualidade + 0.5 * math.sqrt(
            max(0.0, decisao.pd) / 1000
        )
        empresa.networking = _limitar(
            empresa.networking - 1 + 2 * math.sqrt(max(0.0, decisao.networking) / 500)
        )

        produtividade = turma.produtividade_por_pessoa
        if empresa.autoeficacia < AUTOEFICACIA_BAIXA:
            produtividade *= 1 - QUEDA_PRODUTIVIDADE_AUTOEFICACIA_BAIXA
            c.alertas.append(
                "Autoeficácia baixa: a insegurança do empreendedor reduziu a produtividade em 10%."
            )
        c.capacidade = (1 + empresa.funcionarios) * produtividade
        c.atratividade = _atratividade(empresa, decisao, turma, c)
        calculos.append(c)

    # 3. Divisão do mercado
    _dividir_mercado(calculos, turma, rodada, multiplicador_demanda)

    # 4. Apuração
    unidades_totais = sum(c.vendas for c in calculos) or 1.0
    for c in calculos:
        _apurar(db, c, turma, rodada, evento, multiplicador_cmv, unidades_totais)

    db.add(
        EventoRodada(
            turma_id=turma.id,
            rodada=rodada,
            codigo=evento.codigo,
            titulo=evento.titulo,
            narrativa=evento.narrativa,
        )
    )

    # 5. Efeitos que duram mais de uma rodada e avanço do calendário
    if turma.cmv_rodadas_restantes > 0:
        turma.cmv_rodadas_restantes -= 1
        if turma.cmv_rodadas_restantes == 0:
            turma.cmv_multiplicador = 1.0
    turma.rodada_atual = rodada + 1
    if turma.rodada_atual > turma.total_rodadas:
        turma.status = StatusTurma.ENCERRADA

    db.commit()
    return db.query(EventoRodada).filter_by(turma_id=turma.id, rodada=rodada).one()


def _aplicar_mudanca_regime(empresa: Empresa, decisao: Decisao, turma: Turma, c: _Calculo) -> None:
    pedido = decisao.regime_solicitado or empresa.regime_pretendido
    empresa.regime_pretendido = None
    if not pedido or pedido == empresa.regime_tributario:
        return
    if pedido == RegimeTributario.MEI:
        funcionarios_previstos = empresa.funcionarios + decisao.contratar - decisao.demitir
        if funcionarios_previstos > MAX_FUNCIONARIOS_MEI:
            c.alertas.append("Mudança para MEI recusada: o MEI pode ter no máximo 1 empregado.")
            return
        if empresa.faturamento_ano > turma.teto_mei_anual:
            c.alertas.append("Mudança para MEI recusada: o faturamento do ano já passou do teto do MEI.")
            return
    empresa.regime_tributario = pedido
    c.alertas.append(f"Regime tributário alterado para {_nome_regime(pedido)} a partir desta rodada.")


def _aplicar_pessoal(empresa: Empresa, decisao: Decisao, turma: Turma, c: _Calculo) -> None:
    demitidos = min(max(0, decisao.demitir), empresa.funcionarios)
    contratados = max(0, decisao.contratar)
    empresa.funcionarios = empresa.funcionarios + contratados - demitidos
    c.rescisoes = demitidos * turma.salario_base
    if demitidos:
        c.alertas.append(f"{demitidos} desligamento(s): verbas rescisórias equivalentes a um salário cada.")
    if (
        empresa.regime_tributario == RegimeTributario.MEI
        and empresa.funcionarios > MAX_FUNCIONARIOS_MEI
    ):
        empresa.regime_tributario = RegimeTributario.SIMPLES_NACIONAL
        c.alertas.append(
            "Desenquadramento do MEI: a empresa passou a ter mais de 1 empregado e agora está no Simples Nacional."
        )


def _aplicar_financiamento(empresa: Empresa, decisao: Decisao, turma: Turma, c: _Calculo) -> None:
    pedido = max(0.0, decisao.emprestimo)
    if pedido > 0:
        if empresa.caixa < 0:
            c.alertas.append("Empréstimo negado: o banco não concede crédito a empresa com caixa negativo.")
        else:
            disponivel = max(0.0, turma.limite_credito - empresa.divida)
            c.emprestimo = min(pedido, disponivel)
            if c.emprestimo < pedido:
                c.alertas.append(
                    f"Empréstimo limitado a {_reais(c.emprestimo)} pelo limite de crédito da turma."
                )
    amortizar = max(0.0, decisao.amortizacao)
    if amortizar > 0:
        c.amortizacao = min(amortizar, empresa.divida, max(0.0, empresa.caixa + c.emprestimo))
        if c.amortizacao < amortizar:
            c.alertas.append(f"Amortização ajustada para {_reais(c.amortizacao)} (dívida ou caixa insuficiente).")
    empresa.divida = empresa.divida + c.emprestimo - c.amortizacao


def _atratividade(empresa: Empresa, decisao: Decisao, turma: Turma, c: _Calculo) -> float:
    preco = max(0.01, decisao.preco)
    referencia = turma.preco_referencia
    valor = (
        (referencia / preco) ** ELASTICIDADE_PRECO_ESCOLHA
        * (1 + empresa.marca) ** PESO_MARCA
        * (1 + empresa.qualidade) ** PESO_QUALIDADE
    )
    limiar_diferenciacao = 0.20 * referencia * turma.demanda_base_por_empresa
    if preco < 0.95 * referencia and (decisao.marketing + decisao.pd) > limiar_diferenciacao:
        valor *= PENALIDADE_MEIO_TERMO
        c.alertas.append(
            "Porter — meio-termo: preço abaixo do mercado com gasto alto em diferenciação confunde o "
            "posicionamento e reduziu sua atratividade em 30%."
        )
    if (
        preco > 1.15 * referencia
        and empresa.marca < LIMIAR_PREMIUM_MARCA_QUALIDADE
        and empresa.qualidade < LIMIAR_PREMIUM_MARCA_QUALIDADE
    ):
        valor *= PENALIDADE_PREMIUM_SEM_BASE
        c.alertas.append(
            "Porter — diferenciação sem base: preço premium sem marca nem qualidade reconhecidas "
            "reduziu sua atratividade em 20%."
        )
    return valor


def _dividir_mercado(
    calculos: List[_Calculo], turma: Turma, rodada: int, multiplicador_demanda: float
) -> None:
    n = len(calculos)
    preco_medio = sum(max(0.01, c.decisao.preco) for c in calculos) / n
    demanda_total = (
        turma.demanda_base_por_empresa
        * n
        * (1 + turma.crescimento_mercado_mensal) ** (rodada - 1)
        * (turma.preco_referencia / preco_medio) ** ELASTICIDADE_PRECO_MERCADO
        * multiplicador_demanda
    )
    soma_atratividade = sum(c.atratividade for c in calculos) or 1.0
    for c in calculos:
        c.demanda = demanda_total * c.atratividade / soma_atratividade
        c.vendas = min(c.demanda, c.capacidade)

    # Clientes não atendidos: parte deles compra de quem ainda tem capacidade ociosa
    nao_atendida = sum(c.demanda - c.vendas for c in calculos) * REAPROVEITAMENTO_DEMANDA
    com_folga = [c for c in calculos if c.capacidade > c.vendas]
    soma_folga = sum(c.atratividade for c in com_folga)
    if nao_atendida > 0 and soma_folga > 0:
        for c in com_folga:
            extra = min(nao_atendida * c.atratividade / soma_folga, c.capacidade - c.vendas)
            c.vendas += extra
            c.demanda += extra

    for c in calculos:
        perdida = c.demanda - c.vendas
        if perdida >= 1:
            c.alertas.append(
                f"Falta de capacidade: {perdida:.0f} unidades deixaram de ser vendidas. "
                "Considere contratar."
            )
        elif c.capacidade > 0 and c.vendas / c.capacidade < 0.6:
            c.alertas.append(
                f"Capacidade ociosa: a equipe usou apenas {c.vendas / c.capacidade:.0%} da capacidade de produção."
            )


def _apurar(
    db: Session,
    c: _Calculo,
    turma: Turma,
    rodada: int,
    evento: ev.Evento,
    multiplicador_cmv: float,
    unidades_totais: float,
) -> None:
    empresa, decisao = c.empresa, c.decisao
    receitas_anteriores = [r.receita for r in empresa.resultados]
    receita_anterior = receitas_anteriores[-1] if receitas_anteriores else None

    receita = c.vendas * decisao.preco
    cmv = c.vendas * turma.custo_unitario * multiplicador_cmv
    if multiplicador_cmv > 1:
        c.alertas.append(f"Greve na logística: CMV {multiplicador_cmv - 1:.0%} mais caro nesta rodada.")
    folha = empresa.funcionarios * turma.salario_base * FATOR_CLT[empresa.regime_tributario]
    royalties = receita * ROYALTIES_FRANQUIA if empresa.classe_dornelas == ClasseDornelas.FRANQUIA else 0.0

    impostos, aliquota = calcular_imposto(
        empresa.regime_tributario,
        receita,
        cmv,
        receitas_anteriores,
        turma.das_mei_mensal,
        turma.aliquota_icms,
    )

    # Teto do MEI (faturamento acumulado no ano-calendário)
    empresa.faturamento_ano += receita
    if empresa.regime_tributario == RegimeTributario.MEI:
        empresa.das_mei_pago_ano += impostos
        teto = turma.teto_mei_anual
        if empresa.faturamento_ano > teto * (1 + TOLERANCIA_TETO_MEI):
            retroativo = max(
                0.0,
                empresa.faturamento_ano * aliquota_efetiva_simples(empresa.faturamento_ano)
                - empresa.das_mei_pago_ano,
            )
            impostos += retroativo
            empresa.regime_tributario = RegimeTributario.SIMPLES_NACIONAL
            c.alertas.append(
                "Desenquadramento retroativo do MEI: o faturamento do ano passou mais de 20% do teto. "
                f"Foram cobrados {_reais(retroativo)} de tributos do Simples sobre todo o faturamento do ano."
            )
        elif empresa.faturamento_ano > teto:
            excesso = (empresa.faturamento_ano - max(teto, empresa.faturamento_ano - receita)) * 0.04
            impostos += excesso
            empresa.regime_pretendido = RegimeTributario.SIMPLES_NACIONAL
            c.alertas.append(
                "Teto do MEI ultrapassado (até 20%): imposto complementar sobre o excesso e migração "
                "para o Simples Nacional na próxima rodada."
            )
        elif empresa.faturamento_ano > 0.8 * teto:
            c.alertas.append(
                f"Atenção: o faturamento do ano já atingiu {empresa.faturamento_ano / teto:.0%} do teto do MEI."
            )

    juros = empresa.divida * turma.taxa_juros_mensal
    if c.caixa_inicio < 0:
        juros_cheque = -c.caixa_inicio * turma.taxa_cheque_especial
        juros += juros_cheque
        c.alertas.append(f"Cheque especial: {_reais(juros_cheque)} de juros sobre o caixa negativo.")

    multas = 0.0
    if evento.codigo == "NOTIFICACAO_FISCAL":
        if empresa.networking < ev.NETWORKING_MINIMO_DEFESA_FISCAL:
            multas += ev.MULTA_NOTIFICACAO_FISCAL
            c.alertas.append("Notificação fiscal: sem apoio contábil da sua rede, a empresa pagou multa.")
        else:
            c.alertas.append("Notificação fiscal: sua rede de contatos ajudou a regularizar a pendência sem multa.")

    lucro = (
        receita
        - impostos
        - cmv
        - folha
        - turma.custos_fixos_mensais
        - decisao.marketing
        - decisao.pd
        - decisao.networking
        - c.rescisoes
        - royalties
        - juros
        - multas
    )
    empresa.caixa = empresa.caixa + c.emprestimo - c.amortizacao + lucro

    # Atributos comportamentais
    if lucro > 0:
        empresa.autoeficacia += 4
    else:
        empresa.autoeficacia -= 6
    if empresa.caixa < 0:
        empresa.autoeficacia -= 10
    empresa.autoeficacia = _limitar(empresa.autoeficacia)
    if receita_anterior is not None:
        empresa.necessidade_realizacao += 3 if receita > receita_anterior else -2
    empresa.necessidade_realizacao = _limitar(empresa.necessidade_realizacao)

    # Fase (Dornelas)
    custos_fixos_totais = turma.custos_fixos_mensais + folha
    if empresa.caixa < custos_fixos_totais:
        empresa.fase_atual = FaseAtual.SOBREVIVENCIA
        c.alertas.append(
            "Estado de sobrevivência: o caixa não cobre nem um mês de custos fixos e folha."
        )
    elif empresa.divida > 0:
        empresa.fase_atual = FaseAtual.CAPTACAO
    elif lucro > 0 and empresa.caixa >= 2 * custos_fixos_totais:
        empresa.fase_atual = FaseAtual.OPERACAO_ESTAVEL
    else:
        empresa.fase_atual = FaseAtual.PLANEJAMENTO

    db.add(
        Resultado(
            empresa_id=empresa.id,
            rodada=rodada,
            preco=decisao.preco,
            demanda=c.demanda,
            capacidade=c.capacidade,
            unidades_vendidas=c.vendas,
            participacao_mercado=c.vendas / unidades_totais,
            receita=receita,
            impostos=impostos,
            cmv=cmv,
            folha=folha,
            custos_fixos=turma.custos_fixos_mensais,
            marketing=decisao.marketing,
            pd=decisao.pd,
            networking_invest=decisao.networking,
            rescisoes=c.rescisoes,
            royalties=royalties,
            juros=juros,
            multas=multas,
            lucro_liquido=lucro,
            caixa_final=empresa.caixa,
            divida_final=empresa.divida,
            regime=empresa.regime_tributario,
            aliquota_efetiva=aliquota,
            funcionarios=empresa.funcionarios,
            marca=empresa.marca,
            qualidade=empresa.qualidade,
            autoeficacia=empresa.autoeficacia,
            networking=empresa.networking,
            necessidade_realizacao=empresa.necessidade_realizacao,
            fase=empresa.fase_atual,
            alertas=c.alertas,
        )
    )


def _nome_regime(regime: RegimeTributario) -> str:
    return {
        RegimeTributario.MEI: "MEI",
        RegimeTributario.SIMPLES_NACIONAL: "Simples Nacional",
        RegimeTributario.LUCRO_PRESUMIDO: "Lucro Presumido",
    }[regime]


def _reais(valor: float) -> str:
    texto = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {texto}"
