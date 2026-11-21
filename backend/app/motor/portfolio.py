"""Portfólio: capacidade compartilhada, estoques separados e valores conciliados."""
from copy import deepcopy
from decimal import Decimal, ROUND_HALF_UP
import math


def dinheiro(v):
    return float(Decimal(str(v)).quantize(Decimal('.01'), rounding=ROUND_HALF_UP))


def dividir(total, pesos):
    """Maiores restos; preserva exatamente a quantidade inteira disponível."""
    total=max(0,int(total)); soma=sum(pesos)
    if not soma: return [0]*len(pesos)
    exatos=[total*p/soma for p in pesos]; partes=[math.floor(x) for x in exatos]
    for i in sorted(range(len(pesos)), key=lambda i:(exatos[i]-partes[i],-i), reverse=True)[:total-sum(partes)]: partes[i]+=1
    return partes


def limitar_por_capacidade(producao, fatores, limite):
    """Limita unidades pela capacidade operacional exigida por cada linha.

    Uma linha complexa pode consumir mais tempo de máquina e operação por
    unidade. Esse fator ainda não é o custo de ativação nem o tempo único de
    setup: ambos serão tratados pela lógica financeira/operacional própria.
    """
    limite = max(0.0, float(limite))
    fatores = [max(0.01, float(fator)) for fator in fatores]
    necessario = sum(unidades * fator for unidades, fator in zip(producao, fatores))
    if necessario <= limite:
        return list(producao)
    if limite <= 0 or necessario <= 0:
        return [0] * len(producao)

    escala = limite / necessario
    alocadas = [min(unidades, math.floor(unidades * escala)) for unidades in producao]
    restante = limite - sum(unidades * fator for unidades, fator in zip(alocadas, fatores))
    ordem = sorted(
        range(len(producao)),
        key=lambda indice: ((producao[indice] * escala) - alocadas[indice], -indice),
        reverse=True,
    )
    while True:
        candidatos = [
            indice for indice in ordem
            if alocadas[indice] < producao[indice] and fatores[indice] <= restante + 1e-12
        ]
        if not candidatos:
            break
        indice = candidatos[0]
        alocadas[indice] += 1
        restante -= fatores[indice]
    return alocadas


def diagnostico_midia(item):
    """Mede a parcela de mídia que realmente conversa com a linha do produto.

    A despesa total nunca é reduzida aqui: contratar o canal errado continua
    consumindo caixa e aparecendo na DRE. A aderência só determina quanto da
    verba de veiculação pode gerar atração/demanda.
    """
    from ..catalogo_campanhas import CAMPANHAS
    tarifas = {identificador: valor for identificador, _nome, _categoria, valor, _unidade in CAMPANHAS}
    recomendadas = set(item.get("midias_recomendadas") or [])
    selecionadas = item.get("midias") or []
    total = sum(tarifas.get(m.get("id"), 0) * max(0, float(m.get("quantidade", 0))) for m in selecionadas)
    compativel = sum(tarifas.get(m.get("id"), 0) * max(0, float(m.get("quantidade", 0)))
                     for m in selecionadas if m.get("id") in recomendadas)
    # Catálogos históricos sem ficha setorial preservam o comportamento que
    # tinham quando foram gravados. Nas novas rodadas, ausência de mídia
    # compatível significa campanha sem efeito comercial.
    aderencia = 1.0 if not recomendadas else (compativel / total if total > 0 else 0.0)
    return {
        "investimento_veiculacao": dinheiro(total),
        "investimento_compativel": dinheiro(compativel),
        "investimento_incompativel": dinheiro(max(0, total - compativel)),
        "aderencia": max(0.0, min(1.0, aderencia)),
    }


def _como_dict(valor):
    """Aceita snapshots persistidos e objetos de validação, sem acoplar o motor ao ORM."""
    if valor is None:
        return {}
    if hasattr(valor, "model_dump"):
        return valor.model_dump()
    return valor if isinstance(valor, dict) else {}


