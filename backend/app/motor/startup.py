"""Motor puro de um SaaS: clientes recorrentes, liquidez e capital dos fundadores.

A tributação de serviços é um perfil didático configurável, não um enquadramento
MEI/comercial. DRE usa competência; DFC usa os recebimentos e pagamentos efetivos.
Nenhum argumento é modificado e cada rodada conserva seus próprios snapshots.
"""

from copy import deepcopy
from decimal import Decimal, ROUND_HALF_UP
import math
from typing import Callable


_CENTAVO = Decimal("0.01")
_DEFAULTS = {
    "custo_nuvem_cliente": 10.0,
    "churn_base": 0.05,
    "aliquota_servico": 0.06,
}


def _decimal(valor) -> Decimal:
    resultado = Decimal(str(0 if valor is None else valor))
    if not resultado.is_finite():
        raise ValueError("Valores financeiros devem ser finitos.")
    return resultado


def _dinheiro(valor) -> float:
    return float(_decimal(valor).quantize(_CENTAVO, rounding=ROUND_HALF_UP))


def _soma(*valores) -> float:
    return _dinheiro(sum((_decimal(v) for v in valores), Decimal(0)))


def _limitar(valor, minimo=0.0, maximo=100.0) -> float:
    return min(maximo, max(minimo, float(valor)))


def _nome(valor) -> str:
    return str(getattr(valor, "value", valor))


def _estado_normalizado(estado) -> dict:
    defaults = {
        "versao": 1,
        "estoque_mp": {"quantidade": 0, "valor": 0.0},
        "estoque_pa": {"quantidade": 0, "valor": 0.0},
        "estoque_obsoleto": {"quantidade": 0, "valor": 0.0},
        "maquinas": [], "receber": [], "pagar": [],
        "rh": {"moral": 80.0, "qualificacao": 0.0, "rotatividade_acumulada": 0},
        "satisfacao": 80.0, "clientes": 0,
        "participacao_fundadores": 1.0, "capital_aportado": 0.0,
    }
    resultado = deepcopy(estado or {})
    for chave, valor in defaults.items():
        resultado.setdefault(chave, deepcopy(valor))
    for chave, valor in defaults["rh"].items():
        resultado["rh"].setdefault(chave, valor)
    return resultado


def _liquidar(titulos: list, rodada: int) -> tuple:
    vencidos, pendentes = [], []
    for titulo in titulos:
        (vencidos if titulo["vencimento"] <= rodada else pendentes).append(deepcopy(titulo))
    return _soma(*(titulo["valor"] for titulo in vencidos)), pendentes


def _balanco(estado: dict, caixa: float, divida: float) -> dict:
    receber = _soma(*(t["valor"] for t in estado["receber"]))
    pagar = _soma(*(t["valor"] for t in estado["pagar"]))
    estoques = _soma(*(estado[chave]["valor"] for chave in ("estoque_mp", "estoque_pa", "estoque_obsoleto")))
    imobilizado = _soma(*(maquina["valor_liquido"] for maquina in estado["maquinas"]))
    return {
        "caixa": _dinheiro(caixa), "receber": receber, "pagar": pagar,
        "estoques": estoques, "imobilizado": imobilizado, "divida": _dinheiro(divida),
        "patrimonio": _soma(caixa, receber, estoques, imobilizado, -pagar, -divida),
        "capital_giro": _soma(caixa, receber, estoques, -pagar),
    }


