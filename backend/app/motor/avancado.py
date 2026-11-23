"""Integração dos motores didáticos v1 e snapshots históricos, sem mudar o legado."""
from copy import deepcopy
from datetime import date, datetime
from enum import Enum
import math

from ..models import Empresa, Resultado, RegimeTributario, FaseAtual
from ..schemas import ConfiguracaoSimulacao, DecisaoSimulacao
from .calendario import adaptar, periodo, VERSAO_SEMANAL
from .tributos import calcular_imposto, aliquota_efetiva_simples, TOLERANCIA_TETO_MEI
from .dependencias import atrativo_porter


def config(turma):
    dados = deepcopy(turma.configuracao_simulacao or {})
    # Metadados normativos são preenchidos pelo serviço de fontes oficiais e
    # não fazem parte do formulário de parâmetros do professor.
    confirmacoes_normativas = dados.pop("confirmacoes_normativas", {})
    configuracao = ConfiguracaoSimulacao.model_validate(dados).model_dump()
    if confirmacoes_normativas:
        configuracao["confirmacoes_normativas"] = confirmacoes_normativas
    return configuracao


def estado_inicial(turma):
    cfg = config(turma)
    crise = turma.cenario == "CRISE"
    tradicional = turma.modo_jogo == "TRADICIONAL"
    custo = turma.custo_unitario
    # Turmas com catálogo: a loja revende (aprovado em 21/11/2026) e não começa
    # com máquina; a fábrica fica para a marca própria a partir da rodada 5.
    from ..routers.mercado import usa_catalogo_fixo
    revenda = tradicional and usa_catalogo_fixo(turma) and not cfg.get("fabrica_inicial")
    return {
        "versao": 1,
        "estoque_mp": {"quantidade": 100 if crise and tradicional else 0, "valor": 100 * custo if crise and tradicional else 0},
        "estoque_pa": {"quantidade": 100 if crise and tradicional else 0, "valor": 100 * custo if crise and tradicional else 0},
        "estoque_obsoleto": {"quantidade": 50 if crise and tradicional else 0, "valor": 0},
        "maquinas": [{"custo": cfg["preco_maquina"], "valor_liquido": cfg["preco_maquina"] * (.5 if crise else 1),
                       "capacidade": cfg["capacidade_maquina"], "condicao": .55 if crise else 1,
                       "ativacao": 1, "vida_util": cfg["vida_util_maquina"]}] if tradicional and not revenda else [],
        "receber": [{"origem": 0, "vencimento": 1, "valor": 5000}] if crise else [],
        "pagar": [{"origem": 0, "vencimento": 1, "valor": 8000}] if crise else [],
        "rh": {"moral": 40 if crise else 80, "qualificacao": 0, "rotatividade_acumulada": 0},
        "satisfacao": 45 if crise else 80,
        "clientes": 100 if crise and not tradicional else 0,
        "participacao_fundadores": 1,
        "capital_aportado": 0,
        **({"vencimento_divida": 3} if crise else {}),
    }


def iniciar_empresa(empresa, turma):
    if turma.modo_jogo == "LEGADO":
        return
    empresa.estado_simulacao = estado_inicial(turma)
    if turma.cenario == "CRISE":
        empresa.caixa = round(turma.caixa_inicial * .25, 2)
        empresa.divida = 20000


def colunas(objeto):
    return {c.name: (valor.value if isinstance(valor := getattr(objeto, c.name), Enum) else deepcopy(valor))
            for c in objeto.__table__.columns}


def parametros(turma):
    dados = colunas(turma)
    dados.pop("criado_em", None)
    # O prazo é preservado na fotografia histórica como ISO, nunca como objeto ORM.
    for nome, valor in dados.items():
        if isinstance(valor, (date, datetime)):
            dados[nome] = valor.isoformat()
    dados["configuracao_simulacao"] = config(turma)
    from ..mercado_pac import custos_da_turma
    custos = custos_da_turma(turma)
    if custos:
        # Catálogo fixo: despesas fixas da loja pela PAC 2024. Item B (17/11/2026):
        # o custo de manter estoque é o custo de oportunidade do capital
        # (Ballou, 2007, p. 279-280; Assaf Neto, 2014, p. 701-702). O caixa
        # positivo rende a Selic do mês (Assaf Neto, p. 91 e 126) e o estoque
        # parado deixa de render; não há despesa de armazenagem separada (o
        # espaço já está no aluguel da PAC).
        dados["custos_fixos_mensais"] = custos["custos_fixos"]["total"]
        dados["configuracao_simulacao"]["custo_armazenagem"] = 0.0
        dados["configuracao_simulacao"]["custo_armazenagem_m3"] = 0.0
        dados["rendimento_caixa_mensal"] = custos["taxa_capital_estoque"]
        dados["custos_loja"] = custos
        # Equipe da loja (itens 1 e 2, 22/11/2026): limite de atendimento por
        # pessoa (PAC 2024) e salário de referência da PAC, nunca abaixo do
        # salário mínimo (CF, art. 7º, IV).
        dados["receita_por_pessoa_mensal"] = custos["receita_por_pessoa"]["valor"]
        dados["salario_minimo"] = custos["salario_minimo"]
        dados["salario_base"] = max(custos["salario_referencia"], custos["salario_minimo"])
        from ..banho_tosa import setor_tem_servico
        # Banho e tosa só existe no setor pet (23/11/2026).
        dados["setor_servico_banho_tosa"] = setor_tem_servico(custos.get("setor"))
    return dados


