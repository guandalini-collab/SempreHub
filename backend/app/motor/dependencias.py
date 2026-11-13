"""Regras transversais da empresa integrada.

Este módulo concentra as relações que não pertencem a uma tela isolada: marca e
inovação acumulam efeitos entre semanas, e a venda só existe quando a cadeia
comercial e operacional consegue sustentá-la.  Os valores retornados são
determinísticos e ficam fotografados no resultado da rodada.
"""

from __future__ import annotations

import math
from copy import deepcopy


def atualizar_marca(anterior: float, investimento: float, eficiencia: float = 0.001,
                     decaimento: float = 0.15) -> float:
    """Equação de saturação de Kotler/Aaker, em escala interna de marca.

    O decaimento impede que um investimento passado continue atraindo clientes
    indefinidamente. ``log1p`` dá retornos decrescentes ao orçamento corrente.
    """
    return max(0.0, (max(0.0, float(anterior)) * (1 - decaimento)) + math.log1p(
        max(0.0, float(investimento)) * max(0.0, float(eficiencia))
    ))


def atualizar_pd(estado: dict, qualidade_anterior: float, investimento: float,
                 rodada: int, modo: str, eficiencia: float = 0.001) -> tuple[float, list[dict]]:
    """Aplica P&D somente depois do tempo de desenvolvimento do modelo.

    Startup entrega após uma semana; empresa tradicional, após duas. Sem novo
    investimento, a qualidade competitiva perde 10% naquela semana. A fila é
    mantida no estado da empresa para que a rodada não possa antecipar o efeito.
    """
    fila = deepcopy(estado.get("fila_pd") or [])
    atraso = 1 if modo == "STARTUP" else 2
    investimento = max(0.0, float(investimento))
    if investimento:
        fila.append({"origem": rodada, "libera_na": rodada + atraso, "valor": investimento})
    prontos = [item for item in fila if int(item.get("libera_na", rodada + atraso)) <= rodada]
    fila = [item for item in fila if item not in prontos]
    estado["fila_pd"] = fila
    base = max(0.0, float(qualidade_anterior))
    if investimento <= 0:
        base *= 0.90
    ganho = sum(math.log1p(max(0.0, float(item.get("valor", 0))) * eficiencia) for item in prontos)
    return max(0.0, base + ganho), prontos


def atualizar_pd_por_produto(estado: dict, itens: list[dict], investimento: float,
                              rodada: int, modo: str, eficiencia: float = 0.001) -> dict[str, dict]:
    """Mantém a fila de P&D por linha de produto.

    A verba informada na tela é distribuída pelo peso comercial das linhas
    publicadas. O efeito não altera a produção no próprio turno: o atraso é de
    uma semana no digital e de duas semanas no modelo físico. Ao maturar, a
    pesquisa reduz gradualmente custo e refugo da linha correspondente.
    """
    itens = [item for item in itens if item.get("produto_id")]
    if not itens:
        return {}
    atraso = 1 if modo == "STARTUP" else 2
    investimento = max(0.0, float(investimento))
    fila = deepcopy(estado.get("fila_pd_produtos") or [])
    pesos = sum(max(0.0, float(item.get("peso", 1))) for item in itens) or len(itens)
    if investimento:
        for item in itens:
            parcela = investimento * max(0.0, float(item.get("peso", 1))) / pesos
            fila.append({
                "produto_id": item["produto_id"], "origem": rodada,
                "libera_na": rodada + atraso, "valor": parcela,
            })
    prontos = [item for item in fila if int(item.get("libera_na", rodada + atraso)) <= rodada]
    estado["fila_pd_produtos"] = [item for item in fila if item not in prontos]
    niveis = deepcopy(estado.get("pd_por_produto") or {})
    ativos = {item["produto_id"] for item in itens}
    if investimento <= 0:
        for produto_id in ativos:
            niveis[produto_id] = max(0.0, float(niveis.get(produto_id, 0.0)) * 0.90)
    for item in prontos:
        produto_id = item.get("produto_id")
        if produto_id:
            niveis[produto_id] = max(0.0, float(niveis.get(produto_id, 0.0)) + math.log1p(
                max(0.0, float(item.get("valor", 0))) * eficiencia
            ))
    estado["pd_por_produto"] = niveis
    return {
        item["produto_id"]: {
            "nivel": float(niveis.get(item["produto_id"], 0.0)),
            "maturado": [deepcopy(pronto) for pronto in prontos if pronto.get("produto_id") == item["produto_id"]],
            # Tetos impedem que P&D elimine integralmente custo ou defeitos.
            "reducao_custo": min(0.15, float(niveis.get(item["produto_id"], 0.0)) * 0.03),
            "reducao_refugo": min(0.10, float(niveis.get(item["produto_id"], 0.0)) * 0.02),
        }
        for item in itens
    }