def _preparar_rh(empresa: dict, decisao: dict, parametros: dict, estado: dict) -> dict:
    simulacao = decisao.get("simulacao") or {}
    rh = estado["rh"]
    anteriores = max(0, int(empresa.get("funcionarios", 0)))
    demitidos = min(anteriores, max(0, int(decisao.get("demitir", 0))))
    contratados = max(0, int(decisao.get("contratar", 0)))
    funcionarios = anteriores - demitidos + contratados
    referencia = max(0.0, float(parametros.get("salario_base", 2000.0)))
    salario = simulacao.get("salario")
    salario = _dinheiro(referencia if salario is None else max(0, salario))
    beneficio = _dinheiro(max(0, simulacao.get("beneficio", 0)))
    treinamento = _dinheiro(max(0, simulacao.get("treinamento", 0)))
    salario_anterior = rh.get("salario", referencia)
    rescisao = _dinheiro(_decimal(demitidos) * _decimal(salario_anterior))

    # R$ 100 por funcionário adiciona um ponto de qualificação, até 20/mês.
    qualificacao = _limitar(rh["qualificacao"] + min(20, treinamento / (max(1, funcionarios) * 100)))
    razao_salario = salario / referencia if referencia > 0 else 1.0
    moral = _limitar(
        rh["moral"] + _limitar((razao_salario - 1) * 20, -20, 10)
        + min(5, beneficio / max(1, referencia) * 20)
        + min(5, treinamento / (max(1, funcionarios) * 200))
        - min(15, demitidos * 3),
    )
    taxa_rotatividade = max(0.0, (50 - moral) / 100)
    sairam = min(funcionarios, math.floor(funcionarios * taxa_rotatividade))
    funcionarios -= sairam
    rh.update(
        moral=moral, qualificacao=qualificacao,
        rotatividade_acumulada=int(rh["rotatividade_acumulada"]) + sairam,
        salario=salario, beneficio=beneficio,
    )
    return {
        "funcionarios": funcionarios, "demitidos": demitidos, "rotatividade": sairam,
        # Encargos simplificados de 45%, independentes do regime comercial antigo.
        "folha": _dinheiro(_decimal(funcionarios) * _decimal(salario) * Decimal("1.45")),
        "beneficios": _dinheiro(_decimal(funcionarios) * _decimal(beneficio)),
        "treinamento": treinamento, "rescisoes": rescisao,
    }