def motor(turma):
    from . import tradicional, startup
    return startup if turma.modo_jogo == "STARTUP" else tradicional


def preparar(empresa, decisao, turma, multiplicador_custo=1, multa=0, efeitos_operacionais=None):
    dados = colunas(empresa)
    dados["estado_simulacao"] = dados["estado_simulacao"] or estado_inicial(turma)
    if turma.modo_jogo=="TRADICIONAL":
        anteriores=[d for d in empresa.decisoes if d.rodada<turma.rodada_atual and d.plano_comercial]
        original=anteriores[-1].plano_comercial["produto_id"] if anteriores else (decisao.plano_comercial or {}).get("produto_id")
        if original: dados["estado_simulacao"].setdefault("produto_estoque_original",original)
    entrada = colunas(decisao)
    simulacao_salva = dict(entrada["simulacao"] or {})
    salario_ajustado = False
    from ..mercado_pac import salario_minimo_vigente
    if simulacao_salva.get("salario") is not None and float(simulacao_salva["salario"]) < salario_minimo_vigente():
        # Decisão gravada antes da trava do salário mínimo (22/11/2026): o
        # fechamento não falha; o salário sobe ao mínimo legal e o aluno é avisado.
        simulacao_salva["salario"] = salario_minimo_vigente()
        salario_ajustado = True
    entrada["simulacao"] = DecisaoSimulacao.model_validate(simulacao_salva).model_dump()
    p = parametros(turma)
    p["custo_referencia_portfolio"]=turma.custo_unitario
    if decisao.plano_comercial:
        p["custo_unitario"] = decisao.plano_comercial["custo_unitario"]
        if turma.modo_jogo == "STARTUP":
            p["configuracao_simulacao"]["custo_nuvem_cliente"] = decisao.plano_comercial["custo_unitario"]
    from .portfolio import propaganda_para
    p["propaganda"] = propaganda_para(turma, turma.rodada_atual, empresa, decisao.plano_comercial)
    p["multa_evento"] = multa
    p["multas"] = multa
    p["eventos_operacionais"] = deepcopy(efeitos_operacionais or {})
    preparo = motor(turma).preparar(dados, entrada, p, turma.rodada_atual, multiplicador_custo)
    if salario_ajustado:
        preparo.setdefault("alertas", []).append(
            "Salário abaixo do salário mínimo na decisão gravada: ajustado ao mínimo legal (Constituição, art. 7º, IV).")
    # A mesma parametrização usada pelo motor acompanha a prévia até o
    # fechamento, inclusive os efeitos de ocorrências operacionais.
    preparo["parametros"] = deepcopy(p)
    itens=(decisao.plano_comercial or {}).get("produtos", [])
    if itens:
        from .portfolio import atrativos, diagnosticos_segmentacao
        segmentacao = ((decisao.plano_comercial or {}).get("analises") or {}).get("segmentacao")
        from .simulacao import ELASTICIDADE_PRECO_ESCOLHA
        # Startup mantém 1,4 até ser refeita com o Modo Empresa do zero (dezembro).
        base=(turma.preco_referencia/decisao.preco)**(1.4 if turma.modo_jogo=="STARTUP" else ELASTICIDADE_PRECO_ESCOLHA)
        if any(i.get("preco_mercado") for i in itens):
            base = 1.0  # item 2b: sem divisão pelo preço de referência antigo
        preparo["atratividade"]*=sum(atrativos(itens,turma.preco_referencia,turma.custo_unitario,empresa.marca,empresa.qualidade,segmentacao,p.get("propaganda")))/sum(i["peso"] for i in itens)/base
        preparo["diagnosticos_segmentacao"] = diagnosticos_segmentacao(itens, segmentacao)
    from .estrategia import avaliar, mensagens
    avaliacao = avaliar(decisao, turma)
    preparo["avaliacao_estrategica"] = avaliacao
    preparo["alertas"].extend(mensagens(avaliacao))
    # O cockpit e a validação final usam exatamente a mesma fotografia do
    # motor: não há regra visual que não exista no fechamento da rodada.
    from .dependencias import radar_coerencia
    if turma.modo_jogo == "TRADICIONAL":
        from .localizacao import estimar_frete
        frete = estimar_frete(entrada.get("simulacao") or {}, p.get("configuracao_simulacao") or {})["frete_unitario"]
        capacidade_operacional = preparo.get("capacidade_produtiva", 0)
    else:
        frete = 0.0
        capacidade_operacional = preparo.get("capacidade", 0)
    preparo["radar"] = radar_coerencia(
        modo=turma.modo_jogo,
        decisao=entrada,
        plano_comercial=entrada.get("plano_comercial"),
        caixa=preparo.get("caixa_disponivel", dados.get("caixa", 0)),
        funcionarios=preparo.get("funcionarios", 0),
        capacidade_operacional=capacidade_operacional,
        estoque_disponivel=(preparo.get("estado") or {}).get("estoque_pa", {}).get("quantidade", 0),
        custo_frete_unitario=frete,
        gastos_previstos=preparo.get("gastos_previstos", 0),
    )
    preparo["alertas"].extend(preparo["radar"]["avisos"])
    if decisao.emprestimo > 0:
        preparo["alertas"].append("Crédito bancário tem custo alto: juros mensais reduzem lucro e capital de giro, podem subir com a Selic, e o principal precisa ser devolvido.")
    return preparo


