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
    if preco_maximo is not None and preco > float(preco_maximo):
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

    return {
        "fator": max(0.0, min(1.0, fator)),
        "status": "alinhado" if not avisos else "alinhamento_parcial",
        "preco": preco, "preco_maximo": preco_maximo,
        "canais_produto": sorted(canais_produto), "canais_publico": sorted(canais_alvo),
        "cobertura_produto": cobertura_produto, "cobertura_publico": cobertura_alvo,
        "avisos": avisos,
    }


def diagnosticos_segmentacao(itens, segmentacao=None):
    return {item.get("produto_id"): diagnostico_segmentacao(item, segmentacao) for item in itens}


def atrativos(itens, referencia, custo_referencia, marca=0, qualidade=0, segmentacao=None):
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
        # Nas linhas novas não há demanda orgânica. Se a equipe escolheu mídia
        # incompatível (ou não escolheu nenhum canal), a verba aparece como
        # despesa, porém esta linha não disputa consumidores nesta semana.
        if p.get("midias_recomendadas") and (not p.get("midias") or diagnostico["aderencia"] <= 0):
            valores.append(0.0)
            continue
        segmento = diagnostico_segmentacao(p, segmentacao)
        valores.append(p['peso']*(ref/preco)**2*canal*pos*(1+math.sqrt(campanha/1000))**.3 * segmento["fator"])
    return valores


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
