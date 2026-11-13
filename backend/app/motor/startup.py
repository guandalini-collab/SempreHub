"""Motor puro de um SaaS: clientes recorrentes, liquidez e capital dos fundadores.

A tributação de serviços é um perfil didático configurável, não um enquadramento
MEI/comercial. DRE usa competência; DFC usa os recebimentos e pagamentos efetivos.
Nenhum argumento é modificado e cada rodada conserva seus próprios snapshots.
"""

from .versionamento import ENGINE_VERSION, inicializar_indicadores
from .financeiros import reconciliar_financeiros
from .indicadores import enps, dedicacao_fundador
from .dependencias import atualizar_marca, atualizar_pd, atualizar_pd_por_produto, atrativo_porter
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
    fracao = parametros.get("_calendario", {}).get("fator_mensal",1)
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
    sairam = min(funcionarios, math.floor(funcionarios * taxa_rotatividade * fracao))
    funcionarios -= sairam
    rh.update(
        moral=moral, qualificacao=qualificacao,
        rotatividade_acumulada=int(rh["rotatividade_acumulada"]) + sairam,
        salario=salario, beneficio=beneficio,
    )
    return {
        "funcionarios": funcionarios, "demitidos": demitidos, "rotatividade": sairam,
        # Encargos simplificados de 45%, independentes do regime comercial antigo.
        "folha": _dinheiro(_decimal(funcionarios) * _decimal(salario) * _decimal(fracao) * Decimal("1.45")),
        "beneficios": _dinheiro(_decimal(funcionarios) * _decimal(beneficio) * _decimal(fracao)),
        "treinamento": treinamento, "rescisoes": rescisao,
    }