def prever(empresa, decisao, turma):
    calculo = preparar(empresa, decisao, turma, turma.cmv_multiplicador if turma.cmv_rodadas_restantes > 0 else 1)
    op = (decisao.simulacao or {})
    if turma.modo_jogo == "TRADICIONAL":
        cfg = config(turma)
        from .localizacao import estimar_frete
        localizacao = estimar_frete(op, cfg)
        custo = ((decisao.plano_comercial or {}).get("custo_unitario", turma.custo_unitario)) * (turma.cmv_multiplicador if turma.cmv_rodadas_restantes > 0 else 1)
        margem = decisao.preco * (1 - (0.05 if empresa.classe_dornelas.value == "FRANQUIA" else 0)) - custo - localizacao["frete_unitario"]
        # A prévia deve mostrar aquilo que a empresa conseguirá preparar nesta
        # semana, e não o teto abstrato da fábrica. A capacidade continua
        # exposta separadamente para tornar o gargalo visível ao aluno.
        producao = calculo.get("producao_real", 0)
    else:
        margem = decisao.preco - (decisao.plano_comercial or {}).get("custo_unitario", config(turma)["custo_nuvem_cliente"])
        producao = calculo.get("capacidade_atendimento", 0)
    gastos = calculo.get("gastos_previstos", 0)
    return {
        "rodada": turma.rodada_atual, "regime": empresa.regime_tributario.value,
        "funcionarios": calculo["funcionarios"],
        "capacidade": (
            calculo.get("capacidade_produtiva")
            or calculo.get("capacidade_atendimento")
            or calculo.get("capacidade", 0)
        ),
        "folha": calculo.get("folha", 0), "juros": calculo.get("juros", 0),
        "gastos_previstos": gastos, "margem_unitaria": margem,
        "ponto_equilibrio": gastos / margem if margem > 0 else None,
        "emprestimo_aprovado": calculo.get("emprestimo", 0),
        "amortizacao_aplicada": calculo.get("amortizacao", 0),
        "divida_prevista": empresa.divida + calculo.get("emprestimo", 0) - calculo.get("amortizacao", 0),
        "caixa_disponivel": calculo.get("caixa_disponivel", empresa.caixa + calculo.get("emprestimo", 0) - calculo.get("amortizacao", 0)),
        "alertas": calculo.get("alertas", []),
        "radar": calculo.get("radar", {"bloqueios": [], "avisos": [], "liberado": True}),
        "simulacao": {"estado": deepcopy(calculo.get("estado", {})), "producao": producao,
                       **(localizacao if turma.modo_jogo == "TRADICIONAL" else {}),
                       "avaliacao_estrategica": calculo["avaliacao_estrategica"],
                       "aviso": "Estimativa sem vendas: demanda e eventos da próxima rodada ainda são desconhecidos."},
    }