def diagnostico_segmentacao(item, segmentacao=None):
    """Mede se produto, preço, praça e comunicação alcançam o público declarado.

    A segmentação não é decorativa: um preço acima do teto declarado inviabiliza
    a compra; canal, cobertura e mídia inadequados reduzem a eficiência da
    demanda. Snapshots legados sem segmentação permanecem neutros para que o
    passado não seja recalculado por regras novas.
    """
    alvo = _como_dict(segmentacao)
    if not alvo:
        return {"fator": 1.0, "status": "sem_segmentacao_estruturada", "avisos": []}

    avisos = []
    fator = 1.0
    preco_maximo = alvo.get("preco_maximo")
    preco = float(item.get("preco", 0) or 0)
    catalogo = bool(item.get("preco_mercado"))
    if catalogo and preco_maximo is not None and preco > float(preco_maximo):
        avisos.append("Preço acima do limite de compra declarado para o público-alvo. "
                      "Próximo passo: ajuste o preço ou revise o limite declarado.")
    elif preco_maximo is not None and preco > float(preco_maximo):
        return {
            "fator": 0.0, "status": "preco_acima_do_teto", "preco": preco,
            "preco_maximo": float(preco_maximo),
            "avisos": ["Preço acima do teto declarado para o público-alvo; esta linha não gera demanda."],
        }

    canais_alvo = set(alvo.get("canais") or [])
    canais_produto = set(item.get("canais") or [])
    if canais_alvo and canais_produto:
        canais_comuns = canais_alvo & canais_produto
        if not canais_comuns:
            fator *= 0.35
            avisos.append("Os canais escolhidos para o produto não atendem os canais do público-alvo.")
        elif canais_comuns != canais_produto:
            fator *= 0.75
            avisos.append("Apenas parte dos canais do produto alcança o público-alvo.")

    niveis = {"LOCAL": 1, "REGIONAL": 2, "NACIONAL": 3, "INTERNACIONAL": 4}
    cobertura_alvo = alvo.get("cobertura")
    cobertura_produto = item.get("cobertura")
    if cobertura_alvo in niveis and cobertura_produto in niveis:
        excesso = niveis[cobertura_produto] - niveis[cobertura_alvo]
        if excesso == 1:
            fator *= 0.70
            avisos.append("A cobertura comercial é maior que a cobertura definida para o público-alvo.")
        elif excesso >= 2:
            fator *= 0.40
            avisos.append("A cobertura comercial está muito acima do mercado-alvo e dispersa a verba.")

    midias_alvo = set(alvo.get("midias") or [])
    midias_produto = {m.get("id") for m in item.get("midias") or [] if m.get("id")}
    if midias_alvo and midias_produto and not (midias_alvo & midias_produto):
        fator *= 0.50
        avisos.append("As mídias escolhidas não coincidem com os canais declarados para o público-alvo.")

    if catalogo:
        # Item 2d (18/11/2026): no catálogo a segmentação declarada é devolutiva,
        # sem efeito na demanda (sem demanda por segmento no modelo).
        fator = 1.0
    return {
        "fator": max(0.0, min(1.0, fator)),
        "status": ("alinhado" if not avisos else "alinhamento_parcial") if not catalogo else ("alinhado" if not avisos else "diagnostico"),
        "preco": preco, "preco_maximo": preco_maximo,
        "canais_produto": sorted(canais_produto), "canais_publico": sorted(canais_alvo),
        "cobertura_produto": cobertura_produto, "cobertura_publico": cobertura_alvo,
        "avisos": avisos,
    }


def diagnosticos_segmentacao(itens, segmentacao=None):
    return {item.get("produto_id"): diagnostico_segmentacao(item, segmentacao) for item in itens}


ELASTICIDADE_PROPAGANDA = 0.12  # Sethuraman, Tellis e Briesch (2011), média de curto prazo
# Persistência (carryover) do efeito da propaganda: Clarke (1976, JMR, Tabela 2),
# coeficiente médio da variável dependente defasada por intervalo dos dados.
PERSISTENCIA_PROPAGANDA = {"MENSAL": 0.440, "SEMANAL": 0.537}
DEFASAGENS_PROPAGANDA = 3  # Clarke: 90% do efeito acumulado em cerca de 3 meses


def persistencia_propaganda(periodicidade=None):
    return PERSISTENCIA_PROPAGANDA["SEMANAL" if periodicidade == "SEMANAL" else "MENSAL"]