def preparar(
    empresa: dict, decisao: dict, parametros: dict, rodada: int,
    multiplicador_custo: float = 1,
) -> dict:
    empresa, decisao, parametros = deepcopy(empresa), deepcopy(decisao), deepcopy(parametros)
    from .calendario import adaptar
    parametros = adaptar(parametros, rodada)
    calendario = parametros.get("_calendario")
    efeitos_eventos = parametros.get("eventos_operacionais") or {}
    fracao = calendario["fator_mensal"] if calendario else 1
    multiplicador_custo *= calendario["sazonalidade"]["insumos"] if calendario else 1
    estado_inicial = _estado_normalizado(empresa.get("estado_simulacao"))
    estado = deepcopy(estado_inicial)
    inicializar_indicadores(estado)
    estado["rh"]["moral"] = _limitar(estado["rh"].get("moral", 80.0) + float(efeitos_eventos.get("moral", 0)))
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
    from .eventos_operacionais import juros_evento_periodo
    juros = _dinheiro(
        _decimal(divida) * _decimal(float(parametros.get("taxa_juros_mensal", 0.025)) + juros_evento_periodo(efeitos_eventos, fracao))
        + _decimal(max(0.0, -caixa_inicial)) * _decimal(parametros.get("taxa_cheque_especial", 0.08)),
    )

    rh = _preparar_rh(empresa, decisao, parametros, estado)
    pro_labore = _dinheiro(max(0, simulacao.get("pro_labore", 0)))
    # Jornada do fundador proporcional à retirada (dedicação parcial do sócio),
    # limitada a uma jornada regular. Ver indicadores.dedicacao_fundador.
    dedicacao = dedicacao_fundador(pro_labore, parametros.get("salario_base", 2000), fracao)
    fundador_ativo = dedicacao > 0
    if 0 < dedicacao < 1:
        alertas.append(
            f"Pró-labore abaixo do salário de referência: o fundador dedica {dedicacao:.0%} "
            "de uma jornada à operação."
        )
    kpis_rh = enps(estado, rh["funcionarios"], estado["rh"].get("salario", parametros.get("salario_base", 2000)), parametros.get("salario_base", 2000), (decisao.get("simulacao") or {}).get("beneficio", 0), (decisao.get("simulacao") or {}).get("horas_extras", 0))
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
    # A nuvem não substitui suporte, vendas e operação. O fundador só amplia
    # a capacidade quando há pró-labore explícito, na proporção da dedicação.
    produtividade_pessoa = max(1, int(configuracao.get("capacidade_atendimento_por_pessoa", 120)))
    capacidade_pessoas = math.floor((rh["funcionarios"] + dedicacao) * produtividade_pessoa * (0.75 + estado["rh"]["moral"] / 400))
    capacidade_atendimento = max(0, min(capacidade_nuvem, capacidade_pessoas) * float(efeitos_eventos.get("capacidade", 1)))
    capacidade = max(0, math.floor(capacidade_atendimento - retidos))
    preco = float(decisao.get("preco", parametros.get("preco_referencia", 100)))
    if preco <= 0:
        raise ValueError("O preço mensal deve ser positivo.")
    from ..custos_campanhas import investimento_efetivo
    verba_midia=investimento_efetivo(decisao)
    # A veiculação mede o alcance da campanha; criação, produção e demais
    # serviços obrigatórios continuam sendo despesas reais da semana. Assim a
    # DRE e o fluxo de caixa registram o orçamento inteiro, sem usar esses
    # serviços duas vezes para ampliar a marca.
    marketing = _dinheiro(max(0, decisao.get("marketing", 0)) * float(efeitos_eventos.get("marketing", 1)))
    digital = min(verba_midia, _dinheiro(max(0, simulacao.get("marketing_digital", 0))))
    canal = _nome(simulacao.get("canal", "DIRETO"))
    fator_canal = 1.1 + (digital / verba_midia * 0.1 if verba_midia else 0) if canal == "DIGITAL" else 1.05 if canal == "DISTRIBUIDOR" else 1.0
    posicionamento = _nome(simulacao.get("posicionamento", "CUSTO"))
    fator_diferenciacao = 1 + estado["rh"]["qualificacao"] / 200 if posicionamento == "DIFERENCIACAO" else 1.0
    marca = atualizar_marca(empresa.get("marca", 0), marketing)
    qualidade, pd_maturado = atualizar_pd(estado, empresa.get("qualidade", 0), decisao.get("pd", 0), rodada, "STARTUP")
    atratividade = atrativo_porter(marca, qualidade, preco, parametros.get("preco_referencia", 100)) * fator_canal * fator_diferenciacao
    plano_comercial = deepcopy(decisao.get("plano_comercial"))
    pd_por_linha = atualizar_pd_por_produto(
        estado, (plano_comercial or {}).get("produtos", []), decisao.get("pd", 0), rodada, "STARTUP"
    )
    produto_publicado = bool((plano_comercial or {}).get("produtos"))
    comercial_ativo = produto_publicado and marketing > 0
    if not produto_publicado:
        alertas.append("Aquisição bloqueada: publique e precifique ao menos um produto no mix comercial.")
    elif marketing <= 0:
        alertas.append("Aquisição bloqueada: marketing da semana está zerado; não há demanda orgânica automática.")
    taxa_royalties = parametros.get("taxa_royalties")
    if taxa_royalties is None:
        taxa_royalties = 0.05 if _nome(empresa.get("classe_dornelas", "")) == "FRANQUIA" else 0.0
    custos = {
        "custos_fixos": _dinheiro(parametros.get("custos_fixos_mensais", 1500)), "pro_labore": pro_labore,
        "marketing": marketing, "pd": _dinheiro(decisao.get("pd", 0)),
        "networking": _dinheiro(decisao.get("networking", 0)),
        "juros": juros, "multas": _dinheiro(parametros.get("multas", 0)),
        "eventos_operacionais": _dinheiro(efeitos_eventos.get("custo", 0)),
        **{chave: rh[chave] for chave in ("folha", "beneficios", "treinamento", "rescisoes")},
    }
    return {
        "calendario": calendario, "fracao":fracao,
        "kpis_rh": kpis_rh, "taxa_cheque_especial": parametros.get("taxa_cheque_especial", 0.08),
        "plano_comercial": plano_comercial,
        "capacidade": capacidade, "atratividade": atratividade,
        "estado_inicial": deepcopy(estado_inicial), "estado": estado,
        "funcionarios_inicio": max(0,int(empresa.get("funcionarios",0))),
        "desligamentos_efetivos": rh["demitidos"]+rh["rotatividade"],
        "funcionarios": rh["funcionarios"], "emprestimo": emprestimo,
        "amortizacao": amortizacao, "amortizacao_obrigatoria": obrigatoria,
        "folha": rh["folha"], "juros": juros, "divida": divida,
        "gastos_previstos": _soma(*custos.values()), "alertas": alertas,
        "caixa_inicial": caixa_inicial, "caixa_disponivel": caixa_disponivel,
        "recebimentos_vencidos": recebimentos_vencidos, "pagamentos_vencidos": pagamentos_vencidos,
        "rodada": rodada, "preco": preco, "custos": custos,
        "configuracao": configuracao, "simulacao": simulacao,
        "efeitos_eventos": deepcopy(efeitos_eventos),
        "capacidade_nuvem": capacidade_nuvem, "capacidade_pessoas": capacidade_pessoas,
        "capacidade_atendimento": capacidade_atendimento, "clientes_iniciais": clientes_iniciais,
        "clientes_perdidos": perdidos, "clientes_retidos": retidos, "churn": churn,
        "aporte": aporte, "valuation": valuation, "diluicao": diluicao,
        "pro_labore": pro_labore, "fundador_ativo": fundador_ativo, "dedicacao_fundador": dedicacao,
        "marca": marca, "qualidade": qualidade, "pd_maturado": pd_maturado,
        "pd_por_linha": pd_por_linha,
        "produto_publicado": produto_publicado, "comercial_ativo": comercial_ativo,
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
    efeitos_eventos = preparo.get("efeitos_eventos") or {}
    demanda_comercial = max(0, math.floor(demanda)) if preparo["comercial_ativo"] else 0
    adquiridos = min(demanda_comercial, preparo["capacidade"])
    clientes = preparo["clientes_retidos"] + adquiridos
    atendidos = min(clientes, preparo["capacidade_atendimento"])
    nao_atendidos = clientes - atendidos
    estado["clientes"] = clientes
    satisfacao = float(estado["satisfacao"])
    if clientes > 0:
        satisfacao = _limitar(
            satisfacao + float(efeitos_eventos.get("satisfacao", 0)) + 2 + estado["rh"]["qualificacao"] / 20
            - max(0, 60 - estado["rh"]["moral"]) / 20
            - nao_atendidos / clientes * 30,
        )
    estado["satisfacao"] = satisfacao
    plano_comercial = preparo.get("plano_comercial") or {}
    itens=plano_comercial.get("produtos", [])
    linhas=[]
    if itens:
        from .portfolio import dividir, atrativos
        base=deepcopy(estado.get("clientes_produtos") or {})
        if not base: base[itens[0]["produto_id"]]=preparo["clientes_iniciais"]
        atuais=[base.get(p["produto_id"],0) for p in itens]
        retencao=dividir(preparo["clientes_retidos"],atuais)
        segmentacao = (plano_comercial.get("analises") or {}).get("segmentacao")
        novos=dividir(adquiridos,atrativos(itens,1,1, segmentacao=segmentacao))
        finais=[r+n for r,n in zip(retencao,novos)]
        ativos=dividir(atendidos,finais)
        estado["clientes_produtos"]={p["produto_id"]:q for p,q in zip(itens,finais)}
        for item,q,f in zip(itens,ativos,finais):
            reducao_custo = preparo.get("pd_por_linha", {}).get(item["produto_id"], {}).get("reducao_custo", 0)
            linhas.append({"produto_id":item["produto_id"],"nome":item["produto_nome"],"preco":item["preco"],"custos_campanha":deepcopy(item.get("custos_campanha")),"vendas":q,"clientes_finais":f,"receita":_dinheiro(q*item["preco"]*preparo["fracao"]),"cmv":_dinheiro(q*item["custo_unitario"]*(1-reducao_custo)*preparo["fracao"]*preparo["multiplicador_custo"])})
        receita=_soma(*(l["receita"] for l in linhas))
        custo_nuvem=_soma(*(l["cmv"] for l in linhas))
    else:
        receita = _dinheiro(_decimal(atendidos) * _decimal(preparo["preco"]) * _decimal(preparo["fracao"]))
        custo_nuvem = _dinheiro(
            _decimal(atendidos) * _decimal(configuracao["custo_nuvem_cliente"])
            * _decimal(preparo["multiplicador_custo"]),
        )
    aliquota = float(configuracao["aliquota_servico"])
    impostos = _dinheiro(_decimal(receita) * _decimal(aliquota))
    royalties = _dinheiro(_decimal(receita) * _decimal(preparo["taxa_royalties"]))
    proporcao_prazo = _limitar(simulacao.get("vendas_prazo", 0), 0, 1)
    perda_recebiveis = _dinheiro(
        _decimal(receita) * _decimal(proporcao_prazo)
        * _decimal(min(.95, max(0.0, float(efeitos_eventos.get("recebiveis_perda", 0)))))
    )
    dre = {
        "receita": receita, "impostos": impostos, "cmv": custo_nuvem,
        **deepcopy(preparo["custos"]), "royalties": royalties,
        "refugos": 0.0, "frete": 0.0, "armazenagem": 0.0, "depreciacao": 0.0,
    }
    dre["eventos_operacionais"] = _soma(dre.get("eventos_operacionais", 0), perda_recebiveis)
    despesas = _soma(*(valor for chave, valor in dre.items() if chave != "receita"))
    dre["lucro_liquido"] = _soma(receita, -despesas)
    receber_novo = _dinheiro(_decimal(receita) * _decimal(proporcao_prazo) - _decimal(perda_recebiveis))
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
    # Perda de recebíveis reduz a conta a receber, mas não é uma nova saída de caixa.
    pagamentos = _soma(preparo["pagamentos_vencidos"], despesas, -perda_recebiveis, -pagar_novo)
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
        "funcionarios_inicio":preparo["funcionarios_inicio"], "desligamentos_efetivos":preparo["desligamentos_efetivos"],
        **preparo["kpis_rh"], "oee": None, "otif": None,
        "produtos": linhas,
        "clientes_iniciais": preparo["clientes_iniciais"], "clientes_perdidos": preparo["clientes_perdidos"],
        "churn": preparo["churn"], "clientes_retidos": preparo["clientes_retidos"],
        "clientes_adquiridos": adquiridos, "clientes_atendidos": atendidos, "clientes_finais": clientes,
        "clientes_nao_atendidos": nao_atendidos, "capacidade_nuvem": preparo["capacidade_nuvem"],
        "capacidade_pessoas": preparo["capacidade_pessoas"], "capacidade_atendimento": preparo["capacidade_atendimento"],
        "produto_publicado": preparo["produto_publicado"], "comercial_ativo": preparo["comercial_ativo"],
        "pro_labore": preparo["pro_labore"], "fundador_ativo": preparo["fundador_ativo"], "pd_maturado": preparo["pd_maturado"],
        "cac": cac, "ltv": ltv, "burn": burn,
        "runway": max(0.0, caixa) / burn if burn > 0 else None,
        "mrr": receita / preparo["fracao"], "aporte": preparo["aporte"], "valuation": preparo["valuation"],
        "participacao_anterior": preparo["participacao_anterior"],
        "participacao_fundadores": estado["participacao_fundadores"], "diluicao": preparo["diluicao"],
        "amortizacao_obrigatoria": preparo["amortizacao_obrigatoria"],
        "eventos_operacionais": deepcopy(efeitos_eventos),
    }
    alertas = deepcopy(preparo["alertas"])
    if nao_atendidos:
        alertas.append(
            f"Nuvem insuficiente: {nao_atendidos} cliente(s) não foi(ram) atendido(s). "
            "A base foi preservada, mas a satisfação caiu e pode elevar o churn na próxima rodada.",
        )
    balanco = _balanco(estado, caixa, preparo["divida"])
    operacao.update(reconciliar_financeiros(balanco, estado, dre, preparo["rodada"], preparo["taxa_cheque_especial"], modo="STARTUP", dias=7 if preparo["calendario"] else 30, horizonte=52 if preparo["calendario"] else 12))
    detalhes = {
        "versao_motor": 1, "engine_version": ENGINE_VERSION, "modo": "STARTUP", "perfil_tributario": "SERVICO_DIDATICO",
        "aliquota_servico": aliquota, "estado_inicial": deepcopy(preparo["estado_inicial"]),
        "estado_final": deepcopy(estado), "operacao": operacao, "dfc": dfc,
        "balanco": balanco,
        "balanco_inicial": deepcopy(preparo["balanco_inicial"]),
    }
    return {
        "estado": estado, "caixa": caixa, "divida": preparo["divida"],
        "funcionarios": preparo["funcionarios"], "capacidade": preparo["capacidade_atendimento"],
        "vendas": atendidos, "dre": dre, "aliquota": aliquota,
        "detalhes": detalhes, "alertas": alertas, "satisfacao": satisfacao,
        "marca": preparo["marca"], "qualidade": preparo["qualidade"],
    }
