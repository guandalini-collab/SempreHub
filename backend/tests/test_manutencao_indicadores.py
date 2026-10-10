from copy import deepcopy
import pytest
from app.motor.indicadores import disponibilidade_maquinas
from app.motor.tradicional import preparar, apurar
from tests.test_tradicional import base, sem_tributos
from tests import test_tradicional as verificacao_contabil


def maquina(capacidade=240, condicao=1):
    return {'capacidade': capacidade, 'condicao': condicao, 'custo': 12000, 'valor_liquido': 12000, 'vida_util': 24, 'ativacao': 1}


def test_risco_acumula_proporcional_e_manutencao_integral_recupera():
    m=[maquina()]
    assert disponibilidade_maquinas(m, 0) == pytest.approx(.95)
    assert disponibilidade_maquinas(m, 0) == pytest.approx(.90)
    assert disponibilidade_maquinas(m, 500) == pytest.approx(.875)
    assert disponibilidade_maquinas(m, 1000) == 1
    assert m[0]['risco_quebra'] == 0
    assert disponibilidade_maquinas(m, 1500) == 1


def test_limites_investimento_e_risco():
    m=[maquina()]
    for _ in range(25): disponibilidade_maquinas(m, -100)
    assert m[0]['risco_quebra'] == 1
    assert m[0]['condicao'] == 0
    assert disponibilidade_maquinas(m,1000) == 1


def test_maquina_nova_nao_herda_desgaste_e_consolidacao_e_ponderada():
    antiga=maquina(240);antiga['risco_quebra']=.4
    nova=maquina(480);nova['risco_quebra']=0
    assert disponibilidade_maquinas([antiga,nova],0)==pytest.approx((240*.55+480*.95)/720)
    assert antiga['risco_quebra']==pytest.approx(.45)
    assert nova['risco_quebra']==pytest.approx(.05)


def test_condicao_antiga_convertida_sem_duplicacao():
    m=[maquina(condicao=.55)]
    assert disponibilidade_maquinas(m,0)==pytest.approx(.50)
    assert disponibilidade_maquinas(m,0)==pytest.approx(.45)


def test_manutencao_despesa_caixa_e_depreciacao_vida_util_separadas():
    e,d,p=base();e['estado_simulacao']['maquinas']=[maquina()]
    d['simulacao'].update(manutencao=1000,producao=0,comprar_mp=0)
    origem=deepcopy(e)
    preparo=preparar(e,d,p,1)
    assert e==origem
    assert preparo['depreciacao']==500
    assert preparo['kpis']['disponibilidade']==1
    assert preparo['estado']['maquinas'][0]['valor_liquido']==11500
    r=apurar(preparo,0,sem_tributos)
    assert r['dre']['manutencao']==1000
    assert r['dre']['depreciacao']==500
    assert r['detalhes']['dfc']['variacao']==-1000
    assert r['dre']['lucro_liquido']==-1500
    verificacao_contabil.TestTradicional().assert_reconciliacao(e,r)


def test_manutencao_nao_gasta_vida_util_duas_vezes():
    e,d,p=base();m=maquina();m['valor_liquido']=200;e['estado_simulacao']['maquinas']=[m]
    d['simulacao'].update(manutencao=1000,producao=0,comprar_mp=0)
    c=preparar(e,d,p,1)
    assert c['depreciacao']==200
    assert c['estado']['maquinas'][0]['valor_liquido']==0