def veiculacao_por_produto(plano):
    """Veiculação (R$) de cada produto do catálogo fixo em um plano comercial."""
    return {item.get("produto_id"): diagnostico_midia(item)["investimento_veiculacao"]
            for item in ((plano or {}).get("produtos") or []) if item.get("preco_mercado")}


def estoques_propaganda(planos, persistencia):
    """Estoque de propaganda por produto: soma de λ^v × veiculação(t − v).

    ``planos[v]`` é o plano do período t − v (``None`` quando não houve). É a
    forma de defasagens distribuídas de Cooper e Nakanishi (1988, apêndice
    3.10.1) com pesos geométricos (Koyck), como em Clarke (1976).
    """
    estoques = {}
    for v, plano in enumerate(planos[:DEFASAGENS_PROPAGANDA + 1]):
        for pid, valor in veiculacao_por_produto(plano).items():
            estoques[pid] = estoques.get(pid, 0.0) + (persistencia ** v) * valor
    return estoques


def beta_propaganda(concorrentes, persistencia):
    """Coeficiente da forma exponencial (MNL) da propaganda.

    Cooper e Nakanishi (1988, p. 33-36): elasticidade MNL = β(1 − s)X. O β é
    calibrado para que, na empresa média (participação 1/n e estoque igual à
    média do mercado), a elasticidade de curto prazo seja 0,12 (Sethuraman,
    Tellis e Briesch, 2011); o longo prazo resulta 0,12 × Σ λ^v.
    """
    soma = sum(persistencia ** v for v in range(DEFASAGENS_PROPAGANDA + 1))
    return ELASTICIDADE_PROPAGANDA * soma / (1 - 1 / max(2, int(concorrentes)))


def fator_propaganda(estoque, propaganda):
    """exp(β × estoque ÷ estoque médio do mercado); 1 quando ninguém anunciou."""
    media = float((propaganda or {}).get("media") or 0)
    if media <= 0:
        return 1.0
    return math.exp(float(propaganda["beta"]) * max(0.0, float(estoque)) / media)


def contexto_propaganda(estoques_por_empresa, concorrentes, persistencia):
    """Média do estoque de propaganda por produto ofertado no mercado e β."""
    valores = [v for estoques in estoques_por_empresa.values() for v in estoques.values()]
    return {"media": sum(valores) / len(valores) if valores else 0.0,
            "beta": beta_propaganda(concorrentes, persistencia), "persistencia": persistencia,
            "estoques_por_empresa": estoques_por_empresa}


def propaganda_para(turma, rodada, empresa, plano_corrente):
    """Propaganda de uma empresa: do fechamento (contexto guardado) ou da prévia."""
    if turma.modo_jogo == "STARTUP":
        return None
    cache = getattr(turma, "_contexto_propaganda", None)
    if cache and cache[0] == rodada:
        contexto = cache[1]
    else:
        contexto = contexto_propaganda_turma(turma, rodada, {empresa.id: plano_corrente})
    return propaganda_da_empresa(contexto, empresa.id)


def contexto_propaganda_turma(turma, rodada, planos_correntes=None, guardar=False):
    """Contexto da propaganda da rodada para turmas com catálogo fixo.

    No fechamento, ``planos_correntes`` traz as decisões vigentes de todas as
    empresas. Na prévia de uma equipe, as demais entram com o último plano
    enviado, a mesma regra que o jogo aplica a quem não envia decisão.
    """
    cache = getattr(turma, "_contexto_propaganda", None)
    if cache and cache[0] == rodada and not guardar:
        return cache[1]
    cfg = turma.configuracao_simulacao or {}
    persistencia = persistencia_propaganda(cfg.get("periodicidade"))
    estoques = {}
    for empresa in turma.empresas:
        por_rodada = {d.rodada: d.plano_comercial for d in empresa.decisoes
                      if d.rodada < rodada and d.plano_comercial and (d.enviada_em or d.automatica)}
        if planos_correntes is not None and empresa.id in planos_correntes:
            atual = planos_correntes[empresa.id]
        else:
            atual = por_rodada[max(por_rodada)] if por_rodada else None
        planos = [atual] + [por_rodada.get(rodada - v) for v in range(1, DEFASAGENS_PROPAGANDA + 1)]
        estoques[empresa.id] = estoques_propaganda(planos, persistencia)
    concorrentes = len(turma.empresas) + int(cfg.get("concorrentes_virtuais", 0) or 0)
    contexto = contexto_propaganda(estoques, concorrentes, persistencia)
    if guardar:
        turma._contexto_propaganda = (rodada, contexto)
    return contexto