def _tributar(empresa, turma, receita, cmv, alertas, servicos=0.0):
    regime = empresa.regime_tributario
    temporal = adaptar(parametros(turma), turma.rodada_atual)
    historico = [r.receita for r in empresa.resultados]
    if temporal.get('_calendario') and regime == RegimeTributario.SIMPLES_NACIONAL:
        # Anualização pelo tempo efetivamente simulado, sem contar uma semana como mês.
        ultimos = empresa.resultados[-52:]
        equivalentes = sum((r.detalhes_simulacao or {}).get('calendario', {}).get('fator_mensal', 1) for r in ultimos)
        base = sum(r.receita for r in ultimos)/equivalentes*12 if equivalentes else receita/temporal['_calendario']['fator_mensal']*12
        from .tributos import imposto_simples
        impostos = imposto_simples(receita, base, servicos)
        aliquota = impostos / receita if receita > 0 else aliquota_efetiva_simples(base)
    else:
        impostos, aliquota = calcular_imposto(regime, receita, cmv, historico,
                                             temporal["das_mei_mensal"], turma.aliquota_icms, servicos)
    acumulado = empresa.faturamento_ano + receita
    if regime == RegimeTributario.MEI:
        empresa.das_mei_pago_ano += impostos
        from .regras_mei import regras_mei
        teto = regras_mei(turma, turma.rodada_atual)["teto_anual"]
        if acumulado > teto * (1 + TOLERANCIA_TETO_MEI):
            impostos += max(0, acumulado * aliquota_efetiva_simples(acumulado) - empresa.das_mei_pago_ano)
            empresa.regime_tributario = RegimeTributario.SIMPLES_NACIONAL
            alertas.append("Teto do MEI excedido em mais de 20%: migração e complemento retroativo de tributos.")
        elif acumulado > teto:
            impostos += (acumulado - max(teto, empresa.faturamento_ano)) * .04
            empresa.regime_pretendido = RegimeTributario.SIMPLES_NACIONAL
            alertas.append("Teto do MEI excedido: complemento e migração na próxima rodada.")
    return impostos, aliquota


def forca_concorrente(cfg, indice):
    nivel = {"BAIXA": .8, "MEDIA": 1, "ALTA": 1.2}[cfg.get("nivel_concorrencia", "MEDIA")]
    forca = {"FRACA": .7, "MEDIA": 1, "FORTE": 1.3, "MUITO_FORTE": 1.6}[cfg.get("forca_concorrentes", "MEDIA")]
    estrutura = cfg.get("estrutura_mercado", "FRAGMENTADO")
    concentracao = (1.5 if indice == 0 else .5) if estrutura == "MONOPOLIO" else (1.2 if indice < 3 else .8) if estrutura == "OLIGOPOLIO" else 1
    return nivel * forca * concentracao


