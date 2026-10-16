from types import SimpleNamespace
import pytest
from app.dashboard_semanal import calcular_dashboard,BasesSemanais
from .test_fluxo import _criar_turma,_entrar
from .conftest import cadastrar
from .test_avancado_api import _decisao_avancada,_fechar


def test_calculo_nps_e_bases_semanais_sem_inventar_clientes():
    r=SimpleNamespace(detalhes_simulacao={'operacao':{'oee':.9,'otif':.95,'producao_planejada':100,'producao_real':80,'refugo':4,'horas_extras':2}},receita=1000,funcionarios=2)
    d=calcular_dashboard(r,{'marketing':100,'novos_clientes':10,'pedidos':20,'leads':100,'cliques':50,'promotores':6,'neutros':2,'detratores':2,'horas_ausencia':4,'horas_contratadas':80})
    assert d['marketing']['CAC']['valor']==10
    assert d['marketing']['Conversão']['valor']==20
    assert d['marketing']['CPC']['valor']==2
    assert d['marketing']['NPS']['valor']==40
    assert d['rh']['Absenteísmo']['valor']==5
    assert d['producao']['Refugo']['valor']==5
    assert d['logistica']['OTIF']['valor']==95
    assert calcular_dashboard(r,{})['marketing']['CAC']['valor'] is None
    with pytest.raises(ValueError): BasesSemanais(horas_ausencia=90,horas_contratadas=80)
    with pytest.raises(ValueError): BasesSemanais(marketing=float('nan'))


def test_bases_manuais_nao_reescrevem_dre_e_professor_somente_leitura(cliente,professor):
    t=_criar_turma(cliente,professor,modo_jogo='TRADICIONAL')
    a=cadastrar(cliente,'Ana','painel-semanal@aluno.iffar.edu.br')
    eid=_entrar(cliente,a,t['codigo'],'Semanal')
    _decisao_avancada(cliente,a,eid,1,producao=10,comprar_mp=10)
    _fechar(cliente,professor,t,1)
    antes=cliente.get(f'/api/aluno/empresas/{eid}',headers=a).json()['resultados']
    url=f'/api/aluno/empresas/{eid}/dashboard/1'
    r=cliente.put(url,headers=a,json={'marketing':100,'novos_clientes':10})
    assert r.status_code==200,r.text
    assert r.json()['indicadores']['marketing']['CAC']['valor']==10
    assert cliente.get(f'/api/aluno/empresas/{eid}',headers=a).json()['resultados']==antes
    assert cliente.get(f"/api/professor/turmas/{t['id']}/empresas/{eid}/dashboard/1",headers=professor).status_code==200
    assert cliente.put(url,headers=a,json={'marketing':-1}).status_code==422