def propaganda_da_empresa(contexto, empresa_id):
    """Recorte do contexto para uma empresa (serializável, vai nos parâmetros)."""
    if not contexto:
        return None
    estoques = dict(contexto["estoques_por_empresa"].get(empresa_id, {}))
    return {"estoques": estoques, "media": contexto["media"], "beta": contexto["beta"],
            "persistencia": contexto["persistencia"]}


def atratividade_concorrente_catalogo(razao_preco, forca, contexto=None):
    """Concorrente simulado com catálogo fixo (item 2b, 18/11/2026).

    Mesma forma das equipes (Cooper e Nakanishi, 1988, p. 71-73): preço em
    relação ao preço de mercado de cada item elevado à elasticidade e fator de
    propaganda no estoque médio do mercado. ``forca`` é o ajuste do professor,
    interpretado como o intercepto da loja (Briesch; Chintagunta; Fox, 2009).
    """
    from .simulacao import ELASTICIDADE_PRECO_ESCOLHA
    contexto = contexto or {}
    media = float(contexto.get("media") or 0)
    return ((1 / razao_preco) ** ELASTICIDADE_PRECO_ESCOLHA
            * fator_propaganda(media, {"media": media, "beta": contexto.get("beta", 0)}) * forca)


def avisos_posicionamento_catalogo(itens, posicionamento):
    """Item 2c (18/11/2026): Porter (1980, cap. 2) como diagnóstico, sem
    penalidade numérica; compara o preço de cada item com o preço de mercado."""
    acima = [i for i in itens if i.get("preco_mercado") and float(i["preco"]) > float(i["preco_mercado"])]
    abaixo = [i for i in itens if i.get("preco_mercado") and float(i["preco"]) < float(i["preco_mercado"])]
    if posicionamento == "DIFERENCIACAO":
        if abaixo:
            return [f"Porter: posicionamento em diferenciação com preço abaixo do mercado em {len(abaixo)} item(ns). "
                    "Sem diferença percebida, a disputa tende a se dar por preço (risco de meio-termo)."]
        return []
    if acima:
        return [f"Porter: posicionamento em custo com preço acima do mercado em {len(acima)} item(ns). "
                "A liderança em custo pede preços competitivos (risco de meio-termo)."]
    return []


def contexto_guardado(turma, rodada):
    cache = getattr(turma, "_contexto_propaganda", None)
    return cache[1] if cache and cache[0] == rodada else None


