"""Orçamento auditável: veiculação e serviços contratados são despesas distintas.

Cotações são preservadas no plano enviado. Históricos sem orçamento v2 não são
recalculados ao consultar ou repetir uma decisão.
"""
from decimal import Decimal, ROUND_HALF_UP


def arredondar(valor):
    return float(Decimal(str(valor)).quantize(Decimal('.01'),rounding=ROUND_HALF_UP))


def necessarios(midias):
    from .servicos_midias import servicos_por_midia
    exigidos={}
    tem_jingle=any(m['id']=='jingle' for m in midias)
    for m in midias:
        if tem_jingle and m['id'] in ('radio-spot','radio-streaming'):continue
        for s in servicos_por_midia(m['id']):
            quantidade=m['quantidade'] if s['cobranca']=='POR_UNIDADE_MIDIA' else 1
            exigidos[s['id']]={**s,'quantidade':quantidade}
    return list(exigidos.values())


def orcamento(midias,servicos,cotacoes=None):
    from .catalogo_campanhas import CAMPANHAS
    tarifas={i:p for i,n,c,p,u in CAMPANHAS}
    base=arredondar(sum(tarifas[m['id']]*m['quantidade'] for m in midias))
    contratados={s['id']:s['quantidade'] for s in servicos}
    detalhes=[{**s,'quantidade':contratados[s['id']],'subtotal':arredondar(s['preco_unitario']*contratados[s['id']])} for s in necessarios(midias) if s['id'] in contratados]
    from .servicos_midias import PENDENTES
    for c in cotacoes or []:
        detalhes.append({'id':'cotacao-'+c['midia_id'],'nome':PENDENTES[c['midia_id']],'quantidade':1,'preco_unitario':arredondar(c['valor']),'subtotal':arredondar(c['valor']),'fonte':{'url':c['fonte_url'],'titulo':'Cotação informada pela equipe','data_consulta':'Informada na decisão'},'referencia_tipo':'Valor informado pela equipe; não verificado automaticamente pelo sistema.','escopo':PENDENTES[c['midia_id']],'cobranca':'POR_CAMPANHA'})
    producao=arredondar(sum(s['subtotal'] for s in detalhes))
    # Produzir o jingle ou imprimir papel não compra audiência.
    eficaz=arredondar(sum(tarifas[m['id']]*m['quantidade'] for m in midias if m['id'] not in ('jingle','flyer-impressao')))
    return {'versao':2,'veiculacao':base,'servicos':producao,'total':arredondar(base+producao),'investimento_efetivo':eficaz,'detalhes_servicos':detalhes}


def validar_cotacoes(midias,cotacoes):
    from .servicos_midias import PENDENTES
    exigidos={m['id'] for m in midias if m['id'] in PENDENTES}
    presentes={c['midia_id'] for c in cotacoes}
    if len(presentes)!=len(cotacoes) or presentes!=exigidos:
        raise ValueError('Os serviços sob consulta exigem orçamento total com fonte para cada mídia escolhida. Não envie apenas a verba de veiculação.')


def validar_dependencias(midias):
    q={m['id']:m['quantidade'] for m in midias}
    if 'flyer-impressao' in q or 'flyer-distribuicao' in q:
        if q.get('flyer-impressao')!=q.get('flyer-distribuicao'):
            raise ValueError('Panfletos exigem impressão e distribuição na mesma quantidade.')
    if 'jingle' in q and not any(i in q for i in ('radio-spot','radio-patrocinio','radio-streaming')):
        raise ValueError('O jingle exige contratação de veiculação em rádio ou streaming.')


def investimento_efetivo(decisao):
    plano=decisao.get('plano_comercial') if isinstance(decisao,dict) else decisao.plano_comercial
    custos=(plano or {}).get('custos_campanha') or {}
    total=decisao.get('marketing',0) if isinstance(decisao,dict) else decisao.marketing
    return custos.get('investimento_efetivo',total) if custos.get('versao')==2 else total