def _mercado(preparos, decisoes, turma, rodada, multiplicador):
    cfg = config(turma)
    temporal = adaptar({"configuracao_simulacao":cfg,"demanda_base_por_empresa":turma.demanda_base_por_empresa}, rodada)
    cal = temporal.get("_calendario")
    from ..mercado_pac import demanda_por_loja
    pac = demanda_por_loja(turma, [d.plano_comercial for d in decisoes], cal["fator_mensal"] if cal else 1.0)
    if pac:
        # Catálogo fixo (opção B): o mercado é medido em reais.
        temporal["demanda_base_por_empresa"] = pac["receita"] * pac["fator_periodo"]
        for p in preparos:
            p.setdefault("parametros", {})["mercado_em_reais"] = True
            p["parametros"]["mercado_pac"] = {k: pac[k] for k in ("receita", "atividade_pac", "fator_pmc", "periodo_pmc", "aviso")}
    bots = []
    for i in range(cfg["concorrentes_virtuais"]):
        # Política pública, determinística: não lê as decisões privadas dos alunos.
        preco = turma.preco_referencia * (0.9 + .05 * (i % 5))
        if pac:
            from .portfolio import atratividade_concorrente_catalogo, contexto_guardado
            atratividade_bot = atratividade_concorrente_catalogo(0.9 + .05 * (i % 5), forca_concorrente(cfg, i),
                                                                 contexto_guardado(turma, rodada))
        else:
            atratividade_bot = atrativo_porter(2.5 + .12 * (i % 4), 2.0 + .08 * (rodada - 1), preco, turma.preco_referencia) * forca_concorrente(cfg, i)
        bots.append({"empresa": f"Concorrente virtual {i + 1}", "virtual": True, "preco": preco,
                     "atratividade": atratividade_bot,
                     "capacidade": temporal["demanda_base_por_empresa"]})
    precos = [d.preco for d in decisoes] + [b["preco"] for b in bots]
    media = sum(precos) / len(precos)
    crescimento_acumulado = sum(periodo(cfg, n)["fator_mensal"] for n in range(cfg.get("rodada_inicio_calendario",1), rodada)) if cal else rodada-1
    if pac:
        # Mercado = loja pequena × lojas na disputa (equipes + concorrentes) ×
        # sazonalidade; o crescimento sem fonte dá lugar à atualização pela PMC.
        total = (temporal["demanda_base_por_empresa"] * (len(preparos) + len(bots))
                 * multiplicador * (cal["sazonalidade"]["demanda"] if cal else 1))
    else:
        total = (temporal["demanda_base_por_empresa"] * len(preparos)
                 * (1 + turma.crescimento_mercado_mensal) ** crescimento_acumulado
                 * multiplicador * (cal["sazonalidade"]["demanda"] if cal else 1))
    # Uma empresa sem produto publicado ou sem ativação comercial não disputa
    # demanda. A fatia que ela deixaria de atender migra para concorrentes.
    atrativos = [max(.001, p["atratividade"]) if p.get("comercial_ativo") else 0.0 for p in preparos] + [b["atratividade"] for b in bots]
    soma = sum(atrativos)
    if pac and pac.get("setor"):
        # Canal de venda (opção A, 23/11/2026): toda loja disputa a parte vendida
        # em lojas; só quem vende pela internet (e os concorrentes simulados)
        # disputa a parte da internet (PAC 2023, tabela 9349). Sem fator de
        # canal na atratividade (Levy; Grewal, 2026, cap. 3 e 4, não dão número).
        from ..mercado_pac import participacao_canais
        partes = participacao_canais(pac["setor"])
        online = [1.0 if p.get("canal") == "DIGITAL" else 0.0 for p in preparos] + [1.0 for _ in bots]
        soma_online = sum(a * o for a, o in zip(atrativos, online))
        lojas = [total * partes["loja"] * atr / soma if atr > 0 else 0.0 for atr in atrativos]
        internet = [total * partes["internet"] * atr * o / soma_online if atr > 0 and o and soma_online else 0.0
                    for atr, o in zip(atrativos, online)]
        demandas = [a + b for a, b in zip(lojas, internet)]
        for p, d_loja, d_net in zip(preparos, lojas, internet):
            p["parametros"]["canais_venda"] = {
                "vende_internet": p.get("canal") == "DIGITAL", "demanda_loja": round(d_loja, 2),
                "demanda_internet": round(d_net, 2),
                "fracao_internet": d_net / (d_loja + d_net) if d_loja + d_net else 0.0,
                "parte_internet_mercado": partes["internet_pac"], "fonte": partes["fonte"], "aviso": partes["aviso"]}
    else:
        demandas = [total * atr / soma if atr > 0 else 0.0 for atr in atrativos]
    if pac and pac.get("setor"):
        _mercado_banho_tosa(preparos, decisoes, bots, pac, temporal, total / max(1e-9, temporal["demanda_base_por_empresa"] * (len(preparos) + len(bots))))
    for bot, demanda in zip(bots, demandas[len(preparos):]):
        if pac:
            bot["receita"] = round(min(bot["capacidade"], demanda), 2)
            bot["unidades_vendidas"] = 0.0  # concorrente simulado medido em valor
        else:
            bot["unidades_vendidas"] = min(bot["capacidade"], demanda)
    # O fator de conversão é aplicado uma única vez depois da disputa.
    # Assim não desaparece quando há somente uma empresa no mercado.
    return [demanda * p["avaliacao_estrategica"]["fator"] for demanda, p in zip(demandas, preparos)], bots


