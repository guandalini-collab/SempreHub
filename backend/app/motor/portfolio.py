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


def atrativos(itens, referencia, custo_referencia, marca=0, qualidade=0):
    from ..catalogo_campanhas import CAMPANHAS
    custos={i:v for i,n,c,v,u in CAMPANHAS}
    valores=[]
    for p in itens:
        ref=referencia*p['custo_unitario']/max(.01,custo_referencia)
        canal=1.1 if 'ATACADO' in p['canais'] else 1.05 if any(c in p['canais'] for c in ('ECOMMERCE','MARKETPLACE')) else 1
        pos=.75 if p['posicionamento']!='PRECO' and marca<3 and qualidade<3 else 1
        campanha=sum(custos[m['id']]*m['quantidade'] for m in p.get('midias',[]))
        if (p.get('custos_campanha') or {}).get('versao')==2:
            campanha=p['custos_campanha']['investimento_efetivo']
        valores.append(p['peso']*(ref/p['preco'])**2*canal*pos*(1+math.sqrt(campanha/1000))**.3)
    return valores


def produzir(estado, itens, op, capacidade, maquinas, multiplicador):
    estoque=deepcopy(estado.get('estoques_produtos') or {})
    # Estoque histórico anterior ao portfólio pertence ao produto original, nunca é clonado.
    original=estado.get('produto_estoque_original') or itens[0]['produto_id']
    if not estoque:
        estoque[original]={k:deepcopy(estado[k]) for k in ('estoque_mp','estoque_pa')}
    pesos=[p['peso'] for p in itens]
    compras_un=dividir(op.get('comprar_mp',0),pesos)
    pedidas=dividir(op.get('producao',0),pesos)
    disponiveis=[]; compras=0
    for p,un in zip(itens,compras_un):
        st=estoque.setdefault(p['produto_id'],{'estoque_mp':{'quantidade':0,'valor':0},'estoque_pa':{'quantidade':0,'valor':0}})
        valor=dinheiro(un*p['custo_unitario']*multiplicador); compras+=valor
        st['estoque_mp']['quantidade']+=un;st['estoque_mp']['valor']=dinheiro(st['estoque_mp']['valor']+valor)
        disponiveis.append(st['estoque_mp']['quantidade'])
    producao=[min(q,disp) for q,disp in zip(pedidas,disponiveis)]
    limite=max(0,math.floor(capacidade+1e-12))
    if sum(producao)>limite: producao=dividir(limite,producao)
    real=sum(producao); taxa=estado.get("indicadores_didaticos",{}).get("taxa_defeito",.02)
    refugos=dividir(math.floor(real*taxa+1e-12),producao)
    perda=0
    for p,q,ref in zip(itens,producao,refugos):
        st=estoque[p['produto_id']];mp=st['estoque_mp'];pa=st['estoque_pa']
        consumido=dinheiro(mp['valor']*q/mp['quantidade']) if mp['quantidade'] else 0
        refugo=dinheiro(consumido*ref/q) if q else 0;perda+=refugo
        mp['quantidade']-=q;mp['valor']=dinheiro(mp['valor']-consumido)
        pa['quantidade']+=q-ref;pa['valor']=dinheiro(pa['valor']+consumido-refugo)
    estado['estoques_produtos']=estoque
    sincronizar(estado)
    return dinheiro(compras),real,sum(refugos),dinheiro(perda)


def sincronizar(estado):
    for k in ('estoque_mp','estoque_pa'):
        estado[k]={'quantidade':sum(p[k]['quantidade'] for p in estado['estoques_produtos'].values()),'valor':dinheiro(sum(p[k]['valor'] for p in estado['estoques_produtos'].values()))}


def vender(estado,itens,demanda,pesos):
    demandas=dividir(demanda,pesos); linhas=[]
    for p,d in zip(itens,demandas):
        st=estado['estoques_produtos'][p['produto_id']]['estoque_pa'];q=min(d,st['quantidade'])
        cmv=dinheiro(st['valor']*q/st['quantidade']) if st['quantidade'] else 0
        receita=dinheiro(q*p['preco']);st['quantidade']-=q;st['valor']=dinheiro(st['valor']-cmv)
        comissao=dinheiro(receita*(.05 if 'ATACADO' in p['canais'] else .03 if any(c in p['canais'] for c in ('ECOMMERCE','MARKETPLACE')) else 0))
        linhas.append({'produto_id':p['produto_id'],'nome':p['produto_nome'],'preco':p['preco'],'custos_campanha':deepcopy(p.get('custos_campanha')),'demanda':d,'vendas':q,'receita':receita,'cmv':cmv,'comissao_canal':comissao,'estoque_final':deepcopy(st)})
    sincronizar(estado)
    return linhas