def preparar(
    empresa: dict, decisao: dict, parametros: dict, rodada: int,
    multiplicador_custo: float = 1,
) -> dict:
    empresa, decisao, parametros = deepcopy(empresa), deepcopy(decisao), deepcopy(parametros)
    estado_inicial = _estado_normalizado(empresa.get("estado_simulacao"))
    estado = deepcopy(estado_inicial)
    simulacao = decisao.get("simulacao") or {}
    configuracao = {**_DEFAULTS, **(parametros.get("configuracao_simulacao") or {})}
    alertas = [
        "Startup: alíquota de serviços didática de "
        f"{float(configuracao['aliquota_servico']) * 100:g}% sobre a receita; "
        "não representa enquadramento fiscal real.",
    ]
    if any(simulacao.get(campo, 0) for campo in ("producao", "comprar_mp", "comprar_maquinas", "manutencao")):
        alertas.append("Produção, matéria-prima e máquinas não são aplicadas ao modelo SaaS.")
    caixa_inicial = _dinheiro(empresa.get("caixa", 0))
    divida_inicial = _dinheiro(empresa.get("divida", 0))
    recebimentos_vencidos, estado["receber"] = _liquidar(estado["receber"], rodada)
    pagamentos_vencidos, estado["pagar"] = _liquidar(estado["pagar"], rodada)
    caixa_disponivel = _soma(caixa_inicial, recebimentos_vencidos, -pagamentos_vencidos)

    aporte = _dinheiro(max(0, simulacao.get("aporte", 0)))
    valuation = _dinheiro(simulacao.get("valuation", 100000))
    if valuation <= 0:
        raise ValueError("O valuation anterior ao aporte deve ser positivo.")
    participacao_anterior = float(estado["participacao_fundadores"])
    diluicao = aporte / (valuation + aporte) if aporte else 0.0
    estado["participacao_fundadores"] = participacao_anterior * (1 - diluicao)
    estado["capital_aportado"] = _soma(estado["capital_aportado"], aporte)
    caixa_disponivel = _soma(caixa_disponivel, aporte)

    pedido_emprestimo = _dinheiro(max(0, decisao.get("emprestimo", 0)))
    limite = max(0.0, float(parametros.get("limite_credito", 50000)) - divida_inicial)
    emprestimo = 0.0 if caixa_disponivel < 0 else min(pedido_emprestimo, _dinheiro(limite))
    if emprestimo < pedido_emprestimo:
        alertas.append("Empréstimo reduzido ou negado por limite de crédito ou caixa negativo.")
    caixa_disponivel = _soma(caixa_disponivel, emprestimo)
    amortizacao = min(
        _dinheiro(max(0, decisao.get("amortizacao", 0))),
        _soma(divida_inicial, emprestimo), max(0.0, caixa_disponivel),
    )
    if amortizacao < _dinheiro(max(0, decisao.get("amortizacao", 0))):
        alertas.append("Amortização ajustada à dívida e ao caixa disponíveis.")
    obrigatoria = 0.0
    if estado.get("vencimento_divida") is not None and estado["vencimento_divida"] <= rodada:
        obrigatoria = max(0.0, _soma(divida_inicial, -amortizacao))
        estado.pop("vencimento_divida")
        if obrigatoria:
            alertas.append("A dívida herdada da crise venceu e foi quitada; o principal não é despesa na DRE.")
    amortizacao = _soma(amortizacao, obrigatoria)
    divida = _soma(divida_inicial, emprestimo, -amortizacao)
    caixa_disponivel = _soma(caixa_disponivel, -amortizacao)
    juros = _dinheiro(
        _decimal(divida) * _decimal(parametros.get("taxa_juros_mensal", 0.025))
        + _decimal(max(0.0, -caixa_inicial)) * _decimal(parametros.get("taxa_cheque_especial", 0.08)),
    )

    rh = _preparar_rh(empresa, decisao, parametros, estado)
    if rh["rotatividade"]:
        alertas.append(f"Moral baixa: {rh['rotatividade']} funcionário(s) saiu(ram) voluntariamente.")
    clientes_iniciais = max(0, int(estado["clientes"]))
    churn = _limitar(
        float(configuracao["churn_base"]) * (
            1 + (80 - float(estado["satisfacao"])) / 100
            + (80 - estado["rh"]["moral"]) / 200
            - estado["rh"]["qualificacao"] / 400
        ), 0, 0.95,
    )
    perdidos = min(clientes_iniciais, math.floor(clientes_iniciais * churn + 1e-10))
    retidos = clientes_iniciais - perdidos
    estado["clientes"] = retidos
    capacidade_nuvem = max(0, int(simulacao.get("capacidade_nuvem", 300)))
    capacidade = max(0, capacidade_nuvem - retidos)
    preco = float(decisao.get("preco", parametros.get("preco_referencia", 100)))
    if preco <= 0:
        raise ValueError("O preço mensal deve ser positivo.")
    marketing = _dinheiro(max(0, decisao.get("marketing", 0)))
    digital = min(marketing, _dinheiro(max(0, simulacao.get("marketing_digital", 0))))
    canal = _nome(simulacao.get("canal", "DIRETO"))
    fator_canal = 1.1 + (digital / marketing * 0.1 if marketing else 0) if canal == "DIGITAL" else 1.05 if canal == "DISTRIBUIDOR" else 1.0
    posicionamento = _nome(simulacao.get("posicionamento", "CUSTO"))
    fator_diferenciacao = 1 + estado["rh"]["qualificacao"] / 200 if posicionamento == "DIFERENCIACAO" else 1.0
    atratividade = (
        (float(parametros.get("preco_referencia", 100)) / preco) ** 1.4
        * (1 + max(0, float(empresa.get("marca", 0))) + marketing / 10000) ** 0.3
        * (1 + max(0, float(empresa.get("qualidade", 0))) + float(decisao.get("pd", 0)) / 10000) ** 0.25
        * fator_canal * fator_diferenciacao
    )
    taxa_royalties = parametros.get("taxa_royalties")
    if taxa_royalties is None:
        taxa_royalties = 0.05 if _nome(empresa.get("classe_dornelas", "")) == "FRANQUIA" else 0.0
    custos = {
        "custos_fixos": _dinheiro(parametros.get("custos_fixos_mensais", 1500)),
        "marketing": marketing, "pd": _dinheiro(decisao.get("pd", 0)),
        "networking": _dinheiro(decisao.get("networking", 0)),
        "juros": juros, "multas": _dinheiro(parametros.get("multas", 0)),
        **{chave: rh[chave] for chave in ("folha", "beneficios", "treinamento", "rescisoes")},
    }
    return {
        "plano_comercial": deepcopy(decisao.get("plano_comercial")),
        "capacidade": capacidade, "atratividade": atratividade,
        "estado_inicial": deepcopy(estado_inicial), "estado": estado,
        "funcionarios": rh["funcionarios"], "emprestimo": emprestimo,
        "amortizacao": amortizacao, "amortizacao_obrigatoria": obrigatoria,
        "folha": rh["folha"], "juros": juros, "divida": divida,
        "gastos_previstos": _soma(*custos.values()), "alertas": alertas,
        "caixa_inicial": caixa_inicial, "caixa_disponivel": caixa_disponivel,
        "recebimentos_vencidos": recebimentos_vencidos, "pagamentos_vencidos": pagamentos_vencidos,
        "rodada": rodada, "preco": preco, "custos": custos,
        "configuracao": configuracao, "simulacao": simulacao,
        "capacidade_nuvem": capacidade_nuvem, "clientes_iniciais": clientes_iniciais,
        "clientes_perdidos": perdidos, "clientes_retidos": retidos, "churn": churn,
        "aporte": aporte, "valuation": valuation, "diluicao": diluicao,
        "participacao_anterior": participacao_anterior,
        "taxa_royalties": float(taxa_royalties), "multiplicador_custo": float(multiplicador_custo),
        "balanco_inicial": _balanco(estado_inicial, caixa_inicial, divida_inicial),
    }


