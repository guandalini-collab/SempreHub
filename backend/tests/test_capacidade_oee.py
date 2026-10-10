from copy import deepcopy
import pytest
from app.motor.indicadores import capacidades_producao
from app.motor.tradicional import preparar, apurar
from tests.test_tradicional import base, sem_tributos
from tests import test_tradicional as contabil


def test_sem_sobrecarga_oculta():
    e,d,p=base();e['funcionarios']=5;p['produtividade_por_pessoa']=1000
    d['simulacao'].update(producao=1000,comprar_mp=1000)
    c=preparar(e,d,p,1)
    assert c['capacidade_produtiva']==pytest.approx(240*.95*.995)
    assert c['producao_real']==226
    assert c['producao_real']<=c['capacidade_produtiva']
    r=apurar(c,1000,sem_tributos);contabil.TestTradicional().assert_reconciliacao(e,r)


def test_horas_extras_aumentam_tempo_sem_performance_acima_de_cem():
    e,d,p=base();e['funcionarios']=5;p['produtividade_por_pessoa']=1000
    p['salario_base']=2000
    d['simulacao'].update(producao=1000,comprar_mp=1000,manutencao=1000,treinamento=500)
    regular=preparar(e,d,p,1)
    d['simulacao']['horas_extras']=40
    extra=preparar(e,d,p,1)
    assert regular['producao_real']==240
    assert extra['producao_real']==283
    assert extra['kpis']['performance']==1
    assert extra['kpis']['capacidade_nominal_periodo']==pytest.approx(240*(1+40/220))
    assert extra['custo_horas_extras']>0
    assert extra['utilizacao_maquinas']<=1


def test_equipe_e_insumos_limitam_producao():
    c=capacidades_producao(1000,0,120,1,40,1,1)
    assert c['capacidade_produtiva']==120
    assert c['capacidade_trabalho_extra']==0
    assert c['fator_tempo_maquinas']==1
    e,d,p=base();d['simulacao'].update(producao=1000,comprar_mp=10)
    assert preparar(e,d,p,1)['producao_real']==10


def test_sem_maquinas_ou_sem_plano_nao_aplica():
    e,d,p=base();e['estado_simulacao']['maquinas']=[]
    c=preparar(e,d,p,1);assert c['kpis']['oee'] is None;assert c['producao_real']==0
    e,d,p=base();d['simulacao']['producao']=0
    c=preparar(e,d,p,1);assert c['kpis']['oee'] is None;assert c['kpis']['oee_observado'] is None


def test_qualidade_esperada_e_observada_preservam_inteiros_e_custos():
    e,d,p=base();d['simulacao'].update(producao=10,comprar_mp=10)
    original=deepcopy(e)
    c=preparar(e,d,p,1)
    assert e==original
    assert c['kpis']['qualidade_oee']==.98
    assert c['refugo']==0
    assert c['kpis']['qualidade_observada']==1
    assert c['kpis']['oee']==pytest.approx(.95*.995*.98)
    assert c['kpis']['oee_observado']==pytest.approx(.95*.995)
    r=apurar(c,100,sem_tributos);contabil.TestTradicional().assert_reconciliacao(e,r)


def test_treinamento_proporcional_teto_e_piso():
    e,d,p=base();e['funcionarios']=2
    d['simulacao'].update(treinamento=200,manutencao=1000)
    c=preparar(e,d,p,1);assert c['kpis']['performance']==1;assert c['kpis']['qualidade_oee']==pytest.approx(.985)
    d['simulacao']['treinamento']=20000
    c=preparar(e,d,p,1);assert c['kpis']['performance']==1;assert c['kpis']['qualidade_oee']==pytest.approx(.995)
