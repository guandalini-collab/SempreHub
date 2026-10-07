"""Motor tradicional didático, puro e versionado.

Estoque é avaliado pelo custo médio; folha é despesa do período. As compras
não são CPV, máquinas não são despesas e títulos não são dinheiro recebido.
As regras de RH e de capacidade são hipóteses didáticas deste perfil.
"""

from .localizacao import estimar_frete
from copy import deepcopy
from decimal import Decimal, ROUND_HALF_UP
import math
from typing import Callable


_CENTAVO = Decimal("0.01")


def _dinheiro(valor: float) -> float:
    return float(Decimal(str(valor)).quantize(_CENTAVO, rounding=ROUND_HALF_UP))


def _soma(valores) -> float:
    return float(sum((Decimal(str(v)) for v in valores), Decimal(0)).quantize(_CENTAVO, rounding=ROUND_HALF_UP))


def _produto(*valores) -> float:
    resultado = Decimal(1)
    for valor in valores:
        resultado *= Decimal(str(valor))
    return _dinheiro(resultado)


def _proporcao(valor, numerador, denominador) -> float:
    return (_dinheiro(Decimal(str(valor)) * Decimal(str(numerador)) / Decimal(str(denominador)))
            if denominador else 0.0)


def _limitar(valor, minimo=0.0, maximo=100.0):
    return max(minimo, min(maximo, valor))


def _estoque(estado, nome):
    estado.setdefault(nome, {"quantidade": 0, "valor": 0.0})
    estado[nome]["quantidade"] = max(0, int(estado[nome]["quantidade"]))
    estado[nome]["valor"] = _dinheiro(estado[nome]["valor"])
    return estado[nome]


def _quitar(titulos, rodada):
    vencidos = [t for t in titulos if t["vencimento"] <= rodada]
    restantes = [t for t in titulos if t["vencimento"] > rodada]
    return restantes, _soma(t["valor"] for t in vencidos)