def atrativos(itens, referencia, custo_referencia, marca=0, qualidade=0, segmentacao=None, propaganda=None):
    from ..catalogo_campanhas import CAMPANHAS
    custos={i:v for i,n,c,v,u in CAMPANHAS}
    valores=[]
    for p in itens:
        # A API impede preço nulo ou negativo, mas o motor também precisa ser
        # seguro para históricos e simulações diretas. Um produto sem preço
        # comercial não gera atratividade — e jamais pode provocar divisão por
        # zero durante a apuração financeira.
        preco = max(0.0, float(p.get("preco", 0)))
        if preco <= 0:
            valores.append(0.0)
            continue
        ref=referencia*p['custo_unitario']/max(.01,custo_referencia)
        canal=1.1 if 'ATACADO' in p['canais'] else 1.05 if any(c in p['canais'] for c in ('ECOMMERCE','MARKETPLACE')) else 1
        pos=.75 if p['posicionamento']!='PRECO' and marca<3 and qualidade<3 else 1
        diagnostico = diagnostico_midia(p)
        campanha = diagnostico["investimento_compativel"]
        # O orçamento auditável pode incluir serviços obrigatórios. Eles são
        # custo legítimo, mas não transformam uma mídia incompatível em canal
        # eficaz. A veiculação compatível é a única base de atração.
        if not p.get("midias_recomendadas") and (p.get('custos_campanha') or {}).get('versao')==2:
            campanha=p['custos_campanha']['investimento_efetivo']
        if p.get('preco_mercado'):
            # Catálogo fixo (aprovado em 17/11/2026). Propaganda na forma
            # exponencial (MNL), indicada por Cooper e Nakanishi (1988, p. 35-36)
            # por haver efeito limiar: sem veiculação o fator é exp(0) = 1, e a
            # loja segue disputando clientes. O estoque de propaganda soma os
            # últimos meses com persistência λ (Clarke, 1976), medido contra a
            # média do mercado (distintividade, p. 71-74). β calibrado pela
            # elasticidade 0,12 (Sethuraman, Tellis e Briesch, 2011). Todas as
            # mídias têm o mesmo peso por real.
            segmento = diagnostico_segmentacao(p, segmentacao)
            if propaganda is None:
                # Sem contexto de mercado (uso direto): só o mês corrente, contra
                # a média dos próprios produtos do plano.
                estoques_locais = estoques_propaganda([{"produtos": itens}], persistencia_propaganda())
                propaganda = {"estoques": estoques_locais,
                              "media": sum(estoques_locais.values()) / len(estoques_locais) if estoques_locais else 0.0,
                              "beta": beta_propaganda(2, persistencia_propaganda())}
            estoque = (propaganda.get("estoques") or {}).get(p.get("produto_id"), 0.0)
            from .simulacao import ELASTICIDADE_PRECO_ESCOLHA
            valores.append(p['peso']*(float(p['preco_mercado'])/preco)**ELASTICIDADE_PRECO_ESCOLHA
                           *canal*pos*fator_propaganda(estoque, propaganda)*segmento["fator"])
            continue
        # Nas linhas novas não há demanda orgânica. Se a equipe escolheu mídia
        # incompatível (ou não escolheu nenhum canal), a verba aparece como
        # despesa, porém esta linha não disputa consumidores nesta semana.
        if p.get("midias_recomendadas") and (not p.get("midias") or diagnostico["aderencia"] <= 0):
            valores.append(0.0)
            continue
        segmento = diagnostico_segmentacao(p, segmentacao)
        from .simulacao import ELASTICIDADE_PRECO_ESCOLHA
        # Produto do catálogo fixo: a referência é o preço de mercado do item.
        if p.get('preco_mercado'):
            ref = float(p['preco_mercado'])
        valores.append(p['peso']*(ref/preco)**ELASTICIDADE_PRECO_ESCOLHA*canal*pos*(1+math.sqrt(campanha/1000))**.3 * segmento["fator"])
    return valores


def pesos_em_valor(itens, pesos):
    """Converte pesos de atratividade (fatias de receita) em pesos de unidades.

    Cooper e Nakanishi (Market-Share Analysis, cap. 2 e 4): participação pode
    ser medida em valor, e só se somam medidas que "add together sensibly". A
    fatia em reais de cada produto vira unidades pelo preço do próprio produto.
    """
    return [w / max(.01, float(p.get("preco", 0) or 0)) if float(p.get("preco", 0) or 0) > 0 else 0.0
            for p, w in zip(itens, pesos)]


def unidades_da_receita(receita, itens, pesos):
    """Unidades totais correspondentes a uma demanda em reais repartida pelos pesos."""
    soma = sum(pesos)
    return receita * sum(pesos_em_valor(itens, pesos)) / soma if soma else 0.0


