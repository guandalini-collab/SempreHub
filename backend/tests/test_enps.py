from copy import deepcopy
import pytest
from app.motor.indicadores import enps
from app.motor.tradicional import preparar, apurar
from tests.test_tradicional import base, sem_tributos
from tests import test_tradicional as contabil


@pytest.mark.parametrize('beneficio,nota', [(0,8),(1,8),(149.99,8),(150,9),(300,9)])
def test_minimo_por_funcionario(beneficio,nota):
    r=enps({},4,2100,2000,beneficio,0)
    assert r['enps_perfis'][0]['nota']==nota
    assert r['enps']==(100 if nota==9 else 0)
    assert r['enps_respondentes']==4


@pytest.mark.parametrize('salario,nota',[(1900,5),(2000,7),(2100,8)])
def test_referencia_professor(salario,nota):
    assert enps({},3,salario,2000,0,0)['enps_perfis'][0]['nota']==nota
    assert enps({},3,salario,0,0,0)['enps_nota']==7


def test_recorrencia_reset_e_ausencia_de_funcionarios():
    s={}
    assert enps(s,3,2100,2000,150,10)['enps_perfis'][0]['nota']==9
    assert enps(s,3,2100,2000,150,10)['enps_perfis'][0]['nota']==8
    assert enps(s,3,2100,2000,150,0)['enps_perfis'][0]['nota']==9
    assert enps(s,3,2100,2000,150,10)['enps_perfis'][0]['nota']==9
    r=enps(s,0,2100,2000,150,10)
    assert r['enps'] is None and r['enps_respondentes']==0
    assert r['enps_promotores']==r['enps_neutros']==r['enps_detratores']==0
    assert s['indicadores_didaticos']['rodadas_horas_extras']==0


def test_notas_nao_acumulam_e_resultado_reproduzivel():
    s={}
    enps(s,3,2100,2000,150,0)
    assert enps(s,3,2000,2000,0,0)['enps_nota']==7
    anterior=deepcopy(s)
    a=enps(deepcopy(anterior),3,1900,2000,150,10)
    b=enps(deepcopy(anterior),3,1900,2000,150,10)
    assert a==b and a['enps']==-100
    assert a['enps_promotores']+a['enps_neutros']+a['enps_detratores']==3


def test_beneficio_e_custo_preservados_abaixo_do_minimo():
    e,d,p=base();e['funcionarios']=3;p['salario_base']=2000
    d['simulacao'].update(salario=2100,beneficio=149.99)
    c=preparar(e,d,p,1)
    assert c['kpis']['enps_perfis'][0]['nota']==8
    r=apurar(c,40,sem_tributos)
    assert r['dre']['beneficios']==449.97
    contabil.TestTradicional().assert_reconciliacao(e,r)


@pytest.mark.parametrize('quantidade',range(1,51))
def test_perfis_somam_e_inicial_neutro(quantidade):
    r=enps({},quantidade,2000,2000,0,0)
    assert sum(g['quantidade'] for g in r['enps_perfis'])==quantidade
    assert r['enps']==0 and r['enps_neutros']==quantidade


def test_notas_fracionarias_e_sensibilidades():
    s={}
    enps(s,10,2100,2000,150,10)
    r=enps(s,10,2100,2000,150,10)
    assert [g['nota'] for g in r['enps_perfis']]==[8,7.5,9]
    assert (r['enps_promotores'],r['enps_neutros'],r['enps_detratores'])==(2,8,0)
    assert r['enps']==20
    s={};enps(s,10,2000,2000,150,10)
    r=enps(s,10,2000,2000,150,10)
    assert [g['nota'] for g in r['enps_perfis']]==[7,6.5,7.5]
    assert r['enps_detratores']==4 and r['enps']==-40


def test_resultado_fracionario_nao_truncado():
    s={};enps(s,3,2100,2000,150,10)
    r=enps(s,3,2100,2000,150,10)
    assert r['enps']==pytest.approx(100/3)
    assert r['enps']!=int(r['enps'])