def _mercado_banho_tosa(preparos, decisoes, bots, pac, temporal, ajuste):
    """Banho e tosa (setor pet, 23/11/2026). Mercado do serviço = mercado de
    mercadorias da loja × razão serviços gerais ÷ mercadorias de pet shop
    (Abempet, 2025), pelo mesmo número de lojas, sazonalidade e eventos
    (``ajuste``). Disputam as equipes que oferecem o serviço e os concorrentes
    simulados, pela atratividade de preço do serviço (mesma forma da loja)."""
    from ..banho_tosa import RAZAO_SERVICO, atratividade, setor_tem_servico, fontes
    if not setor_tem_servico(pac.get("setor")):
        return
    from .portfolio import fator_propaganda
    total = temporal["demanda_base_por_empresa"] * (len(preparos) + len(bots)) * ajuste * RAZAO_SERVICO
    atr = []
    for p, d in zip(preparos, decisoes):
        plano = d.plano_comercial or {}
        if not (plano.get("banho_tosa") or {}).get("oferece"):
            atr.append(0.0)
            continue
        prop = (p.get("parametros") or {}).get("propaganda") or {}
        estoques = list((prop.get("estoques") or {}).values())
        fator = fator_propaganda(sum(estoques) / len(estoques), prop) if estoques else 1.0
        atr.append(max(.001, atratividade(plano, fator)))
    atr_bots = [b["atratividade"] for b in bots]
    soma = sum(atr) + sum(atr_bots)
    for p, a in zip(preparos, atr):
        if a > 0:
            p["parametros"]["banho_tosa_mercado"] = {
                "demanda_reais": round(total * a / soma, 2) if soma else 0.0,
                "mercado_total": round(total, 2), "lojas_com_servico": sum(1 for x in atr if x > 0) + len(bots),
                "razao_servico": RAZAO_SERVICO, "fonte": fontes()["mercado"], "aviso": fontes()["aviso"]}
    for b, a in zip(bots, atr_bots):
        b["receita_servicos"] = round(total * a / soma, 2) if soma else 0.0


def _transferir_ruptura(turma, preparos, demandas, bots):
    """Clientes que vão a outra loja quando falta o produto (Corsten e Gruen,
    2003: 31% nos itens de consumo do pet). Uma apuração prévia, sem tributos,
    mede a falta de cada loja; os clientes que trocam de loja procuram o mesmo
    produto e se dividem pela atratividade das lojas que o vendem (equipes e
    concorrentes simulados). Quem não encontra de novo desiste (sem cascata)."""
    from .portfolio import dividir
    apurar = motor(turma).apurar
    previas = [apurar(p, demanda, lambda receita, cmv, servicos=0.0: (0.0, 0.0)) for p, demanda in zip(preparos, demandas)]
    extras = [dict() for _ in preparos]
    for i, previa in enumerate(previas):
        itens_origem = {item["produto_id"]: item for item in
                        ((preparos[i]["decisao"].get("plano_comercial") or {}).get("produtos") or [])}
        for pid, unidades in (previa.get("transferencias_ruptura") or {}).items():
            destinos = []
            for j, p in enumerate(preparos):
                vende = any(item["produto_id"] == pid for item in
                            ((p["decisao"].get("plano_comercial") or {}).get("produtos") or []))
                if j != i and vende and p.get("comercial_ativo"):
                    destinos.append(("equipe", j, max(.001, p["atratividade"])))
            destinos += [("bot", k, b["atratividade"]) for k, b in enumerate(bots)]
            if not destinos:
                continue
            partes = dividir(unidades, [peso for *_, peso in destinos])
            preco_mercado = float(itens_origem.get(pid, {}).get("preco_mercado") or 0)
            for (tipo, indice, _), qtd in zip(destinos, partes):
                if not qtd:
                    continue
                if tipo == "equipe":
                    extras[indice][pid] = extras[indice].get(pid, 0) + qtd
                else:
                    bot = bots[indice]
                    razao = bot["preco"] / turma.preco_referencia if turma.preco_referencia else 1.0
                    valor = qtd * preco_mercado * razao
                    if "receita" in bot:
                        bot["receita"] = round(min(bot["capacidade"], bot["receita"] + valor), 2)
                    bot["clientes_recebidos_ruptura"] = bot.get("clientes_recebidos_ruptura", 0) + qtd
    for p, extra in zip(preparos, extras):
        if extra:
            p["parametros"]["demanda_transferida"] = extra