def produzir(estado, itens, op, capacidade, maquinas, multiplicador,
             taxas_defeito_linha=None, qualificacao_linha=None):
    estoque=deepcopy(estado.get('estoques_produtos') or {})
    # Estoque histórico anterior ao portfólio pertence ao produto original, nunca é clonado.
    original=estado.get('produto_estoque_original') or itens[0]['produto_id']
    if not estoque:
        estoque[original]={k:deepcopy(estado[k]) for k in ('estoque_mp','estoque_pa')}
    pesos=[p['peso'] for p in itens]
    compras_especificas=op.get('comprar_insumos_por_produto') or {}
    # Uma compra indicada por produto nunca é redistribuída entre linhas.
    # Assim, componentes de notebook não abastecem smartphone, mesmo se ambos
    # pertencem à mesma empresa e têm capacidade de produção disponível.
    compras_un=(
        [max(0, int(compras_especificas.get(p['produto_id'], 0))) for p in itens]
        if compras_especificas else dividir(op.get('comprar_mp',0),pesos)
    )
    pedidas=dividir(op.get('producao',0),pesos)
    disponiveis=[]; compras=0
    for p,un in zip(itens,compras_un):
        st=estoque.setdefault(p['produto_id'],{'estoque_mp':{'quantidade':0,'valor':0},'estoque_pa':{'quantidade':0,'valor':0}})
        valor=dinheiro(un*p['custo_unitario']*multiplicador); compras+=valor
        st['estoque_mp']['quantidade']+=un;st['estoque_mp']['valor']=dinheiro(st['estoque_mp']['valor']+valor)
        disponiveis.append(st['estoque_mp']['quantidade'])
    producao=[min(q,disp) for q,disp in zip(pedidas,disponiveis)]
    limite=max(0,math.floor(capacidade+1e-12))
    fatores_capacidade=[p.get('fator_setup') or 1.0 for p in itens]
    producao=limitar_por_capacidade(producao, fatores_capacidade, limite)
    real=sum(producao); taxa=estado.get("indicadores_didaticos",{}).get("taxa_defeito",.02)
    taxas_defeito_linha = taxas_defeito_linha or {}
    qualificacao_linha = qualificacao_linha or {}
    # A qualidade deixa de ser uma média abstrata da fábrica: cada linha pode
    # sofrer uma taxa própria quando a equipe não possui a qualificação exigida.
    taxas = [max(0.0, min(1.0, float(taxas_defeito_linha.get(p["produto_id"], taxa)))) for p in itens]
    refugos=[min(q, math.floor(q * taxa_linha + 1e-12)) for q, taxa_linha in zip(producao, taxas)]
    perda=0
    for p,q,ref in zip(itens,producao,refugos):
        st=estoque[p['produto_id']];mp=st['estoque_mp'];pa=st['estoque_pa']
        consumido=dinheiro(mp['valor']*q/mp['quantidade']) if mp['quantidade'] else 0
        refugo=dinheiro(consumido*ref/q) if q else 0;perda+=refugo
        mp['quantidade']-=q;mp['valor']=dinheiro(mp['valor']-consumido)
        pa['quantidade']+=q-ref;pa['valor']=dinheiro(pa['valor']+consumido-refugo)
    estado['estoques_produtos']=estoque
    estado['portfolio_producao']=[
        {
            'produto_id': produto['produto_id'],
            'insumo_chave': produto.get('insumo_chave'),
            'insumo_comprado': compra,
            'linha_produto': produto.get('linha_produto'),
            'producao_planejada': planejada,
            'producao_realizada': realizada,
            'fator_capacidade': fator,
            'capacidade_consumida': dinheiro(realizada * fator),
            'taxa_refugo': taxas[indice],
            'qualificacao_compativel': bool(qualificacao_linha.get(produto['produto_id'], {}).get('compativel', True)),
            'motivo_qualificacao': qualificacao_linha.get(produto['produto_id'], {}).get('motivo'),
        }
        for indice, (produto, planejada, realizada, fator, compra) in enumerate(zip(itens, pedidas, producao, fatores_capacidade, compras_un))
    ]
    sincronizar(estado)
    return dinheiro(compras),real,sum(refugos),dinheiro(perda)


def sincronizar(estado):
    for k in ('estoque_mp','estoque_pa'):
        estado[k]={'quantidade':sum(p[k]['quantidade'] for p in estado['estoques_produtos'].values()),'valor':dinheiro(sum(p[k]['valor'] for p in estado['estoques_produtos'].values()))}


# Resposta do consumidor à falta do produto (aprovado em 18/11/2026).
# Itens de consumo do pet: Corsten e Gruen (2003, Figura 2) — substitui na
# mesma loja 45% (19% mesma marca + 26% outra), compra em outra loja 31%,
# adia 15%, desiste 9%. Duráveis: Anderson, Fitzsimons e Simester (2006,
# Tabela 1) — 62% mantêm o pedido e esperam; 32% cancelam e 6% devolvem —,
# com a regra qualitativa de Ballou (2007, p. 280). Vestuário: sem estudo
# lido; a venda continua perdida (lacuna declarada).
RESPOSTA_RUPTURA = {
    "CONSUMO": {"substitui": .45, "outra_loja": .31, "adia": .15, "desiste": .09},
    "DURAVEL": {"adia": .62, "desiste": .38},
}
LINHAS_CONSUMO_PET = {"Alimentação", "Higiene"}