def preparar(empresa: dict, decisao: dict, parametros: dict, rodada: int,
             multiplicador_custo: float = 1) -> dict:
    """Prepara produção e obrigações certas sem modificar os argumentos."""
    e, d, p = deepcopy(empresa), deepcopy(decisao), deepcopy(parametros)
    s = deepcopy(e.get("estado_simulacao") or {})
    inicial = deepcopy(s)
    cfg = p.get("configuracao_simulacao") or {}
    op = d.get("simulacao") or {}
    alertas = []
    s.setdefault("versao", 1)
    mp, pa = _estoque(s, "estoque_mp"), _estoque(s, "estoque_pa")
    _estoque(s, "estoque_obsoleto")
    s.setdefault("maquinas", [])
    s.setdefault("receber", [])
    s.setdefault("pagar", [])
    rh = s.setdefault("rh", {})
    rh.setdefault("moral", 80.0)
    rh.setdefault("qualificacao", 0.0)
    rh.setdefault("rotatividade_acumulada", 0.0)
    s.setdefault("satisfacao", 80.0)
    s.setdefault("clientes", 0)
    s.setdefault("participacao_fundadores", 1.0)
    s.setdefault("capital_aportado", 0.0)

    caixa_inicio = _dinheiro(e.get("caixa", 0))
    divida_inicio = _dinheiro(e.get("divida", 0))
    s["receber"], recebimentos = _quitar(s["receber"], rodada)
    s["pagar"], pagamentos_vencidos = _quitar(s["pagar"], rodada)
    caixa_obrigacoes = _soma([caixa_inicio, recebimentos, -pagamentos_vencidos])

    emprestimo_pedido = max(0.0, d.get("emprestimo", 0))
    emprestimo = 0.0
    if emprestimo_pedido and caixa_obrigacoes < 0:
        alertas.append("Empréstimo negado: caixa negativo após os títulos vencidos.")
    elif emprestimo_pedido:
        emprestimo = _dinheiro(min(emprestimo_pedido, max(0, p.get("limite_credito", 50000) - divida_inicio)))
        if emprestimo < emprestimo_pedido:
            alertas.append("Empréstimo limitado ao crédito disponível.")
    amortizacao = _dinheiro(min(max(0, d.get("amortizacao", 0)), divida_inicio,
                                max(0, caixa_obrigacoes + emprestimo)))
    if amortizacao < d.get("amortizacao", 0):
        alertas.append("Amortização ajustada à dívida ou ao caixa disponível.")
    obrigatoria = 0.0
    if s.get("vencimento_divida") is not None and rodada >= s["vencimento_divida"]:
        obrigatoria = _dinheiro(max(0, divida_inicio - amortizacao))
        amortizacao = _soma([amortizacao, obrigatoria])
        s.pop("vencimento_divida", None)
        if obrigatoria:
            alertas.append("Vencimento da dívida herdada: principal quitado; eventual falta de caixa usa cheque especial.")
    divida = _soma([divida_inicio, emprestimo, -amortizacao])

    funcionarios_inicio = max(0, int(e.get("funcionarios", 0)))
    # Clima baixo produz saídas no ciclo seguinte, com fração persistida para equipes pequenas.
    taxa_turnover = max(0, (60 - rh["moral"]) / 100) * 0.20
    acumulado = rh["rotatividade_acumulada"] + funcionarios_inicio * taxa_turnover
    turnover = min(funcionarios_inicio, int(math.floor(acumulado + 1e-12)))
    rh["rotatividade_acumulada"] = round(acumulado - turnover, 8)
    demitidos = min(max(0, int(d.get("demitir", 0))), funcionarios_inicio - turnover)
    funcionarios = funcionarios_inicio - turnover - demitidos + max(0, int(d.get("contratar", 0)))
    if turnover:
        alertas.append(f"Clima da rodada anterior: {turnover} empregado(s) saíram voluntariamente.")
    salario_base = p.get("salario_base", 2000)
    salario = salario_base if op.get("salario") is None else op["salario"]
    beneficio = max(0, op.get("beneficio", 0))
    treinamento = _dinheiro(max(0, op.get("treinamento", 0)))
    salario_relativo = salario / salario_base if salario_base > 0 else 1.0
    rh["moral"] = _limitar(rh["moral"] + 8 * (salario_relativo - 1)
                           + (min(6, beneficio / salario_base * 20) if salario_base > 0 else 0)
                           - demitidos * 2)
    rh["qualificacao"] = _limitar(rh["qualificacao"] * 0.95
                                  + 6 * math.sqrt(treinamento / (1000 * max(1, funcionarios))))
    regime = e.get("regime_tributario", "SIMPLES_NACIONAL")
    fatores = {"MEI": 1.45, "SIMPLES_NACIONAL": 1.45, "LUCRO_PRESUMIDO": 1.82}
    folha = _produto(funcionarios, salario, fatores.get(regime, 1.45))
    beneficios = _produto(funcionarios, beneficio)
    rescisoes = _produto(demitidos, salario)
    fator_rh = 0.75 + 0.25 * rh["moral"] / 100 + 0.002 * rh["qualificacao"]
    produtividade = p.get("produtividade_por_pessoa", 120)
    if e.get("autoeficacia", 60) < 30:
        produtividade *= 0.9
        alertas.append("Autoeficácia baixa: produtividade reduzida em 10%.")
    capacidade_trabalho = (1 + funcionarios) * produtividade * fator_rh

    manutencao = _dinheiro(max(0, op.get("manutencao", 0)))
    ativas = [m for m in s["maquinas"] if m["ativacao"] <= rodada]
    necessidade_manutencao = _soma(_produto(m["custo"], 0.01) for m in ativas)
    cobertura = min(1.0, manutencao / necessidade_manutencao) if necessidade_manutencao > 0 else 0.0
    for maquina in ativas:
        maquina["condicao"] = _limitar(maquina["condicao"] + 0.10 * cobertura, 0.1, 1)
    capacidade_maquinas = sum(m["capacidade"] * m["condicao"] for m in ativas)
    capacidade_produtiva = min(capacidade_trabalho, capacidade_maquinas)
    depreciacao = 0.0
    for maquina in ativas:
        parcela = min(maquina["valor_liquido"], _proporcao(maquina["custo"], 1, max(1, maquina["vida_util"])))
        maquina["valor_liquido"] = _soma([maquina["valor_liquido"], -parcela])
        depreciacao = _soma([depreciacao, parcela])
    maquinas_compradas = max(0, int(op.get("comprar_maquinas", 0)))
    preco_maquina = cfg.get("preco_maquina", 12000)
    investimento = _produto(maquinas_compradas, preco_maquina)
    for _ in range(maquinas_compradas):
        s["maquinas"].append({"custo": _dinheiro(preco_maquina), "valor_liquido": _dinheiro(preco_maquina),
                              "capacidade": cfg.get("capacidade_maquina", 240), "condicao": 1.0,
                              "ativacao": rodada + 1, "vida_util": cfg.get("vida_util_maquina", 24)})
    if maquinas_compradas:
        alertas.append("Máquinas compradas ficam disponíveis na próxima rodada.")

    mp_inicial, pa_inicial = deepcopy(mp), deepcopy(pa)
    itens=(d.get("plano_comercial") or {}).get("produtos", [])
    if itens:
        from .portfolio import produzir
        compras, producao_real, refugo, custo_refugo=produzir(s,itens,op,capacidade_produtiva,capacidade_maquinas,multiplicador_custo)
        mp,pa=s["estoque_mp"],s["estoque_pa"]
        producao_pedida=max(0,int(op.get("producao",0)))
        boas=producao_real-refugo
        utilizacao=producao_real/capacidade_maquinas if capacidade_maquinas else 0
        compra_a_prazo=_produto(compras,_limitar(op.get("compras_prazo",0),0,1))
        compra_a_vista=_soma([compras,-compra_a_prazo])
        if compra_a_prazo: s["pagar"].append({"origem":rodada,"vencimento":rodada+op.get("prazo_pagamento",1),"valor":compra_a_prazo})
    else:
        unidades_compra = max(0, int(op.get("comprar_mp", 0)))
        compras = _produto(unidades_compra, p.get("custo_unitario", 40), multiplicador_custo)
        compra_a_prazo = _produto(compras, _limitar(op.get("compras_prazo", 0), 0, 1))
        compra_a_vista = _soma([compras, -compra_a_prazo])
        if compra_a_prazo:
            s["pagar"].append({"origem": rodada, "vencimento": rodada + op.get("prazo_pagamento", 1),
                               "valor": compra_a_prazo})
        mp["quantidade"] += unidades_compra
        mp["valor"] = _soma([mp["valor"], compras])
        producao_pedida = max(0, int(op.get("producao", 0)))
        producao_real = min(producao_pedida, mp["quantidade"], int(math.floor(capacidade_produtiva * 1.30)))
        utilizacao = producao_real / capacidade_maquinas if capacidade_maquinas > 0 else 0.0
        taxa_refugo = min(0.15, 0.4 * max(0, utilizacao - 0.90))
        refugo = min(producao_real, int(math.floor(producao_real * taxa_refugo + 1e-12)))
        boas = producao_real - refugo
        custo_consumido = _proporcao(mp["valor"], producao_real, mp["quantidade"])
        custo_refugo = _proporcao(custo_consumido, refugo, producao_real)
        custo_boas = _soma([custo_consumido, -custo_refugo])
        mp["quantidade"] -= producao_real
        mp["valor"] = _soma([mp["valor"], -custo_consumido])
        pa["quantidade"] += boas
        pa["valor"] = _soma([pa["valor"], custo_boas])
    if producao_real < producao_pedida:
        alertas.append("Produção limitada pelos insumos ou pela capacidade de máquinas e pessoas.")
    if refugo:
        alertas.append(f"Sobrecarga: {refugo} unidade(s) refugadas; insumos consumidos não geram estoque vendável.")
    for maquina in ativas:
        maquina["condicao"] = round(_limitar(maquina["condicao"] - 0.02 * utilizacao * (1 - cobertura), 0.1, 1), 8)
    sobrecarga_trabalho = max(0, producao_real / capacidade_trabalho - 0.90) if capacidade_trabalho else 0
    rh["moral"] = round(_limitar(rh["moral"] - 10 * sobrecarga_trabalho), 8)

    juros_banco = _produto(divida, p.get("taxa_juros_mensal", 0.025))
    juros_cheque = _produto(max(0, -caixa_inicio), p.get("taxa_cheque_especial", 0.08))
    juros = _soma([juros_banco, juros_cheque])
    if juros_cheque:
        alertas.append("Juros de cheque especial sobre o saldo negativo de abertura.")
    custos_fixos = _dinheiro(p.get("custos_fixos_mensais", 1500))
    marketing, pd, networking = (_dinheiro(d.get(k, 0)) for k in ("marketing", "pd", "networking"))
    multas = _dinheiro(p.get("multas", 0))
    despesas_pagas = _soma([folha, beneficios, treinamento, rescisoes, manutencao,
                            custos_fixos, marketing, pd, networking, juros, multas])

    from ..custos_campanhas import investimento_efetivo
    verba_midia=investimento_efetivo(d)
    marca = 0.8 * e.get("marca", 0) + math.sqrt(verba_midia / 1000)
    qualidade = 0.9 * e.get("qualidade", 0) + 0.5 * math.sqrt(pd / 1000)
    canal = getattr(op.get("canal", "DIRETO"), "value", op.get("canal", "DIRETO"))
    digital = min(verba_midia, _dinheiro(max(0, op.get("marketing_digital", 0))))
    fator_canal = {
        "DIRETO": 1.0,
        "DISTRIBUIDOR": 1.10,
        "DIGITAL": 1.05 + (0.10 * digital / verba_midia if verba_midia else 0),
    }.get(canal, 1.0)
    taxa_comissao_canal = {"DIRETO": 0.0, "DISTRIBUIDOR": 0.05, "DIGITAL": 0.03}.get(canal, 0.0)
    # Marketing digital é parte do orçamento já lançado e melhora a marca;
    # não é uma despesa adicional.
    marca += 0.20 * math.sqrt(digital / 1000)
    preco = max(0.01, d.get("preco", 100))
    atratividade = ((p.get("preco_referencia", 100) / preco) ** 2
                    * (1 + marca) ** 0.30 * (1 + qualidade) ** 0.25
                    * (0.5 + 0.5 * s["satisfacao"] / 100) * fator_canal)
    diferenciar = op.get("posicionamento", "CUSTO") == "DIFERENCIACAO"
    desalinhada = ((diferenciar and marca < 3 and qualidade < 3)
                   or (not diferenciar and preco > p.get("preco_referencia", 100)))
    if desalinhada:
        atratividade *= 0.75
        alertas.append("Posicionamento e proposta de valor desalinhados: atratividade reduzida em 25%.")
    taxa_royalties = p.get("taxa_royalties", 0.05 if e.get("classe_dornelas") == "FRANQUIA" else 0)
    return {
        "empresa": e, "decisao": d, "parametros": p, "rodada": rodada,
        "estado_inicial": inicial, "estado": s, "funcionarios": funcionarios,
        "emprestimo": emprestimo, "amortizacao": amortizacao, "amortizacao_obrigatoria": obrigatoria,
        "divida": divida, "caixa_inicio": caixa_inicio, "caixa_disponivel": _soma([caixa_obrigacoes, emprestimo, -amortizacao]),
        "capacidade": pa["quantidade"], "capacidade_produtiva": capacidade_produtiva,
        "capacidade_maquinas": capacidade_maquinas, "utilizacao_maquinas": utilizacao,
        "atratividade": atratividade, "marca": marca, "qualidade": qualidade,
        "folha": folha, "juros": juros, "juros_cheque": juros_cheque,
        "gastos_previstos": _soma([despesas_pagas, depreciacao, custo_refugo]),
        "beneficios": beneficios, "treinamento": treinamento, "rescisoes": rescisoes,
        "manutencao": manutencao, "depreciacao": depreciacao, "custo_refugo": custo_refugo,
        "despesas_pagas": despesas_pagas, "compras_a_vista": compra_a_vista,
        "pagamentos_vencidos": pagamentos_vencidos, "recebimentos_vencidos": recebimentos,
        "investimento": investimento, "taxa_royalties": taxa_royalties,
        "canal": canal, "marketing_digital": digital,
        "taxa_comissao_canal": taxa_comissao_canal,
        "producao_planejada": producao_pedida, "producao_real": producao_real,
        "producao_boa": boas, "refugo": refugo, "turnover": turnover,
        "estoque_mp_inicial": mp_inicial, "estoque_pa_inicial": pa_inicial,
        "alertas": alertas,
    }