def custo_unitario_com_barganha(custo_base: float, insumo_comprado: float) -> tuple[float, float]:
    """Desconto de escala de Porter, limitado a 15% para não criar arbitragem."""
    fator = min(0.15, max(0.0, float(insumo_comprado)) / 10_000 * 0.05)
    return max(0.0, float(custo_base) * (1 - fator)), fator


def atrativo_porter(marca: float, qualidade: float, preco: float, preco_referencia: float) -> float:
    """Atratividade relativa com componentes normalizados na escala 0..100.

    A fórmula de Porter combina três índices comparáveis. O preço em reais é
    convertido para o índice contra o preço de referência antes da ponderação;
    subtrair reais diretamente de índices de marca/qualidade não seria válido.
    """
    referencia = max(0.01, float(preco_referencia))
    indice_marca = min(100.0, 20.0 + max(0.0, float(marca)) * 20.0)
    indice_qualidade = min(100.0, 50.0 + max(0.0, float(qualidade)) * 20.0)
    indice_preco = min(100.0, max(0.0, float(preco)) / referencia * 50.0)
    return max(0.01, indice_marca * 0.35 + indice_qualidade * 0.35 - indice_preco * 0.30)


def radar_coerencia(*, modo: str, decisao: dict, plano_comercial: dict | None,
                    caixa: float, funcionarios: int, capacidade_operacional: float,
                    estoque_disponivel: float = 0.0, custo_frete_unitario: float = 0.0,
                    gastos_previstos: float = 0.0) -> dict:
    """Converte dependências em bloqueios objetivos e avisos pedagógicos."""
    op = decisao.get("simulacao") or {}
    bloqueios: list[str] = []
    avisos: list[str] = []
    marketing = max(0.0, float(decisao.get("marketing", 0)))
    pd = max(0.0, float(decisao.get("pd", 0)))
    producao = max(0, int(op.get("producao", 0)))
    publicado = bool((plano_comercial or {}).get("produtos"))
    pro_labore = max(0.0, float(op.get("pro_labore", 0)))

    if modo == "TRADICIONAL" and producao > 0:
        if funcionarios <= 0 and pro_labore <= 0:
            bloqueios.append("Produção planejada sem equipe ativa ou pró-labore do proprietário.")
        if capacidade_operacional <= 0:
            bloqueios.append("Produção planejada sem capacidade efetiva de pessoas, máquinas ou insumos.")
        if int(op.get("comprar_mp", 0)) <= 0 and estoque_disponivel <= 0:
            bloqueios.append("Produção planejada sem matéria-prima disponível ou compra de insumos.")
    if marketing > 0 and not publicado:
        bloqueios.append("Marketing ativado sem produto publicado e precificado no mix comercial.")
    if modo == "STARTUP" and marketing > 0 and publicado and capacidade_operacional <= 0:
        bloqueios.append("Marketing ativo sem capacidade de atendimento: contrate equipe ou registre o pró-labore do proprietário.")
    if modo == "TRADICIONAL" and marketing > 0 and publicado and float(op.get("orcamento_logistico", 0)) <= 0:
        bloqueios.append("Marketing ativo sem orçamento de logística: não haverá entrega física ao cliente.")
    if publicado and marketing <= 0:
        avisos.append("Marketing zerado: não existe demanda orgânica automática nesta semana.")
    if pd > max(0.0, caixa) * 0.25 and pd > 0:
        avisos.append("P&D supera 25% do caixa disponível e pode comprometer o capital de giro.")
    # A decisão continua possível — uma empresa pode recorrer ao cheque especial
    # —, mas o aluno recebe o aviso antes de assumir o custo financeiro. O motor
    # efetivamente reclassifica o saldo negativo e cobra os juros na rodada
    # seguinte; o radar apenas antecipa a consequência para a decisão.
    if gastos_previstos > max(0.0, caixa):
        deficit = gastos_previstos - max(0.0, caixa)
        avisos.append(
            f"Risco de caixa: os compromissos previstos superam os recursos disponíveis em R$ {deficit:,.2f}. "
            "A diferença tende a virar cheque especial e gerar juros."
        )
    if modo == "TRADICIONAL" and producao > 0 and capacidade_operacional < producao:
        avisos.append("Produção planejada supera a capacidade efetiva; a quantidade será limitada pelo gargalo.")
    if modo == "TRADICIONAL" and marketing > 0 and publicado and custo_frete_unitario > 0:
        capacidade_entrega = float(op.get("orcamento_logistico", 0)) / custo_frete_unitario
        if capacidade_entrega < max(1, producao + estoque_disponivel):
            avisos.append("O orçamento logístico pode limitar o escoamento, mesmo com estoque disponível.")
    return {"bloqueios": bloqueios, "avisos": avisos, "liberado": not bloqueios}
