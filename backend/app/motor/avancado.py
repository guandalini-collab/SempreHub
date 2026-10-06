"""Integração dos motores didáticos v1 e snapshots históricos, sem mudar o legado."""
from copy import deepcopy
from enum import Enum
import math

from ..models import Empresa, Resultado, RegimeTributario, FaseAtual
from ..schemas import ConfiguracaoSimulacao, DecisaoSimulacao
from .tributos import calcular_imposto, aliquota_efetiva_simples, TOLERANCIA_TETO_MEI


def config(turma):
    return ConfiguracaoSimulacao.model_validate(turma.configuracao_simulacao or {}).model_dump()


def estado_inicial(turma):
    cfg = config(turma)
    crise = turma.cenario == "CRISE"
    tradicional = turma.modo_jogo == "TRADICIONAL"
    custo = turma.custo_unitario
    return {
        "versao": 1,
        "estoque_mp": {"quantidade": 100 if crise and tradicional else 0, "valor": 100 * custo if crise and tradicional else 0},
        "estoque_pa": {"quantidade": 100 if crise and tradicional else 0, "valor": 100 * custo if crise and tradicional else 0},
        "estoque_obsoleto": {"quantidade": 50 if crise and tradicional else 0, "valor": 0},
        "maquinas": [{"custo": cfg["preco_maquina"], "valor_liquido": cfg["preco_maquina"] * (.5 if crise else 1),
                       "capacidade": cfg["capacidade_maquina"], "condicao": .55 if crise else 1,
                       "ativacao": 1, "vida_util": cfg["vida_util_maquina"]}] if tradicional else [],
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
    dados["configuracao_simulacao"] = config(turma)
    return dados


def motor(turma):
    from . import tradicional, startup
    return startup if turma.modo_jogo == "STARTUP" else tradicional


def preparar(empresa, decisao, turma, multiplicador_custo=1, multa=0):
    dados = colunas(empresa)
    dados["estado_simulacao"] = dados["estado_simulacao"] or estado_inicial(turma)
    if turma.modo_jogo=="TRADICIONAL":
        anteriores=[d for d in empresa.decisoes if d.rodada<turma.rodada_atual and d.plano_comercial]
        original=anteriores[-1].plano_comercial["produto_id"] if anteriores else (decisao.plano_comercial or {}).get("produto_id")
        if original: dados["estado_simulacao"].setdefault("produto_estoque_original",original)
    entrada = colunas(decisao)
    entrada["simulacao"] = DecisaoSimulacao.model_validate(entrada["simulacao"] or {}).model_dump()
    p = parametros(turma)
    p["custo_referencia_portfolio"]=turma.custo_unitario
    if decisao.plano_comercial:
        p["custo_unitario"] = decisao.plano_comercial["custo_unitario"]
        if turma.modo_jogo == "STARTUP":
            p["configuracao_simulacao"]["custo_nuvem_cliente"] = decisao.plano_comercial["custo_unitario"]
    p["multa_evento"] = multa
    p["multas"] = multa
    preparo = motor(turma).preparar(dados, entrada, p, turma.rodada_atual, multiplicador_custo)
    itens=(decisao.plano_comercial or {}).get("produtos", [])
    if itens:
        from .portfolio import atrativos
        base=(turma.preco_referencia/decisao.preco)**(1.4 if turma.modo_jogo=="STARTUP" else 2)
        preparo["atratividade"]*=sum(atrativos(itens,turma.preco_referencia,turma.custo_unitario,empresa.marca,empresa.qualidade))/sum(i["peso"] for i in itens)/base
    from .estrategia import avaliar, mensagens
    avaliacao = avaliar(decisao, turma)
    preparo["avaliacao_estrategica"] = avaliacao
    preparo["alertas"].extend(mensagens(avaliacao))
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
        producao = calculo.get("producao_planejada", 0)
    else:
        margem = decisao.preco - (decisao.plano_comercial or {}).get("custo_unitario", config(turma)["custo_nuvem_cliente"])
        producao = calculo.get("clientes_adquiridos", 0)
    gastos = calculo.get("gastos_previstos", 0)
    return {
        "rodada": turma.rodada_atual, "regime": empresa.regime_tributario.value,
        "funcionarios": calculo["funcionarios"], "capacidade": calculo["capacidade"],
        "folha": calculo.get("folha", 0), "juros": calculo.get("juros", 0),
        "gastos_previstos": gastos, "margem_unitaria": margem,
        "ponto_equilibrio": gastos / margem if margem > 0 else None,
        "emprestimo_aprovado": calculo.get("emprestimo", 0),
        "amortizacao_aplicada": calculo.get("amortizacao", 0),
        "divida_prevista": empresa.divida + calculo.get("emprestimo", 0) - calculo.get("amortizacao", 0),
        "caixa_disponivel": empresa.caixa + calculo.get("emprestimo", 0) - calculo.get("amortizacao", 0),
        "alertas": calculo.get("alertas", []),
        "simulacao": {"estado": deepcopy(calculo.get("estado", {})), "producao": producao,
                       **(localizacao if turma.modo_jogo == "TRADICIONAL" else {}),
                       "avaliacao_estrategica": calculo["avaliacao_estrategica"],
                       "aviso": "Estimativa sem vendas: demanda e eventos da próxima rodada ainda são desconhecidos."},
    }


def _tributar(empresa, turma, receita, cmv, alertas):
    regime = empresa.regime_tributario
    impostos, aliquota = calcular_imposto(regime, receita, cmv, [r.receita for r in empresa.resultados],
                                         turma.das_mei_mensal, turma.aliquota_icms)
    acumulado = empresa.faturamento_ano + receita
    if regime == RegimeTributario.MEI:
        empresa.das_mei_pago_ano += impostos
        teto = turma.teto_mei_anual
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
    bots = []
    for i in range(cfg["concorrentes_virtuais"]):
        # Política pública, determinística: não lê as decisões privadas dos alunos.
        preco = turma.preco_referencia * (0.9 + .05 * (i % 5))
        bots.append({"empresa": f"Concorrente virtual {i + 1}", "virtual": True, "preco": preco,
                     "atratividade": (turma.preco_referencia / preco) ** 2 * (1 + .02 * (rodada - 1)) * forca_concorrente(cfg, i),
                     "capacidade": turma.demanda_base_por_empresa})
    precos = [d.preco for d in decisoes] + [b["preco"] for b in bots]
    media = sum(precos) / len(precos)
    total = (turma.demanda_base_por_empresa * len(preparos)
             * (1 + turma.crescimento_mercado_mensal) ** (rodada - 1)
             * (turma.preco_referencia / media) ** .8 * multiplicador)
    atrativos = [max(.001, p["atratividade"]) for p in preparos] + [b["atratividade"] for b in bots]
    soma = sum(atrativos)
    demandas = [total * atr / soma for atr in atrativos]
    for bot, demanda in zip(bots, demandas[len(preparos):]):
        bot["unidades_vendidas"] = min(bot["capacidade"], demanda)
    # O fator de conversão é aplicado uma única vez depois da disputa.
    # Assim não desaparece quando há somente uma empresa no mercado.
    return [demanda * p["avaliacao_estrategica"]["fator"] for demanda, p in zip(demandas, preparos)], bots


def processar_empresas(db, turma, empresas, rodada, evento, multiplicador_demanda, multiplicador_custo):
    from .simulacao import decisao_vigente, _aplicar_mudanca_regime, _Calculo, _limitar
    from . import eventos as ev
    decisoes, preparos = [], []
    for empresa in empresas:
        d = decisao_vigente(db, empresa, rodada, turma)
        if rodada > 1 and (rodada - 1) % 12 == 0:
            empresa.faturamento_ano = 0
            empresa.das_mei_pago_ano = 0
        c = _Calculo(empresa, d)
        if turma.modo_jogo == "TRADICIONAL":
            _aplicar_mudanca_regime(empresa, d, turma, c)
            if empresa.regime_tributario == RegimeTributario.MEI and empresa.funcionarios + d.contratar - d.demitir > 1:
                empresa.regime_tributario = RegimeTributario.SIMPLES_NACIONAL
                c.alertas.append("Mais de um empregado: migração do MEI para o Simples Nacional.")
        empresa.networking = _limitar(empresa.networking - 1 + 2 * math.sqrt(max(0, d.networking) / 500))
        multa = ev.MULTA_NOTIFICACAO_FISCAL if evento.codigo == "NOTIFICACAO_FISCAL" and empresa.networking < ev.NETWORKING_MINIMO_DEFESA_FISCAL else 0
        p = preparar(empresa, d, turma, multiplicador_custo, multa)
        p["alertas"].extend(c.alertas)
        if d.automatica:
            p["alertas"].append("Decisão automática: ações pontuais não foram repetidas.")
        decisoes.append(d)
        preparos.append(p)
    demandas, bots = _mercado(preparos, decisoes, turma, rodada, multiplicador_demanda)
    apuracoes = []
    for empresa, p, demanda in zip(empresas, preparos, demandas):
        apuracoes.append(motor(turma).apurar(p, demanda,
                        lambda receita, cmv, e=empresa, alertas=p["alertas"]: _tributar(e, turma, receita, cmv, alertas)))
    total_vendas = sum(a["vendas"] for a in apuracoes) + sum(b["unidades_vendidas"] for b in bots)
    for bot in bots:
        bot["participacao_mercado"] = bot["unidades_vendidas"] / total_vendas if total_vendas else 0
        bot.pop("atratividade")
        bot.pop("capacidade")
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
        empresa.fase_atual = (FaseAtual.SOBREVIVENCIA if empresa.caixa < turma.custos_fixos_mensais + dre["folha"] else
                              FaseAtual.CAPTACAO if empresa.divida > 0 else
                              FaseAtual.OPERACAO_ESTAVEL if dre["lucro_liquido"] > 0 else FaseAtual.PLANEJAMENTO)
        detalhes = deepcopy(a["detalhes"])
        detalhes["avaliacao_estrategica"] = deepcopy(preparo["avaliacao_estrategica"])
        detalhes.update(parametros=parametros(turma), decisao=colunas(d), dre=deepcopy(dre),
                        concorrentes_virtuais=deepcopy(bots), evento=evento.codigo)
        # Datas ORM não são valores JSON das fotografias.
        detalhes["parametros"].pop("criado_em", None)
        detalhes["decisao"].pop("enviada_em", None)
        db.add(Resultado(empresa_id=empresa.id, rodada=rodada, preco=d.preco,
                        demanda=demanda, capacidade=a["capacidade"], unidades_vendidas=a["vendas"],
                        participacao_mercado=a["vendas"] / total_vendas if total_vendas else 0,
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
