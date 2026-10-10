from copy import deepcopy
import pytest
from app.motor.financeiros import reconciliar_financeiros
from app.motor.tradicional import preparar, apurar
from tests.test_tradicional import base, sem_tributos, proxima_empresa
from tests import test_tradicional as contabil


def dados():
    b=dict(caixa=-5000,receber=3000,pagar=1000,estoques=2000,imobilizado=10000,divida=4000,patrimonio=5000)
    s={'receber':[{'origem':1,'vencimento':2,'valor':1000},{'origem':0,'vencimento':14,'valor':2000}],
       'pagar':[{'origem':1,'vencimento':2,'valor':1000}],'vencimento_divida':20}
    d=dict(receita=10000,lucro_liquido=2000,juros=400,depreciacao=500)
    return b,s,d


def test_reclassificacao_preserva_patrimonio_e_prazos():
    b,s,d=dados();r=reconciliar_financeiros(b,s,d,1,.08,4000)
    assert b['disponibilidades']==0 and b['cheque_especial']==5000
    assert b['ativo_total']==15000 and b['passivo_total']==10000
    assert b['ativo_total']-b['passivo_total']==b['patrimonio']
    assert b['juros_cheque_proxima_rodada']==400
    assert b['ativo_circulante']==3000 and b['passivo_circulante']==6000
    assert b['realizavel_longo_prazo']==2000 and b['passivo_nao_circulante']==4000
    assert r['liquidez_corrente']==.5 and r['liquidez_seca']==pytest.approx(1/6)
    assert r['liquidez_imediata']==0 and r['liquidez_geral']==.5
    assert r['pmr']==3 and r['pmp']==7.5 and r['ebitda']==2900
    assert set(d)=={'receita','lucro_liquido','juros','depreciacao'}


def test_prazo_desconhecido_nao_inventa_indicador():
    b,s,d=dados();del s['vencimento_divida']
    r=reconciliar_financeiros(b,s,d,1,.08)
    assert r['liquidez_corrente'] is None and r['pmp'] is None
    del s['receber'][0]['vencimento']
    assert reconciliar_financeiros(b,s,d,1,.08)['liquidez_geral'] is None
    del d['depreciacao']
    assert reconciliar_financeiros(b,s,d,1,.08)['ebitda'] is None


@pytest.mark.parametrize('caixa',[0,5000])
def test_sem_deficit_nao_cria_cheque(caixa):
    b,s,d=dados();b['caixa']=caixa
    reconciliar_financeiros(b,s,d,1,.08)
    assert b['disponibilidades']==caixa and b['cheque_especial']==0
    assert b['juros_cheque_proxima_rodada']==0


@pytest.mark.parametrize('preco,status',[(0,'Dados indisponíveis'),(1,'Não se aplica (Margem Negativa)'),(100,'Calculado')])
def test_ponto_equilibrio_e_ltv(preco,status):
    e,d,p=base();d['preco']=preco
    r=apurar(preparar(e,d,p,1),40,sem_tributos)
    assert r['detalhes']['operacao']['ponto_equilibrio_status']==status
    assert r['detalhes']['operacao']['ltv'] is None
    contabil.TestTradicional().assert_reconciliacao(e,r)


def test_juros_cobrados_so_na_rodada_seguinte():
    e,d,p=base();e['caixa']=0;p['custos_fixos_mensais']=5000
    d['simulacao'].update(producao=0,comprar_mp=0)
    r=apurar(preparar(e,d,p,1),0,sem_tributos)
    assert r['caixa']==-5000 and r['dre']['juros']==0
    assert r['detalhes']['balanco']['juros_cheque_proxima_rodada']==400
    r2=apurar(preparar(proxima_empresa(e,r),d,p,2),0,sem_tributos)
    assert r2['dre']['juros']==400
    assert r2['detalhes']['balanco']['ativo_total']-r2['detalhes']['balanco']['passivo_total']==r2['detalhes']['balanco']['patrimonio']


def test_margem_zero_e_ebitda_sem_somar_principal():
    e,d,p=base();r=apurar(preparar(e,d,p,1),40,sem_tributos)
    dre=deepcopy(r['dre'])
    dre['receita']=sum(dre[k] for k in ('impostos','cmv','royalties','comissao_canal','frete','refugos'))
    op=reconciliar_financeiros(r['detalhes']['balanco'],r['estado'],dre,1,.08,4000)
    assert op['ponto_equilibrio'] is None
    assert op['ponto_equilibrio_status']=='Não se aplica (Margem Zero)'
    assert op['ebitda']==pytest.approx(dre['lucro_liquido']+dre['juros']+dre['depreciacao'])