def apurar(preparo: dict, demanda: float,
           tributar: Callable[[float, float], tuple]) -> dict:
    """Fecha a rodada sobre uma cópia e reconcilia resultado, caixa e balanço."""
    c = deepcopy(preparo)
    s, d, p = c["estado"], c["decisao"], c["parametros"]
    cfg, op = p.get("configuracao_simulacao") or {}, d.get("simulacao") or {}
    pa = s["estoque_pa"]
    demanda = max(0, math.floor(demanda))
    itens=(d.get("plano_comercial") or {}).get("produtos", [])
    linhas=[]
    if itens:
        from .portfolio import vender, atrativos
        pesos=atrativos(itens,p.get("preco_referencia",100),p.get("custo_referencia_portfolio",40),c["marca"],c["qualidade"])
        linhas=vender(s,itens,demanda,pesos)
        vendas=sum(l["vendas"] for l in linhas)
        cmv=_soma(l["cmv"] for l in linhas);receita=_soma(l["receita"] for l in linhas)
        pa=s["estoque_pa"]
    else:
        vendas = min(demanda, pa["quantidade"])
        cmv = _proporcao(pa["valor"], vendas, pa["quantidade"])
        receita = _produto(vendas, d.get("preco", 100))
        pa["quantidade"] -= vendas
        pa["valor"] = _soma([pa["valor"], -cmv])
    venda_prazo = _produto(receita, _limitar(op.get("vendas_prazo", 0), 0, 1))
    venda_vista = _soma([receita, -venda_prazo])
    if venda_prazo:
        s["receber"].append({"origem": c["rodada"], "vencimento": c["rodada"] + op.get("prazo_recebimento", 1),
                             "valor": venda_prazo})
    impostos, aliquota = tributar(receita, cmv)
    impostos = _dinheiro(impostos)
    modal = op.get("modal", "PADRAO")
    localizacao = estimar_frete(op, cfg)
    custo_frete = localizacao["frete_unitario"]
    frete = _produto(vendas, custo_frete)
    armazenagem = _produto(pa["valor"], cfg.get("custo_armazenagem", 0.01))
    royalties = _produto(receita, c["taxa_royalties"])
    comissao_canal = _soma(l["comissao_canal"] for l in linhas) if linhas else _produto(receita, c["taxa_comissao_canal"])
    dre = {
        "receita": receita, "impostos": impostos, "cmv": cmv, "folha": c["folha"],
        "custos_fixos": _dinheiro(p.get("custos_fixos_mensais", 1500)),
        "marketing": _dinheiro(d.get("marketing", 0)), "pd": _dinheiro(d.get("pd", 0)),
        "networking": _dinheiro(d.get("networking", 0)), "rescisoes": c["rescisoes"],
        "royalties": royalties, "juros": c["juros"], "multas": _dinheiro(p.get("multas", 0)),
        "comissao_canal": comissao_canal,
        "refugos": c["custo_refugo"], "frete": frete, "armazenagem": armazenagem,
        "depreciacao": c["depreciacao"], "beneficios": c["beneficios"],
        "treinamento": c["treinamento"], "manutencao": c["manutencao"],
    }
    dre["lucro_liquido"] = _soma([receita, -_soma(v for k, v in dre.items() if k != "receita")])
    recebimentos = _soma([c["recebimentos_vencidos"], venda_vista])
    pagamentos = _soma([c["pagamentos_vencidos"], c["compras_a_vista"], c["despesas_pagas"],
                        impostos, frete, armazenagem, royalties, comissao_canal])
    operacional = _soma([recebimentos, -pagamentos])
    investimento, financiamento = -c["investimento"], _soma([c["emprestimo"], -c["amortizacao"]])
    variacao = _soma([operacional, investimento, financiamento])
    caixa = _soma([c["caixa_inicio"], variacao])
    ruptura = demanda - vendas
    atraso = {"RAPIDO": 0, "PADRAO": 0.05, "ECONOMICO": 0.20}[modal]
    s["satisfacao"] = round(_limitar(s["satisfacao"] + (2 - 30 * atraso if vendas else 0)
                                    - (20 * ruptura / demanda if demanda else 0)), 8)
    if ruptura:
        c["alertas"].append(f"Ruptura: {ruptura} unidade(s) de demanda sem estoque disponível.")
    if vendas and atraso:
        c["alertas"].append("Atrasos do modal reduzem a satisfação usada na próxima rodada.")
    receber, pagar = (_soma(t["valor"] for t in s[nome]) for nome in ("receber", "pagar"))
    estoques = _soma(s[nome]["valor"] for nome in ("estoque_mp", "estoque_pa", "estoque_obsoleto"))
    imobilizado = _soma(m["valor_liquido"] for m in s["maquinas"])
    patrimonio = _soma([caixa, receber, estoques, imobilizado, -pagar, -c["divida"]])
    balanco = {"caixa": caixa, "receber": receber, "pagar": pagar, "estoques": estoques,
               "imobilizado": imobilizado, "divida": c["divida"], "patrimonio": patrimonio,
               "capital_giro": _soma([receber, estoques, -pagar])}
    dfc = {"caixa_inicial": c["caixa_inicio"], "recebimentos": recebimentos,
           "pagamentos": pagamentos, "operacional": operacional, "investimento": investimento,
           "financiamento": financiamento, "variacao": variacao, "caixa_final": caixa}
    operacao = {k: c[k] for k in ("producao_planejada", "producao_real", "producao_boa", "refugo",
                                "capacidade_produtiva", "capacidade_maquinas", "utilizacao_maquinas",
                                "estoque_mp_inicial", "estoque_pa_inicial", "turnover")}
    operacao.update(localizacao)
    operacao["produtos"]=linhas
    operacao.update(demanda=demanda, vendas=vendas, ruptura=ruptura,
                    estoque_mp_final=deepcopy(s["estoque_mp"]), estoque_pa_final=deepcopy(pa),
                    satisfacao=s["satisfacao"], moral=s["rh"]["moral"], qualificacao=s["rh"]["qualificacao"],
                    amortizacao_obrigatoria=c["amortizacao_obrigatoria"], canal=c["canal"],
                    marketing_digital=c["marketing_digital"], comissao_canal=comissao_canal)
    detalhes = {"versao_motor": 1, "modo": "TRADICIONAL", "configuracao": deepcopy(p),
                "estado_inicial": deepcopy(c["estado_inicial"]), "estado_final": deepcopy(s),
                "operacao": operacao, "dfc": dfc, "balanco": balanco}
    return {"estado": deepcopy(s), "caixa": caixa, "divida": c["divida"], "funcionarios": c["funcionarios"],
            "capacidade": c["capacidade"], "vendas": vendas, "dre": dre, "aliquota": aliquota,
            "detalhes": detalhes, "alertas": c["alertas"], "satisfacao": s["satisfacao"],
            "marca": c["marca"], "qualidade": c["qualidade"]}