def classe_ruptura(produto_id):
    """CONSUMO, DURAVEL ou None (venda perdida) para um item do catálogo fixo."""
    from ..catalogo_fixo import item as item_catalogo
    ficha = item_catalogo(produto_id)
    if not ficha or ficha["setor"] == "vestuario":
        return None
    if ficha["setor"] == "pet" and ficha["linha"] in LINHAS_CONSUMO_PET:
        return "CONSUMO"
    return "DURAVEL"


def linha_catalogo(produto_id):
    from ..catalogo_fixo import item as item_catalogo
    ficha = item_catalogo(produto_id)
    return (ficha["setor"], ficha["linha"]) if ficha else None


def vender_com_ruptura(estado, itens, demanda, pesos, diagnosticos_publico=None,
                       pendentes=None, transferidas=None, limite_extra=None):
    """Venda do catálogo com pedidos pendentes, demanda vinda de outras lojas e
    resposta à falta. Prioridade no estoque: pendentes, clientes do mês e, por
    último, clientes vindos de outras lojas. Pendente não atendido de novo e
    cliente transferido não atendido são perdidos (sem cascata)."""
    pendentes = {k: int(v) for k, v in (pendentes or {}).items() if v}
    transferidas = {k: int(v) for k, v in (transferidas or {}).items() if v}
    ids = {p['produto_id'] for p in itens}
    pendentes = {k: v for k, v in pendentes.items() if k in ids}
    transferidas = {k: v for k, v in transferidas.items() if k in ids}
    resposta = {"substituidas": 0, "outra_loja": {}, "pendentes": {}, "perdidas": 0,
                "pendentes_atendidos": 0, "pendentes_perdidos": 0,
                "transferidas_atendidas": 0, "transferidas_perdidas": 0}
    if limite_extra is not None:
        # Os pedidos extras também precisam de capacidade de entrega; o que não
        # cabe é contado como perdido (pendentes antes dos transferidos).
        livre = max(0, int(limite_extra))
        for fonte, chave in ((pendentes, "pendentes_perdidos"), (transferidas, "transferidas_perdidas")):
            total = sum(fonte.values())
            if total > livre:
                chaves = list(fonte)
                partes = dividir(livre, [fonte[k] for k in chaves])
                fonte.clear(); fonte.update({k: q for k, q in zip(chaves, partes) if q})
                resposta[chave] += total - livre
            livre -= sum(fonte.values())
    demandas = dividir(demanda, pesos)
    linhas = []
    estoques = estado.setdefault('estoques_produtos', {})
    for p, d in zip(itens, demandas):
        pid = p['produto_id']
        estoque_linha = estoques.setdefault(
            pid, {'estoque_mp': {'quantidade': 0, 'valor': 0}, 'estoque_pa': {'quantidade': 0, 'valor': 0}})
        st = estoque_linha['estoque_pa']
        pend, trans = pendentes.get(pid, 0), transferidas.get(pid, 0)
        disponivel = st['quantidade']
        q_pend = min(pend, disponivel); disponivel -= q_pend
        q_novo = min(d, disponivel); disponivel -= q_novo
        q_trans = min(trans, disponivel)
        q = q_pend + q_novo + q_trans
        cmv = dinheiro(st['valor'] * q / st['quantidade']) if st['quantidade'] else 0
        receita = dinheiro(q * p['preco']); st['quantidade'] -= q; st['valor'] = dinheiro(st['valor'] - cmv)
        resposta["pendentes_atendidos"] += q_pend; resposta["pendentes_perdidos"] += pend - q_pend
        resposta["transferidas_atendidas"] += q_trans; resposta["transferidas_perdidas"] += trans - q_trans
        linhas.append({'produto_id': pid, 'nome': p['produto_nome'], 'preco': p['preco'],
                       'custos_campanha': deepcopy(p.get('custos_campanha')),
                       'demanda': d + pend + trans, 'vendas': q, 'receita': receita, 'cmv': cmv,
                       'pendentes_recebidos': pend, 'transferidas_recebidas': trans, 'substituicoes': 0,
                       'falta_clientes_mes': d - q_novo,
                       'alinhamento_publico': deepcopy((diagnosticos_publico or {}).get(pid))})
    # Resposta dos clientes do mês que não encontraram o produto.
    for p, linha in zip(itens, linhas):
        falta = linha['falta_clientes_mes']
        if falta <= 0:
            continue
        classe = classe_ruptura(linha['produto_id'])
        if classe is None:
            resposta["perdidas"] += falta
            continue
        regra = RESPOSTA_RUPTURA[classe]
        partes = dict(zip(regra, dividir(falta, list(regra.values()))))
        if partes.get("adia"):
            resposta["pendentes"][linha['produto_id']] = partes["adia"]
        if partes.get("outra_loja"):
            resposta["outra_loja"][linha['produto_id']] = partes["outra_loja"]
        resposta["perdidas"] += partes.get("desiste", 0)
        sub = partes.get("substitui", 0)
        if sub:
            # Substituto: outro item da mesma linha do catálogo com estoque.
            mesma = linha_catalogo(linha['produto_id'])
            candidatos = [(i, outra) for i, (q, outra) in enumerate(zip(itens, linhas))
                          if outra is not linha and linha_catalogo(outra['produto_id']) == mesma
                          and estoques[outra['produto_id']]['estoque_pa']['quantidade'] > 0]
            if candidatos:
                partes_sub = dividir(sub, [max(1e-9, pesos[i]) for i, _ in candidatos])
                for (i, outra), qtd in zip(candidatos, partes_sub):
                    st = estoques[outra['produto_id']]['estoque_pa']
                    qtd = min(qtd, st['quantidade'])
                    if qtd <= 0:
                        continue
                    cmv = dinheiro(st['valor'] * qtd / st['quantidade'])
                    receita = dinheiro(qtd * outra['preco'])
                    st['quantidade'] -= qtd; st['valor'] = dinheiro(st['valor'] - cmv)
                    outra['vendas'] += qtd; outra['substituicoes'] += qtd
                    outra['receita'] = dinheiro(outra['receita'] + receita); outra['cmv'] = dinheiro(outra['cmv'] + cmv)
                    resposta["substituidas"] += qtd; sub -= qtd
            resposta["perdidas"] += sub
    for p, linha in zip(itens, linhas):
        linha['comissao_canal'] = dinheiro(linha['receita'] * (.05 if 'ATACADO' in p['canais'] else .03 if any(
            c in p['canais'] for c in ('ECOMMERCE', 'MARKETPLACE')) else 0))
        linha['estoque_final'] = deepcopy(estoques[linha['produto_id']]['estoque_pa'])
    sincronizar(estado)
    return linhas, resposta


