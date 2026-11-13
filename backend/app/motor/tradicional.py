"""Motor tradicional didático, puro e versionado.

Estoque é avaliado pelo custo médio; folha é despesa do período. As compras
não são CPV, máquinas não são despesas e títulos não são dinheiro recebido.
As regras de RH e de capacidade são hipóteses didáticas deste perfil.
"""

from .versionamento import ENGINE_VERSION, inicializar_indicadores
from .financeiros import reconciliar_financeiros
from .indicadores import oee, otif, enps, capacidades_producao, dedicacao_fundador
from .localizacao import estimar_frete
from .dependencias import atualizar_marca, atualizar_pd, atualizar_pd_por_produto, atrativo_porter, custo_unitario_com_barganha
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


_CARGOS_PRODUCAO = ("operarios", "tecnicos", "especialistas")


def _composicao_equipe(rh, total_anterior):
    """Mantém a composição compatível com empresas criadas antes dos cargos."""
    composicao = rh.setdefault("composicao", {})
    for cargo in _CARGOS_PRODUCAO:
        composicao[cargo] = max(0, int(composicao.get(cargo, 0)))
    diferenca = max(0, int(total_anterior) - sum(composicao.values()))
    composicao["operarios"] += diferenca
    return composicao


def _remover_da_equipe(composicao, quantidade):
    """Desliga primeiro a função menos especializada; decisão legada não informa cargo."""
    restante = max(0, int(quantidade))
    removidos = 0
    for cargo in _CARGOS_PRODUCAO:
        sair = min(composicao[cargo], restante)
        composicao[cargo] -= sair
        restante -= sair
        removidos += sair
        if not restante:
            break
    return removidos


def _produtividade_em_integracao(rh, composicao, admissoes, treinamento):
    """Calcula a capacidade disponível enquanto pessoas recém-contratadas aprendem.

    A folha começa no momento da contratação, mas a capacidade não. Operários
    iniciam com 60% de rendimento por uma semana; técnicos e especialistas,
    cuja curva de aprendizado é maior, iniciam com 50% por duas semanas. Um
    treinamento relevante acelera parcialmente essa integração. A fila fica no
    estado da empresa, portanto o efeito não é visual: reduz de fato o teto de
    produção até que a equipe esteja operacional.
    """
    fila = rh.setdefault("integracao", [])
    duracao = {"operarios": 1, "tecnicos": 2, "especialistas": 2}
    rendimento_inicial = {"operarios": 0.60, "tecnicos": 0.50, "especialistas": 0.50}

    for cargo, quantidade in admissoes.items():
        if quantidade > 0:
            fila.append({"cargo": cargo, "quantidade": int(quantidade),
                         "semanas_restantes": duracao[cargo]})

    # Demissões e desligamentos podem ter atingido pessoas recém-contratadas.
    # Por cargo, nunca se penaliza mais gente do que a que ainda está ativa.
    novatos = {cargo: 0 for cargo in _CARGOS_PRODUCAO}
    for entrada in fila:
        cargo = entrada.get("cargo")
        if cargo in novatos and int(entrada.get("semanas_restantes", 0)) > 0:
            disponivel = max(0, int(composicao.get(cargo, 0)) - novatos[cargo])
            novatos[cargo] += min(disponivel, max(0, int(entrada.get("quantidade", 0))))

    total = sum(max(0, int(composicao.get(cargo, 0))) for cargo in _CARGOS_PRODUCAO)
    por_novato = treinamento / max(1, sum(novatos.values()))
    aceleracao = min(0.30, por_novato / 1000.0)
    equivalentes = 0.0
    for cargo in _CARGOS_PRODUCAO:
        quantidade = max(0, int(composicao.get(cargo, 0)))
        em_integracao = novatos[cargo]
        rendimento = min(0.90, rendimento_inicial[cargo] + aceleracao)
        equivalentes += (quantidade - em_integracao) + em_integracao * rendimento

    # A semana atual usa a rampa; a próxima recebe a equipe um estágio adiante.
    nova_fila = []
    for entrada in fila:
        restante = int(entrada.get("semanas_restantes", 0)) - 1
        if restante > 0:
            nova_fila.append({**entrada, "semanas_restantes": restante})
    rh["integracao"] = nova_fila

    return {
        "fator": equivalentes / total if total else 1.0,
        "novatos": sum(novatos.values()),
        "equivalentes": equivalentes,
        "detalhe": novatos,
    }