def apurar(preparo: dict, demanda: float, tributar: Callable) -> dict:
    """Fatura somente clientes atendidos; churn afeta exclusivamente a base inicial.

    `tributar` mantém a interface comum, mas não é usado no SaaS: o perfil de
    serviço didático usa aliquota_servico, sem aplicar regras MEI/comerciais.
    """
    preparo = deepcopy(preparo)
    estado = deepcopy(preparo["estado"])
    simulacao, configuracao = preparo["simulacao"], preparo["configuracao"]
    adquiridos = min(max(0, math.floor(demanda)), preparo["capacidade"])
    clientes = preparo["clientes_retidos"] + adquiridos
    atendidos = min(clientes, preparo["capacidade_nuvem"])
    nao_atendidos = clientes - atendidos
    estado["clientes"] = clientes
    satisfacao = float(estado["satisfacao"])
    if clientes > 0:
        satisfacao = _limitar(
            satisfacao + 2 + estado["rh"]["qualificacao"] / 20
            - max(0, 60 - estado["rh"]["moral"]) / 20
            - nao_atendidos / clientes * 30,
        )
    estado["satisfacao"] = satisfacao
    itens=(preparo.get("plano_comercial") or {}).get("produtos", [])
    linhas=[]
    if itens:
        from .portfolio import dividir, atrativos
        base=deepcopy(estado.get("clientes_produtos") or {})
        if not base: base[itens[0]["produto_id"]]=preparo["clientes_iniciais"]
        atuais=[base.get(p["produto_id"],0) for p in itens]
        retencao=dividir(preparo["clientes_retidos"],atuais)
        novos=dividir(adquiridos,atrativos(itens,1,1))
        finais=[r+n for r,n in zip(retencao,novos)]
        ativos=dividir(atendidos,finais)
        estado["clientes_produtos"]={p["produto_id"]:q for p,q in zip(itens,finais)}
        for item,q,f in zip(itens,ativos,finais):
            linhas.append({"produto_id":item["produto_id"],"nome":item["produto_nome"],"preco":item["preco"],"vendas":q,"clientes_finais":f,"receita":_dinheiro(q*item["preco"]),"cmv":_dinheiro(q*item["custo_unitario"]*preparo["multiplicador_custo"])})
        receita=_soma(*(l["receita"] for l in linhas))
        custo_nuvem=_soma(*(l["cmv"] for l in linhas))
    else:
        receita = _dinheiro(_decimal(atendidos) * _decimal(preparo["preco"]))
        custo_nuvem = _dinheiro(
            _decimal(atendidos) * _decimal(configuracao["custo_nuvem_cliente"])
            * _decimal(preparo["multiplicador_custo"]),
        )
    aliquota = float(configuracao["aliquota_servico"])
    impostos = _dinheiro(_decimal(receita) * _decimal(aliquota))
    royalties = _dinheiro(_decimal(receita) * _decimal(preparo["taxa_royalties"]))
    dre = {
        "receita": receita, "impostos": impostos, "cmv": custo_nuvem,
        **deepcopy(preparo["custos"]), "royalties": royalties,
        "refugos": 0.0, "frete": 0.0, "armazenagem": 0.0, "depreciacao": 0.0,
    }
    despesas = _soma(*(valor for chave, valor in dre.items() if chave != "receita"))
    dre["lucro_liquido"] = _soma(receita, -despesas)
    receber_novo = _dinheiro(_decimal(receita) * _decimal(_limitar(simulacao.get("vendas_prazo", 0), 0, 1)))
    pagar_novo = _dinheiro(_decimal(custo_nuvem) * _decimal(_limitar(simulacao.get("compras_prazo", 0), 0, 1)))
    if receber_novo:
        estado["receber"].append({
            "origem": preparo["rodada"], "vencimento": preparo["rodada"] + int(simulacao.get("prazo_recebimento", 1)),
            "valor": receber_novo,
        })
    if pagar_novo:
        estado["pagar"].append({
            "origem": preparo["rodada"], "vencimento": preparo["rodada"] + int(simulacao.get("prazo_pagamento", 1)),
            "valor": pagar_novo,
        })
    recebimentos = _soma(preparo["recebimentos_vencidos"], receita, -receber_novo)
    pagamentos = _soma(preparo["pagamentos_vencidos"], despesas, -pagar_novo)
    operacional = _soma(recebimentos, -pagamentos)
    financiamento = _soma(preparo["emprestimo"], -preparo["amortizacao"], preparo["aporte"])
    caixa = _soma(preparo["caixa_inicial"], operacional, financiamento)
    dfc = {
        "caixa_inicial": preparo["caixa_inicial"], "recebimentos": recebimentos,
        "pagamentos": pagamentos, "operacional": operacional,
        "investimento": 0.0, "financiamento": financiamento,
        "variacao": _soma(operacional, financiamento), "caixa_final": caixa,
    }
    burn = max(0.0, -operacional)
    margem_cliente = _soma(receita, -custo_nuvem, -impostos, -royalties) / atendidos if atendidos else None
    cac = _dinheiro(preparo["custos"]["marketing"] / adquiridos) if adquiridos else None
    ltv = _dinheiro(margem_cliente / preparo["churn"]) if margem_cliente is not None and preparo["churn"] > 0 else None
    operacao = {
        "produtos": linhas,
        "clientes_iniciais": preparo["clientes_iniciais"], "clientes_perdidos": preparo["clientes_perdidos"],
        "churn": preparo["churn"], "clientes_retidos": preparo["clientes_retidos"],
        "clientes_adquiridos": adquiridos, "clientes_atendidos": atendidos, "clientes_finais": clientes,
        "clientes_nao_atendidos": nao_atendidos, "capacidade_nuvem": preparo["capacidade_nuvem"],
        "cac": cac, "ltv": ltv, "burn": burn,
        "runway": max(0.0, caixa) / burn if burn > 0 else None,
        "mrr": receita, "aporte": preparo["aporte"], "valuation": preparo["valuation"],
        "participacao_anterior": preparo["participacao_anterior"],
        "participacao_fundadores": estado["participacao_fundadores"], "diluicao": preparo["diluicao"],
        "amortizacao_obrigatoria": preparo["amortizacao_obrigatoria"],
    }
    alertas = deepcopy(preparo["alertas"])
    if nao_atendidos:
        alertas.append(
            f"Nuvem insuficiente: {nao_atendidos} cliente(s) não foi(ram) atendido(s). "
            "A base foi preservada, mas a satisfação caiu e pode elevar o churn na próxima rodada.",
        )
    detalhes = {
        "versao_motor": 1, "modo": "STARTUP", "perfil_tributario": "SERVICO_DIDATICO",
        "aliquota_servico": aliquota, "estado_inicial": deepcopy(preparo["estado_inicial"]),
        "estado_final": deepcopy(estado), "operacao": operacao, "dfc": dfc,
        "balanco": _balanco(estado, caixa, preparo["divida"]),
        "balanco_inicial": deepcopy(preparo["balanco_inicial"]),
    }
    return {
        "estado": estado, "caixa": caixa, "divida": preparo["divida"],
        "funcionarios": preparo["funcionarios"], "capacidade": preparo["capacidade_nuvem"],
        "vendas": atendidos, "dre": dre, "aliquota": aliquota,
        "detalhes": detalhes, "alertas": alertas, "satisfacao": satisfacao,
    }