def vender(estado,itens,demanda,pesos,diagnosticos_publico=None):
    demandas=dividir(demanda,pesos); linhas=[]
    for p,d in zip(itens,demandas):
        # Uma linha publicada pode ainda não ter sido ativada por falta de
        # capital para homologação. Ela participa da demanda, mas não pode
        # vender estoque inexistente nem quebrar a apuração da rodada.
        estoque_linha = estado.setdefault('estoques_produtos', {}).setdefault(
            p['produto_id'], {'estoque_mp': {'quantidade': 0, 'valor': 0}, 'estoque_pa': {'quantidade': 0, 'valor': 0}}
        )
        st=estoque_linha['estoque_pa'];q=min(d,st['quantidade'])
        cmv=dinheiro(st['valor']*q/st['quantidade']) if st['quantidade'] else 0
        receita=dinheiro(q*p['preco']);st['quantidade']-=q;st['valor']=dinheiro(st['valor']-cmv)
        comissao=dinheiro(receita*(.05 if 'ATACADO' in p['canais'] else .03 if any(c in p['canais'] for c in ('ECOMMERCE','MARKETPLACE')) else 0))
        linhas.append({'produto_id':p['produto_id'],'nome':p['produto_nome'],'preco':p['preco'],'custos_campanha':deepcopy(p.get('custos_campanha')),'demanda':d,'vendas':q,'receita':receita,'cmv':cmv,'comissao_canal':comissao,'estoque_final':deepcopy(st), 'alinhamento_publico': deepcopy((diagnosticos_publico or {}).get(p['produto_id']))})
    sincronizar(estado)
    return linhas