def _qualificacao_por_linha(itens, rh, fundador_ativo, taxa_base):
    """Aplica a restrição de competência por linha de produto.

    Operários atendem linhas populares; técnicos (ou formação acumulada) são
    necessários para linhas técnicas e especialistas para linhas especializadas.
    A falta não impede a tentativa de produzir, mas torna o erro observável e
    economicamente severo, em vez de deixar produto complexo nascer perfeito.
    """
    composicao = rh.get("composicao", {})
    qualificacao = float(rh.get("qualificacao", 0))
    disponivel = {
        "operario": int(composicao.get("operarios", 0)) + int(fundador_ativo),
        "tecnico": int(composicao.get("tecnicos", 0)) + int(composicao.get("especialistas", 0)),
        "especialista": int(composicao.get("especialistas", 0)),
    }
    limiares = {"operario": 0, "tecnico": 35, "especialista": 65}
    taxas, diagnosticos = {}, {}
    for item in itens:
        exigencia = item.get("qualificacao_minima") or "operario"
        tem_cargo = disponivel.get(exigencia, 0) > 0
        formado = qualificacao >= limiares.get(exigencia, 0)
        compativel = tem_cargo or formado
        taxas[item["produto_id"]] = float(taxa_base) if compativel else max(float(taxa_base), 0.80)
        diagnosticos[item["produto_id"]] = {
            "compativel": compativel,
            "exigencia": exigencia,
            "motivo": None if compativel else f"Linha exige {exigencia}; equipe sem competência compatível.",
        }
    return taxas, diagnosticos


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
    from .calendario import adaptar
    p = adaptar(p, rodada)
    fracao = p.get("_calendario", {}).get("fator_mensal", 1)
    sazonal = p.get("_calendario", {}).get("sazonalidade", {})
    multiplicador_custo *= sazonal.get("insumos", 1)
    s = deepcopy(e.get("estado_simulacao") or {})
    inicial = deepcopy(s)
    inicializar_indicadores(s)
    cfg = p.get("configuracao_simulacao") or {}
    op = d.get("simulacao") or {}
    efeitos_eventos = p.get("eventos_operacionais") or {}
    alertas = []
    s.setdefault("versao", 1)
    mp, pa = _estoque(s, "estoque_mp"), _estoque(s, "estoque_pa")
    _estoque(s, "estoque_obsoleto")
    s.setdefault("maquinas", [])
    # Linhas de produto possuem investimento próprio e permanecem disponíveis
    # após a homologação. Não se confundem com máquinas: representam ferramental,
    # aprovação técnica e preparação comercial específica da linha.
    s.setdefault("ativos_linhas", [])
    s.setdefault("receber", [])
    s.setdefault("pagar", [])
    rh = s.setdefault("rh", {})
    rh.setdefault("moral", 80.0)
    rh.setdefault("qualificacao", 0.0)
    rh.setdefault("rotatividade_acumulada", 0.0)
    rh["moral"] = _limitar(rh["moral"] + float(efeitos_eventos.get("moral", 0)))
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
    composicao = _composicao_equipe(rh, funcionarios_inicio)
    funcionarios_inicio = sum(composicao.values())
    # Clima baixo produz saídas no ciclo seguinte, com fração persistida para equipes pequenas.
    taxa_turnover = max(0, (60 - rh["moral"]) / 100) * 0.20
    acumulado = rh["rotatividade_acumulada"] + funcionarios_inicio * taxa_turnover * fracao
    turnover = min(funcionarios_inicio, int(math.floor(acumulado + 1e-12)))
    rh["rotatividade_acumulada"] = round(acumulado - turnover, 8)
    _remover_da_equipe(composicao, turnover)
    demitidos = _remover_da_equipe(composicao, min(max(0, int(d.get("demitir", 0))), funcionarios_inicio - turnover))
    admissoes_operarios = max(0, int(d.get("contratar", 0)))
    admissoes_tecnicos = max(0, int(d.get("contratar_tecnicos") or 0))
    admissoes_especialistas = max(0, int(d.get("contratar_especialistas") or 0))
    composicao["operarios"] += admissoes_operarios
    composicao["tecnicos"] += admissoes_tecnicos
    composicao["especialistas"] += admissoes_especialistas
    funcionarios = sum(composicao.values())
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
    rh["qualificacao"] = _limitar(rh["qualificacao"] * (0.95 ** fracao)
                                  + 6 * math.sqrt(treinamento / (1000 * max(1, funcionarios))))
    integracao = _produtividade_em_integracao(
        rh,
        composicao,
        {
            "operarios": admissoes_operarios,
            "tecnicos": admissoes_tecnicos,
            "especialistas": admissoes_especialistas,
        },
        treinamento,
    )
    if integracao["novatos"]:
        alertas.append(
            f"{integracao['novatos']} contratação(ões) ainda está(ão) em integração: "
            "a folha já incide, mas a capacidade produtiva ainda é parcial."
        )
    regime = e.get("regime_tributario", "SIMPLES_NACIONAL")
    fatores = {"MEI": 1.45, "SIMPLES_NACIONAL": 1.45, "LUCRO_PRESUMIDO": 1.82}
    equivalentes_folha = (composicao["operarios"] + composicao["tecnicos"] * 1.5
                          + composicao["especialistas"] * 2.2)
    folha = _produto(equivalentes_folha, salario * fracao, fatores.get(regime, 1.45))
    # O proprietário pode executar no máximo uma jornada júnior, e a atividade
    # exige pró-labore explícito. A jornada é proporcional à retirada comparada
    # ao salário de referência da turma (dedicação parcial do sócio).
    pro_labore = _dinheiro(max(0, op.get("pro_labore", 0)))
    dedicacao = dedicacao_fundador(pro_labore, salario_base, fracao)
    fundador_ativo = dedicacao > 0
    if 0 < dedicacao < 1:
        alertas.append(
            f"Pró-labore abaixo do salário de referência: o fundador dedica {dedicacao:.0%} "
            "de uma jornada à operação."
        )
    horas_extras = max(0, min(40 * fracao, op.get("horas_extras", 0))) if funcionarios else 0
    custo_horas_extras = _produto(funcionarios, salario / 220, horas_extras, 1.5, fatores.get(regime, 1.45))
    beneficios = _produto(funcionarios, beneficio * fracao)
    rescisoes = _produto(demitidos, salario)
    fator_rh = (0.75 + 0.25 * rh["moral"] / 100 + 0.002 * rh["qualificacao"]) * integracao["fator"]
    produtividade = p.get("produtividade_por_pessoa", 120)
    if e.get("autoeficacia", 60) < 30:
        produtividade *= 0.9
        alertas.append("Autoeficácia baixa: produtividade reduzida em 10%.")
    manutencao = _dinheiro(max(0, op.get("manutencao", 0)))
    ativas = [m for m in s["maquinas"] if m["ativacao"] <= rodada]
    capacidade_maquinas = sum(m["capacidade"] for m in ativas) * fracao * float(efeitos_eventos.get("capacidade", 1))
    kpis_oee = oee(s, manutencao, treinamento, funcionarios, ativas, max(0, op.get("producao", 0)), fracao)
    # Um evento de qualidade é adicional aos defeitos normais do OEE. A taxa
    # continua limitada à realidade física: nunca inferior a 0,5% nem superior a 100%.
    if efeitos_eventos.get("qualidade"):
        kpis_oee["taxa_defeito"] = max(.005, min(1.0, kpis_oee["taxa_defeito"] - float(efeitos_eventos["qualidade"])))
        kpis_oee["qualidade_oee"] = 1 - kpis_oee["taxa_defeito"]
        if kpis_oee["oee"] is not None:
            kpis_oee["oee"] = kpis_oee["disponibilidade"] * kpis_oee["performance"] * kpis_oee["qualidade_oee"]
    capacidades = capacidades_producao(capacidade_maquinas, funcionarios, produtividade, fator_rh, horas_extras,
                                       kpis_oee["disponibilidade"], kpis_oee["performance"], 220 * fracao,
                                       fundador_ativo=fundador_ativo, dedicacao_fundador=dedicacao)
    capacidade_produtiva = capacidades["capacidade_produtiva"]
    capacidade_trabalho = capacidades["capacidade_trabalho_regular"] + capacidades["capacidade_trabalho_extra"]
    kpis_rh = enps(s, funcionarios, salario, salario_base, beneficio, horas_extras)
    depreciacao = 0.0
    for maquina in ativas:
        parcela = min(maquina["valor_liquido"], _proporcao(maquina["custo"], fracao, max(1, maquina["vida_util"])))
        maquina["valor_liquido"] = _soma([maquina["valor_liquido"], -parcela])
        depreciacao = _soma([depreciacao, parcela])
    for ativo_linha in s["ativos_linhas"]:
        if ativo_linha.get("ativacao", rodada) > rodada:
            continue
        vida_util = max(1, int(ativo_linha.get("vida_util", 104 if "_calendario" in p else 24)))
        parcela = min(ativo_linha.get("valor_liquido", 0), _proporcao(ativo_linha.get("custo", 0), fracao, vida_util))
        ativo_linha["valor_liquido"] = _soma([ativo_linha.get("valor_liquido", 0), -parcela])
        depreciacao = _soma([depreciacao, parcela])
    maquinas_compradas = max(0, int(op.get("comprar_maquinas", 0)))
    preco_maquina = cfg.get("preco_maquina", 12000)
    investimento_maquinas = _produto(maquinas_compradas, preco_maquina)
    for _ in range(maquinas_compradas):
        s["maquinas"].append({"custo": _dinheiro(preco_maquina), "valor_liquido": _dinheiro(preco_maquina),
                              "capacidade": cfg.get("capacidade_maquina", 240), "condicao": 1.0,
                              "ativacao": rodada + 1, "vida_util": cfg.get("vida_util_maquina", 24), "risco_quebra": 0.0})
    if maquinas_compradas:
        alertas.append("Máquinas compradas ficam disponíveis na próxima rodada.")

    mp_inicial, pa_inicial = deepcopy(mp), deepcopy(pa)
    plano_comercial = d.get("plano_comercial") or {}
    itens=deepcopy(plano_comercial.get("produtos", []))
    from .portfolio import diagnosticos_segmentacao
    diagnosticos_publico = diagnosticos_segmentacao(itens, (plano_comercial.get("analises") or {}).get("segmentacao"))
    for item in itens:
        diagnostico = diagnosticos_publico.get(item.get("produto_id"), {})
        for aviso in diagnostico.get("avisos", []):
            alertas.append(f"{item.get('produto_nome', item.get('produto_id'))}: {aviso}")
    linhas_ativas = {ativo.get("produto_id") for ativo in s["ativos_linhas"]}
    linhas_ativadas_agora, linhas_ativadas_agora_ids, linhas_sem_capex = [], set(), []
    investimento_linhas = 0.0
    caixa_para_ativacao = max(0, caixa_obrigacoes + emprestimo - amortizacao - investimento_maquinas)
    vida_util_linha = int(cfg.get("vida_util_linha", 104 if "_calendario" in p else 24))
    for item in itens:
        produto_id = item["produto_id"]
        if produto_id in linhas_ativas:
            continue
        # Catálogos publicados antes da ativação de linhas podem trazer o
        # campo nulo. Nesse caso a linha é tratada como estruturalmente
        # disponível, sem converter ``None`` em erro de processamento.
        capex = _dinheiro(max(0, float(item.get("capex_ativacao") or 0)))
        # Mix gravados antes da introdução de Capex não podem ganhar uma
        # penalidade retroativa. Sem valor de homologação, a linha já é tratada
        # como estruturalmente disponível e não consome setup nesta rodada.
        if capex <= 0:
            linhas_ativas.add(produto_id)
            continue
        if capex > caixa_para_ativacao:
            linhas_sem_capex.append(item.get("produto_nome", produto_id))
            continue
        s["ativos_linhas"].append({
            "produto_id": produto_id,
            "nome": item.get("produto_nome", produto_id),
            "custo": capex,
            "valor_liquido": capex,
            "ativacao": rodada,
            "vida_util": max(1, vida_util_linha),
        })
        linhas_ativas.add(produto_id)
        linhas_ativadas_agora.append(item.get("produto_nome", produto_id))
        linhas_ativadas_agora_ids.add(produto_id)
        investimento_linhas = _soma([investimento_linhas, capex])
        caixa_para_ativacao = _soma([caixa_para_ativacao, -capex])
    if linhas_sem_capex:
        alertas.append(
            "Linha(s) não ativada(s) por falta de caixa para homologação e ferramental: "
            + ", ".join(linhas_sem_capex) + "."
        )
    if linhas_ativadas_agora:
        alertas.append(
            "Ativação de nova linha: o investimento foi lançado no fluxo de investimentos e a capacidade útil sofre setup nesta semana."
        )
    itens_operacionais = [item for item in itens if item["produto_id"] in linhas_ativas]
    pd = _dinheiro(d.get("pd", 0))
    # A qualidade global ainda informa a percepção de mercado. A ficha por
    # produto aplica o mesmo investimento, com fila própria, no custo e no
    # refugo da linha que efetivamente recebeu desenvolvimento.
    qualidade, pd_maturado = atualizar_pd(s, e.get("qualidade", 0), pd, rodada, "TRADICIONAL")
    pd_por_linha = atualizar_pd_por_produto(s, itens, pd, rodada, "TRADICIONAL")
    penalidade_setup = min(.75, sum(.15 * max(1.0, float(item.get("fator_setup") or 1))
                                    for item in itens if item["produto_id"] in linhas_ativadas_agora_ids))
    if penalidade_setup:
        capacidade_produtiva *= 1 - penalidade_setup
        alertas.append(f"Setup de linha reduziu a capacidade útil desta semana em {penalidade_setup * 100:.0f}%.")
    investimento = _soma([investimento_maquinas, investimento_linhas])
    # Escala melhora a negociação, mas o ganho tem teto de 15% e nunca reduz
    # a necessidade de caixa ou de compra física de insumo.
    compras_especificas = op.get("comprar_insumos_por_produto") or {}
    # Quando existe um mix publicado, o total da compra é apenas a soma das
    # linhas escolhidas. O agregado legado não pode criar insumo genérico que
    # abasteça indevidamente outro produto.
    compra_planejada = (
        sum(max(0, int(compras_especificas.get(item["produto_id"], 0))) for item in itens_operacionais)
        if itens_operacionais and compras_especificas else max(0, int(op.get("comprar_mp", 0)))
    )
    if itens_operacionais and compras_especificas:
        op = {**op, "comprar_mp": compra_planejada}
    if itens_operacionais:
        custo_base = sum(i["custo_unitario"] * i.get("peso", 1) for i in itens_operacionais) / max(1, sum(i.get("peso", 1) for i in itens_operacionais))
    else:
        custo_base = p.get("custo_unitario", 40)
    custo_unitario_atual, fator_barganha = custo_unitario_com_barganha(custo_base, compra_planejada)
    if itens_operacionais:
        for item in itens_operacionais:
            ganho_pd = pd_por_linha.get(item["produto_id"], {}).get("reducao_custo", 0)
            item["custo_unitario"] = _dinheiro(item["custo_unitario"] * (1 - fator_barganha) * (1 - ganho_pd))
    # Compra à vista só é possível com recurso financeiro disponível. Crédito
    # do fornecedor pode postergar a saída, mas continua registrado em pagar.
    fracao_prazo = _limitar(op.get("compras_prazo", 0), 0, 1)
    custo_vista_unitario = custo_unitario_atual * multiplicador_custo * (1 - fracao_prazo)
    caixa_para_compras = max(0, caixa_obrigacoes + emprestimo - amortizacao - investimento_maquinas - investimento_linhas)
    limite_compra = compra_planejada if custo_vista_unitario <= 0 else max(0, math.floor(caixa_para_compras / custo_vista_unitario))
    if itens_operacionais and compras_especificas:
        custo_vista_planejado = sum(
            max(0, int(compras_especificas.get(item["produto_id"], 0)))
            * item["custo_unitario"] * multiplicador_custo * (1 - fracao_prazo)
            for item in itens_operacionais
        )
        if custo_vista_planejado > caixa_para_compras and custo_vista_planejado > 0:
            proporcao = caixa_para_compras / custo_vista_planejado
            compras_limitadas = {
                item["produto_id"]: math.floor(max(0, int(compras_especificas.get(item["produto_id"], 0))) * proporcao)
                for item in itens_operacionais
            }
            op = {
                **op,
                "comprar_insumos_por_produto": compras_limitadas,
                "comprar_mp": sum(compras_limitadas.values()),
            }
            alertas.append("Compra de insumos por linha limitada pelo caixa disponível para pagamento à vista.")
    elif compra_planejada > limite_compra:
        op = {**op, "comprar_mp": limite_compra}
        alertas.append("Compra de insumos limitada pelo caixa disponível para pagamento à vista.")
    if itens:
        if not itens_operacionais:
            compras = producao_real = refugo = custo_refugo = compra_a_prazo = compra_a_vista = 0.0
            producao_pedida = max(0, int(op.get("producao", 0)))
            boas = 0
            utilizacao = 0.0
        else:
            from .portfolio import produzir
        # O portfólio lê a taxa armazenada no estado. A alteração causada por
        # uma ocorrência vale apenas enquanto ela estiver ativa, portanto não
        # é gravada como desgaste permanente após o fechamento.
            indicador = s.setdefault("indicadores_didaticos", {})
            defeito_normal = indicador.get("taxa_defeito")
            if efeitos_eventos.get("qualidade"):
                indicador["taxa_defeito"] = kpis_oee["taxa_defeito"]
            taxas_por_linha, diagnostico_qualificacao = _qualificacao_por_linha(
                itens_operacionais, rh, fundador_ativo, kpis_oee["taxa_defeito"]
            )
            for item in itens_operacionais:
                produto_id = item["produto_id"]
                # P&D melhora processo e insumo, mas não corrige a ausência de
                # uma qualificação obrigatória; neste caso prevalece o refugo de 80%.
                if diagnostico_qualificacao[produto_id]["compativel"]:
                    taxas_por_linha[produto_id] = max(
                        0.005,
                        taxas_por_linha[produto_id] - pd_por_linha.get(produto_id, {}).get("reducao_refugo", 0),
                    )
            linhas_sem_competencia = [
                item.get("produto_nome", item["produto_id"]) for item in itens_operacionais
                if not diagnostico_qualificacao[item["produto_id"]]["compativel"]
            ]
            if linhas_sem_competencia:
                alertas.append(
                    "Qualificação incompatível em " + ", ".join(linhas_sem_competencia)
                    + ": a taxa de refugo desta linha foi elevada a 80%."
                )
            compras, producao_real, refugo, custo_refugo=produzir(
                s, itens_operacionais, op, capacidade_produtiva, capacidade_maquinas, multiplicador_custo,
                taxas_defeito_linha=taxas_por_linha,
                qualificacao_linha=diagnostico_qualificacao,
            )
            if efeitos_eventos.get("qualidade"):
                indicador["taxa_defeito"] = defeito_normal
            mp,pa=s["estoque_mp"],s["estoque_pa"]
            producao_pedida=max(0,int(op.get("producao",0)))
            boas=producao_real-refugo
            utilizacao=producao_real/capacidades["capacidade_nominal_periodo"] if capacidades["capacidade_nominal_periodo"] else 0
            compra_a_prazo=_produto(compras,_limitar(op.get("compras_prazo",0),0,1))
            compra_a_vista=_soma([compras,-compra_a_prazo])
            if compra_a_prazo: s["pagar"].append({"origem":rodada,"vencimento":rodada+op.get("prazo_pagamento",1),"valor":compra_a_prazo})
    else:
        unidades_compra = max(0, int(op.get("comprar_mp", 0)))
        compras = _produto(unidades_compra, custo_unitario_atual, multiplicador_custo)
        compra_a_prazo = _produto(compras, _limitar(op.get("compras_prazo", 0), 0, 1))
        compra_a_vista = _soma([compras, -compra_a_prazo])
        if compra_a_prazo:
            s["pagar"].append({"origem": rodada, "vencimento": rodada + op.get("prazo_pagamento", 1),
                               "valor": compra_a_prazo})
        mp["quantidade"] += unidades_compra
        mp["valor"] = _soma([mp["valor"], compras])
        producao_pedida = max(0, int(op.get("producao", 0)))
        producao_real = min(producao_pedida, mp["quantidade"], int(math.floor(capacidade_produtiva + 1e-12)))
        utilizacao = producao_real / capacidades["capacidade_nominal_periodo"] if capacidades["capacidade_nominal_periodo"] > 0 else 0.0
        taxa_refugo = kpis_oee["taxa_defeito"]
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
        alertas.append(f"Refugo de produção: {refugo} unidade(s) perdidas; insumos consumidos não geram estoque vendável.")
    sobrecarga_trabalho = max(0, producao_real / capacidade_trabalho - 0.90) if capacidade_trabalho else 0
    rh["moral"] = round(_limitar(rh["moral"] - 10 * sobrecarga_trabalho), 8)

    from .eventos_operacionais import juros_evento_periodo
    juros_banco = _produto(
        divida,
        p.get("taxa_juros_mensal", 0.025) + juros_evento_periodo(efeitos_eventos, fracao),
    )
    juros_cheque = _produto(max(0, -caixa_inicio), p.get("taxa_cheque_especial", 0.08))
    juros = _soma([juros_banco, juros_cheque])
    if juros_cheque:
        alertas.append("Juros de cheque especial sobre o saldo negativo de abertura.")
    custos_fixos = _dinheiro(p.get("custos_fixos_mensais", 1500))
    marketing = _produto(d.get("marketing", 0), float(efeitos_eventos.get("marketing", 1)))
    networking = _dinheiro(d.get("networking", 0))
    multas = _dinheiro(p.get("multas", 0))
    custos_eventos = _dinheiro(efeitos_eventos.get("custo", 0))
    despesas_pagas = _soma([folha, custo_horas_extras, beneficios, treinamento, rescisoes, pro_labore, manutencao,
                            custos_fixos, marketing, pd, networking, juros, multas])

    from ..custos_campanhas import investimento_efetivo
    verba_midia=investimento_efetivo(d)
    # Marca perde força sem presença ativa; a resposta ao investimento é
    # logarítmica, evitando que orçamento alto compre demanda infinita.
    marca = atualizar_marca(e.get("marca", 0), verba_midia)
    canal = getattr(op.get("canal", "DIRETO"), "value", op.get("canal", "DIRETO"))
    digital = min(verba_midia, _dinheiro(max(0, op.get("marketing_digital", 0))))
    fator_canal = {
        "DIRETO": 1.0,
        "DISTRIBUIDOR": 1.10,
        "DIGITAL": 1.05 + (0.10 * digital / verba_midia if verba_midia else 0),
    }.get(canal, 1.0)
    taxa_comissao_canal = {"DIRETO": 0.0, "DISTRIBUIDOR": 0.05, "DIGITAL": 0.03}.get(canal, 0.0)
    # Marketing digital é parte do orçamento já lançado e melhora a marca;
    # não é uma despesa adicional nem um segundo custo.
    if digital:
        marca = atualizar_marca(marca, digital, eficiencia=.0002, decaimento=0)
    # Esta informação precisa existir já na preparação: a divisão de mercado
    # acontece antes da apuração de vendas. Sem ela, uma empresa com catálogo
    # e campanha válidos seria excluída indevidamente da demanda.
    produto_publicado = bool(itens)
    comercial_ativo = produto_publicado and marketing > 0
    preco = max(0.01, d.get("preco", 100))
    atratividade = atrativo_porter(marca, qualidade, preco, p.get("preco_referencia", 100))
    atratividade *= (0.5 + 0.5 * s["satisfacao"] / 100) * fator_canal
    diferenciar = op.get("posicionamento", "CUSTO") == "DIFERENCIACAO"
    desalinhada = ((diferenciar and marca < 3 and qualidade < 3)
                   or (not diferenciar and preco > p.get("preco_referencia", 100)))
    if desalinhada:
        atratividade *= 0.75
        alertas.append("Posicionamento e proposta de valor desalinhados: atratividade reduzida em 25%.")
    taxa_royalties = p.get("taxa_royalties", 0.05 if e.get("classe_dornelas") == "FRANQUIA" else 0)
    return {
        "empresa": e, "decisao": d, "parametros": p, "rodada": rodada,
        "kpis": {**kpis_oee, **kpis_rh, **capacidades,
                 "composicao_equipe": deepcopy(composicao),
                 "equivalentes_folha": equivalentes_folha,
                 "integracao_equipe": deepcopy(integracao),
                 "qualidade_observada": boas / producao_real if producao_real else None,
                 "oee_observado": kpis_oee["disponibilidade"] * kpis_oee["performance"] * boas / producao_real if kpis_oee["oee"] is not None and producao_real else None},
        "estado_inicial": inicial, "estado": s, "funcionarios": funcionarios,
        "emprestimo": emprestimo, "amortizacao": amortizacao, "amortizacao_obrigatoria": obrigatoria,
        "divida": divida, "caixa_inicio": caixa_inicio, "caixa_disponivel": _soma([caixa_obrigacoes, emprestimo, -amortizacao]),
        "capacidade": capacidade_produtiva, "estoque_disponivel": pa["quantidade"], "capacidade_produtiva": capacidade_produtiva,
        "capacidade_maquinas": capacidade_maquinas, "utilizacao_maquinas": utilizacao,
        "atratividade": atratividade, "marca": marca, "qualidade": qualidade,
        "produto_publicado": produto_publicado, "comercial_ativo": comercial_ativo,
        "custos_eventos": custos_eventos,
        "marketing": marketing,
        "horas_extras": horas_extras, "custo_horas_extras": custo_horas_extras,
        "folha": folha, "pro_labore": pro_labore, "fundador_ativo": fundador_ativo, "dedicacao_fundador": dedicacao,
        "juros": juros, "juros_cheque": juros_cheque,
        "gastos_previstos": _soma([despesas_pagas, custos_eventos, depreciacao, custo_refugo]),
        "beneficios": beneficios, "treinamento": treinamento, "rescisoes": rescisoes,
        "manutencao": manutencao, "depreciacao": depreciacao, "custo_refugo": custo_refugo,
        "despesas_pagas": despesas_pagas, "compras_a_vista": compra_a_vista, "compras_mes": compras,
        "pagamentos_vencidos": pagamentos_vencidos, "recebimentos_vencidos": recebimentos,
        "investimento": investimento, "taxa_royalties": taxa_royalties,
        "investimento_maquinas": investimento_maquinas, "investimento_linhas": investimento_linhas,
        "linhas_ativadas_agora": linhas_ativadas_agora, "linhas_sem_capex": linhas_sem_capex,
        "penalidade_setup": penalidade_setup,
        "fator_barganha_fornecedor": fator_barganha, "custo_unitario_insumo": custo_unitario_atual,
        "canal": canal, "marketing_digital": digital, "pd_maturado": pd_maturado,
        "pd_por_linha": pd_por_linha,
        "taxa_comissao_canal": taxa_comissao_canal,
        "producao_planejada": producao_pedida, "producao_real": producao_real,
        "producao_boa": boas, "refugo": refugo, "turnover": turnover,
        "estoque_mp_inicial": mp_inicial, "estoque_pa_inicial": pa_inicial,
        "diagnosticos_segmentacao": diagnosticos_publico,
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
    plano_comercial = d.get("plano_comercial") or {}
    itens=plano_comercial.get("produtos", [])
    publicado = bool(itens)
    # A mercadoria só sai do estoque se a empresa reservou recurso para o
    # escoamento. O frete contratado define uma capacidade física de entrega.
    localizacao = estimar_frete(op, cfg)
    efeitos_eventos = p.get("eventos_operacionais") or {}
    custo_frete = localizacao["frete_unitario"] * float(efeitos_eventos.get("frete", 1))
    orcamento_logistico = max(0.0, float(op.get("orcamento_logistico", 0)))
    capacidade_entrega = (math.floor(orcamento_logistico / custo_frete)
                           if custo_frete > 0 and orcamento_logistico > 0 else 0)
    comercial_ativo = publicado and c.get("marketing", 0) > 0
    demanda_comercial = min(demanda, capacidade_entrega) if comercial_ativo else 0
    if demanda and not publicado:
        c["alertas"].append("Demanda anulada: nenhum produto foi publicado no mix comercial.")
    elif demanda and c.get("marketing", 0) <= 0:
        c["alertas"].append("Demanda anulada: marketing da semana está zerado; não há alcance orgânico automático.")
    elif demanda and capacidade_entrega <= 0:
        c["alertas"].append("Demanda anulada: não há orçamento de logística para despachar os pedidos.")
    linhas=[]
    if itens:
        from .portfolio import vender, atrativos
        segmentacao = (plano_comercial.get("analises") or {}).get("segmentacao")
        pesos=atrativos(itens,p.get("preco_referencia",100),p.get("custo_referencia_portfolio",40),c["marca"],c["qualidade"], segmentacao)
        linhas=vender(s,itens,demanda_comercial,pesos,c.get("diagnosticos_segmentacao"))
        vendas=sum(l["vendas"] for l in linhas)
        cmv=_soma(l["cmv"] for l in linhas);receita=_soma(l["receita"] for l in linhas)
        pa=s["estoque_pa"]
    else:
        vendas = min(demanda_comercial, pa["quantidade"])
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
    frete = _produto(vendas, custo_frete)
    armazenagem_sobre_valor = _produto(pa["valor"], cfg.get("custo_armazenagem", 0.01))
    ocupacao_armazenagem_m3 = 0.0
    if itens and s.get("estoques_produtos"):
        for item in itens:
            estoque_linha = s["estoques_produtos"].get(item["produto_id"], {}).get("estoque_pa", {})
            # Catálogos antigos podem não trazer o volume do item. Nesse caso,
            # não há ocupação volumétrica adicional — mas o fechamento não pode
            # falhar por tentar converter ``None`` em número.
            ocupacao_armazenagem_m3 += estoque_linha.get("quantidade", 0) * max(0, float(item.get("volume_armazenagem_m3") or 0))
    armazenagem_por_volume = _produto(ocupacao_armazenagem_m3, cfg.get("custo_armazenagem_m3", 0))
    armazenagem = _soma([armazenagem_sobre_valor, armazenagem_por_volume])
    royalties = _produto(receita, c["taxa_royalties"])
    comissao_canal = _soma(l["comissao_canal"] for l in linhas) if linhas else _produto(receita, c["taxa_comissao_canal"])
    # Inadimplência só alcança vendas a prazo; não reduz ficticiamente vendas à vista.
    perda_recebiveis = _produto(venda_prazo, min(.95, max(0.0, float(efeitos_eventos.get("recebiveis_perda", 0)))))
    if perda_recebiveis:
        s["receber"][-1]["valor"] = _soma([s["receber"][-1]["valor"], -perda_recebiveis])
    custos_eventos = _soma([c.get("custos_eventos", 0), perda_recebiveis])
    dre = {
        "receita": receita, "impostos": impostos, "cmv": cmv, "folha": c["folha"], "pro_labore": c["pro_labore"],
        "horas_extras": c["custo_horas_extras"],
        "custos_fixos": _dinheiro(p.get("custos_fixos_mensais", 1500)),
        "marketing": c["marketing"], "pd": _dinheiro(d.get("pd", 0)),
        "networking": _dinheiro(d.get("networking", 0)), "rescisoes": c["rescisoes"],
        "royalties": royalties, "juros": c["juros"], "multas": _dinheiro(p.get("multas", 0)),
        "comissao_canal": comissao_canal,
        "refugos": c["custo_refugo"], "frete": frete, "armazenagem": armazenagem,
        "depreciacao": c["depreciacao"], "beneficios": c["beneficios"],
        "treinamento": c["treinamento"], "manutencao": c["manutencao"],
        "eventos_operacionais": custos_eventos,
    }
    dre["lucro_liquido"] = _soma([receita, -_soma(v for k, v in dre.items() if k != "receita")])
    recebimentos = _soma([c["recebimentos_vencidos"], venda_vista])
    # DRE reconhece impostos por competência. No DFC, o tributo é liquidado no
    # fechamento mensal simulado; até lá, torna-se obrigação de curto prazo.
    periodo = p.get("_calendario", {})
    fim_mes = bool(periodo.get("fim_mes"))
    imposto_pagar = impostos if fim_mes else 0.0
    if impostos and not fim_mes:
        from .calendario import proxima_rodada_fechamento_mensal
        s["pagar"].append({
            "origem": c["rodada"],
            "vencimento": proxima_rodada_fechamento_mensal(p.get("configuracao_simulacao") or {}, c["rodada"]),
            "valor": impostos,
            "origem_contabil": "impostos_provisionados",
        })
    pagamentos = _soma([c["pagamentos_vencidos"], c["compras_a_vista"], c["despesas_pagas"], c.get("custos_eventos", 0),
                        imposto_pagar, frete, armazenagem, royalties, comissao_canal])
    operacional = _soma([recebimentos, -pagamentos])
    investimento, financiamento = -c["investimento"], _soma([c["emprestimo"], -c["amortizacao"]])
    variacao = _soma([operacional, investimento, financiamento])
    caixa = _soma([c["caixa_inicio"], variacao])
    ruptura = demanda - vendas
    multa_ruptura = _produto(ruptura, max(0.0, float(cfg.get("multa_ruptura_unitaria", 0))))
    if multa_ruptura:
        dre["multas"] = _soma([dre["multas"], multa_ruptura])
        dre["lucro_liquido"] = _soma([dre["lucro_liquido"], -multa_ruptura])
        pagamentos = _soma([pagamentos, multa_ruptura])
        operacional = _soma([recebimentos, -pagamentos])
        variacao = _soma([operacional, investimento, financiamento])
        caixa = _soma([c["caixa_inicio"], variacao])
    indicadores_entrega = otif(demanda, vendas, modal)
    falhas_transporte = indicadores_entrega["pedidos_com_falha"] - indicadores_entrega["pedidos_nao_atendidos"]
    atraso = falhas_transporte / vendas if vendas else 0
    s["satisfacao"] = round(_limitar(s["satisfacao"] + float(efeitos_eventos.get("satisfacao", 0)) + (2 - 30 * atraso if vendas else 0)
                                    - (20 * ruptura / demanda if demanda else 0)), 8)
    if c["kpis"]["oee"] is not None:
        c["alertas"].append(f"OEE simulado: {c['kpis']['oee'] * 100:.2f}%. Manutenção e treinamento alteram disponibilidade, ritmo e defeitos.")
    if c["kpis"]["enps"] is not None:
        c["alertas"].append(f"eNPS simulado: {c['kpis']['enps']:+.0f}. Salários, benefícios e horas extras recorrentes definem as respostas.")
    if ruptura:
        c["alertas"].append(f"Ruptura: {ruptura} unidade(s) de demanda sem estoque disponível.")
    if vendas and atraso:
        c["alertas"].append("Falhas de transporte reduzem a satisfação usada na próxima rodada.")
    receber, pagar = (_soma(t["valor"] for t in s[nome]) for nome in ("receber", "pagar"))
    estoques = _soma(s[nome]["valor"] for nome in ("estoque_mp", "estoque_pa", "estoque_obsoleto"))
    imobilizado_maquinas = _soma(m["valor_liquido"] for m in s["maquinas"])
    ativos_linhas = _soma(ativo.get("valor_liquido", 0) for ativo in s.get("ativos_linhas", []))
    imobilizado = _soma([imobilizado_maquinas, ativos_linhas])
    patrimonio = _soma([caixa, receber, estoques, imobilizado, -pagar, -c["divida"]])
    balanco = {"caixa": caixa, "receber": receber, "pagar": pagar, "estoques": estoques,
               "imobilizado": imobilizado, "imobilizado_maquinas": imobilizado_maquinas,
               "ativos_linhas": ativos_linhas, "divida": c["divida"], "patrimonio": patrimonio,
               "capital_giro": _soma([receber, estoques, -pagar])}
    dfc = {"caixa_inicial": c["caixa_inicio"], "recebimentos": recebimentos,
           "pagamentos": pagamentos, "operacional": operacional, "investimento": investimento,
           "financiamento": financiamento, "variacao": variacao, "caixa_final": caixa}
    operacao = {k: c[k] for k in ("producao_planejada", "producao_real", "producao_boa", "refugo",
                                "capacidade_produtiva", "capacidade_maquinas", "utilizacao_maquinas",
                                "estoque_mp_inicial", "estoque_pa_inicial", "turnover", "horas_extras", "custo_horas_extras")}
    operacao.update(funcionarios_inicio=c["empresa"].get("funcionarios",0),
                    desligamentos_efetivos=c["turnover"]+min(max(0,int(d.get("demitir",0))),max(0,c["empresa"].get("funcionarios",0)-c["turnover"])))
    operacao.update(c["kpis"])
    operacao.update(reconciliar_financeiros(balanco, s, dre, c["rodada"], p.get("taxa_cheque_especial", 0.08), c["compras_mes"], dias=p.get("_calendario", {}).get("dias",30), horizonte=52 if "_calendario" in p else 12))
    operacao.update(indicadores_entrega)
    operacao.update(
        admissoes=(max(0, int(d.get("contratar", 0))) + max(0, int(d.get("contratar_tecnicos") or 0))
                   + max(0, int(d.get("contratar_especialistas") or 0))),
        admissoes_operarios=max(0, int(d.get("contratar", 0))),
        admissoes_tecnicos=max(0, int(d.get("contratar_tecnicos") or 0)),
        admissoes_especialistas=max(0, int(d.get("contratar_especialistas") or 0)),
        demissoes=max(0, int(d.get("demitir", 0))), treinamento=c["treinamento"], manutencao=c["manutencao"],
    )
    operacao.update(localizacao)
    operacao["produtos"]=linhas
    operacao.update(demanda=demanda, demanda_comercial=demanda_comercial, vendas=vendas, ruptura=ruptura,
                    estoque_mp_final=deepcopy(s["estoque_mp"]), estoque_pa_final=deepcopy(pa),
                    satisfacao=s["satisfacao"], moral=s["rh"]["moral"], qualificacao=s["rh"]["qualificacao"],
                    amortizacao_obrigatoria=c["amortizacao_obrigatoria"], canal=c["canal"],
                    marketing_digital=c["marketing_digital"], comissao_canal=comissao_canal,
                    orcamento_logistico=orcamento_logistico, capacidade_entrega=capacidade_entrega,
                    comercial_ativo=comercial_ativo, produto_publicado=publicado,
                    pd_maturado=c.get("pd_maturado", []), fundador_ativo=c["fundador_ativo"],
                    pro_labore=c["pro_labore"], investimento_linhas=c.get("investimento_linhas", 0),
                    linhas_ativadas_agora=c.get("linhas_ativadas_agora", []),
                    linhas_sem_capex=c.get("linhas_sem_capex", []), penalidade_setup=c.get("penalidade_setup", 0),
                    ocupacao_armazenagem_m3=_dinheiro(ocupacao_armazenagem_m3),
                    armazenagem_sobre_valor=armazenagem_sobre_valor,
                    armazenagem_por_volume=armazenagem_por_volume)
    operacao["eventos_operacionais"] = deepcopy(p.get("eventos_operacionais") or {})
    detalhes = {"versao_motor": 1, "engine_version": ENGINE_VERSION, "modo": "TRADICIONAL", "configuracao": deepcopy(p),
                "estado_inicial": deepcopy(c["estado_inicial"]), "estado_final": deepcopy(s),
                "operacao": operacao, "dfc": dfc, "balanco": balanco}
    return {"estado": deepcopy(s), "caixa": caixa, "divida": c["divida"], "funcionarios": c["funcionarios"],
            "capacidade": c["capacidade_produtiva"], "vendas": vendas, "dre": dre, "aliquota": aliquota,
            "detalhes": detalhes, "alertas": c["alertas"], "satisfacao": s["satisfacao"],
            "marca": c["marca"], "qualidade": c["qualidade"]}