def processar_empresas(db, turma, empresas, rodada, evento, multiplicador_demanda, multiplicador_custo):
    from .simulacao import decisao_vigente, _aplicar_mudanca_regime, _Calculo, _limitar
    from . import eventos as ev
    decisoes, preparos = [], []
    vigentes = {empresa.id: decisao_vigente(db, empresa, rodada, turma) for empresa in empresas}
    if turma.modo_jogo != "STARTUP":
        # Estoque de propaganda de todas as lojas da rodada (itens A e C).
        from .portfolio import contexto_propaganda_turma
        contexto_propaganda_turma(turma, rodada, {i: d.plano_comercial for i, d in vigentes.items()}, guardar=True)
    for empresa in empresas:
        d = vigentes[empresa.id]
        calendario = periodo(config(turma), rodada)
        anterior_calendario = periodo(config(turma), rodada-1) if calendario and rodada>1 else None
        if (calendario and anterior_calendario and calendario["ano_fiscal"] != anterior_calendario["ano_fiscal"]) or (not calendario and rodada > 1 and (rodada - 1) % 12 == 0):
            empresa.faturamento_ano = 0
            empresa.das_mei_pago_ano = 0
        c = _Calculo(empresa, d)
        if turma.modo_jogo == "TRADICIONAL":
            _aplicar_mudanca_regime(empresa, d, turma, c)
            from .regras_mei import regras_mei
            limite_empregados = regras_mei(turma, rodada)["limite_empregados"]
            # Tosadores do banho e tosa também são empregados (23/11/2026).
            tosadores = int((((d.plano_comercial or {}).get("banho_tosa") or {}).get("tosadores") or 0)
                            if ((d.plano_comercial or {}).get("banho_tosa") or {}).get("oferece") else 0)
            if empresa.regime_tributario == RegimeTributario.MEI and empresa.funcionarios + d.contratar - d.demitir + tosadores > limite_empregados:
                empresa.regime_tributario = RegimeTributario.SIMPLES_NACIONAL
                c.alertas.append(f"Mais de {limite_empregados} empregado(s): migração do MEI para o Simples Nacional.")
        empresa.networking = _limitar(empresa.networking - 1 + 2 * math.sqrt(max(0, d.networking) / 500))
        multa = ev.MULTA_NOTIFICACAO_FISCAL if evento.contem("NOTIFICACAO_FISCAL") and empresa.networking < ev.NETWORKING_MINIMO_DEFESA_FISCAL else 0
        from .eventos_operacionais import efeitos_ativos
        efeitos, ocorrencias = efeitos_ativos(db, empresa.id, rodada)
        p = preparar(empresa, d, turma, multiplicador_custo * efeitos["cmv"], multa, efeitos)
        p["ocorrencias_operacionais"] = ocorrencias
        if ocorrencias:
            nomes = ", ".join(o.titulo for o in ocorrencias)
            p["alertas"].append(f"Ocorrências operacionais ativas: {nomes}.")
        p["alertas"].extend(c.alertas)
        if d.automatica:
            p["alertas"].append("Decisão automática: ações pontuais não foram repetidas.")
        decisoes.append(d)
        preparos.append(p)
    demandas, bots = _mercado(preparos, decisoes, turma, rodada, multiplicador_demanda)
    demandas = [demanda * p["parametros"].get("eventos_operacionais", {}).get("demanda", 1.0)
                for demanda, p in zip(demandas, preparos)]
    if turma.modo_jogo != "STARTUP" and any(p.get("parametros", {}).get("mercado_em_reais") for p in preparos):
        _transferir_ruptura(turma, preparos, demandas, bots)
    apuracoes = []
    for empresa, p, demanda in zip(empresas, preparos, demandas):
        apuracoes.append(motor(turma).apurar(p, demanda,
                        lambda receita, cmv, servicos=0.0, e=empresa, alertas=p["alertas"]: _tributar(e, turma, receita, cmv, alertas, servicos)))
    em_reais = any(p.get("parametros", {}).get("mercado_em_reais") for p in preparos)
    if em_reais:
        # Participação em valor (Cooper e Nakanishi, eq. 2.1: "dollar volume").
        # Banho e tosa fica fora da participação de mercado (mercadorias).
        medida = [a["dre"]["receita"] - float(((a["detalhes"].get("operacao") or {}).get("banho_tosa") or {}).get("receita", 0))
                  for a in apuracoes]
        total_vendas = sum(medida) + sum(b.get("receita", 0) for b in bots)
        for bot in bots:
            bot["participacao_mercado"] = bot.get("receita", 0) / total_vendas if total_vendas else 0
    else:
        medida = [a["vendas"] for a in apuracoes]
        total_vendas = sum(medida) + sum(b["unidades_vendidas"] for b in bots)
        for bot in bots:
            bot["participacao_mercado"] = bot["unidades_vendidas"] / total_vendas if total_vendas else 0
    for bot in bots:
        bot.pop("atratividade")
        bot.pop("capacidade")
    from ..atualizacoes_oficiais import consultar as consultar_fontes
    fontes_da_rodada = consultar_fontes(db)
    for empresa, d, a, demanda, preparo in zip(empresas, decisoes, apuracoes, demandas, preparos):
        empresa.estado_simulacao = deepcopy(a["estado"])
        empresa.caixa, empresa.divida, empresa.funcionarios = a["caixa"], a["divida"], a["funcionarios"]
        empresa.marca = a.get("marca", empresa.marca)
        empresa.qualidade = a.get("qualidade", empresa.qualidade)
        dre = a["dre"]
        empresa.faturamento_ano += dre["receita"]
        empresa.autoeficacia = _limitar(empresa.autoeficacia + (4 if dre["lucro_liquido"] > 0 else -6) - (10 if empresa.caixa < 0 else 0))
        anterior = empresa.resultados[-1] if empresa.resultados else None
        if anterior:
            empresa.necessidade_realizacao = _limitar(empresa.necessidade_realizacao + (3 if dre["receita"] > anterior.receita else -2))
        empresa.fase_atual = (FaseAtual.SOBREVIVENCIA if empresa.caixa < dre["custos_fixos"] + dre["folha"] else
                              FaseAtual.CAPTACAO if empresa.divida > 0 else
                              FaseAtual.OPERACAO_ESTAVEL if dre["lucro_liquido"] > 0 else FaseAtual.PLANEJAMENTO)
        detalhes = deepcopy(a["detalhes"])
        if calendario:
            detalhes["calendario"] = deepcopy(calendario)
            from .regras_mei import regras_mei
            detalhes["regras_mei"] = regras_mei(turma, rodada)
            detalhes["engine_version"] = VERSAO_SEMANAL
        detalhes["avaliacao_estrategica"] = deepcopy(preparo["avaliacao_estrategica"])
        detalhes.update(parametros=parametros(turma), decisao=colunas(d), dre=deepcopy(dre),
                        concorrentes_virtuais=deepcopy(bots), evento=evento.codigo, eventos=list(evento.codigos or (evento.codigo,)))
        detalhes["eventos_operacionais"] = [
            {"id": o.id, "codigo": o.codigo, "departamento": o.departamento, "titulo": o.titulo,
             "narrativa": o.narrativa, "rodada_inicio": o.rodada_inicio, "rodada_fim": o.rodada_fim,
             "probabilidade_base": o.probabilidade_base, "probabilidade_aplicada": o.probabilidade_aplicada,
             "fatores": deepcopy(o.fatores), "impacto": deepcopy(o.impacto)}
            for o in preparo.get("ocorrencias_operacionais", [])
        ]
        from .metricas_semanais import gerar_metricas
        detalhes['metricas_semanais'] = gerar_metricas(a, (calendario or {}).get('dias', 30))
        detalhes['atualizacoes_oficiais'] = deepcopy(fontes_da_rodada)
        # Datas ORM não são valores JSON das fotografias.
        detalhes["parametros"].pop("criado_em", None)
        detalhes["decisao"].pop("enviada_em", None)
        db.add(Resultado(empresa_id=empresa.id, rodada=rodada, preco=d.preco,
                        demanda=demanda, capacidade=a["capacidade"], unidades_vendidas=a["vendas"],
                        participacao_mercado=(medida[empresas.index(empresa)] if em_reais else a["vendas"]) / total_vendas if total_vendas else 0,
                        receita=dre["receita"], impostos=dre["impostos"], cmv=dre["cmv"], folha=dre["folha"],
                        custos_fixos=dre["custos_fixos"], marketing=dre["marketing"], pd=dre["pd"],
                        networking_invest=dre["networking"], rescisoes=dre["rescisoes"], royalties=dre["royalties"],
                        juros=dre["juros"], multas=dre["multas"], lucro_liquido=dre["lucro_liquido"],
                        caixa_final=empresa.caixa, divida_final=empresa.divida, regime=empresa.regime_tributario,
                        aliquota_efetiva=a["aliquota"], funcionarios=empresa.funcionarios,
                        marca=empresa.marca, qualidade=empresa.qualidade, autoeficacia=empresa.autoeficacia,
                        networking=empresa.networking, necessidade_realizacao=empresa.necessidade_realizacao,
                        fase=empresa.fase_atual, alertas=a["alertas"], detalhes_simulacao=detalhes))


def patrimonio(empresa):
    estado = empresa.estado_simulacao
    if not estado:
        return empresa.caixa - empresa.divida
    estoque = sum(estado.get(k, {}).get("valor", 0) for k in ("estoque_mp", "estoque_pa", "estoque_obsoleto"))
    receber = sum(t["valor"] for t in estado.get("receber", []))
    pagar = sum(t["valor"] for t in estado.get("pagar", []))
    ativos = sum(m["valor_liquido"] for m in estado.get("maquinas", []))
    return round(empresa.caixa + estoque + receber + ativos - pagar - empresa.divida, 2)
