from types import SimpleNamespace
import pytest
from app.dashboard_semanal import calcular_dashboard,BasesSemanais
from .test_fluxo import _criar_turma,_entrar
from .conftest import cadastrar
from .test_avancado_api import _decisao_avancada,_fechar


def test_calculo_nps_e_bases_semanais_sem_inventar_clientes():
    r=SimpleNamespace(detalhes_simulacao={'operacao':{'oee':.9,'otif':.95,'producao_planejada':100,'producao_real':80,'refugo':4,'horas_extras':2}},receita=1000,funcionarios=2)
    d=calcular_dashboard(r,{'marketing':100,'anuncios':100,'novos_clientes':10,'pedidos':20,'leads':100,'cliques':50,'promotores':6,'neutros':2,'detratores':2,'horas_ausencia':4,'horas_contratadas':80})
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
    payload={'marketing':100,'novos_clientes':10,'metas':{'marketing.CAC':{'alvo':10,'alerta':20}}}
    resposta=cliente.put(url,headers=a,json=payload)
    assert resposta.status_code==200,resposta.text
    assert resposta.json()['indicadores']['marketing']['CAC']['meta']['status']=='Dentro da meta'
    assert cliente.get(url,headers=a).json()['metas']==payload['metas']
    # Clientes antigos da API não apagam metas ao salvar somente as bases.
    resposta=cliente.put(url,headers=a,json={'marketing':150,'novos_clientes':10})
    assert resposta.json()['indicadores']['marketing']['CAC']['meta']['status']=='Em alerta'
    resposta=cliente.put(url,headers=a,json={'marketing':150,'novos_clientes':10,'metas':{}})
    assert resposta.json()['metas']=={}
    assert cliente.get(f'/api/aluno/empresas/{eid}',headers=a).json()['resultados']==antes



def test_lacunas_dos_anexos_e_bases_de_anuncios_separadas():
    r=SimpleNamespace(detalhes_simulacao={'dre':{'frete':60,'armazenagem':20},'operacao':{'funcionarios_inicio':10,'desligamentos_efetivos':2,'producao_planejada':100,'producao_real':80,'pedidos_despachados':4}},receita=1000,funcionarios=8)
    b={'marketing':200,'anuncios':50,'novos_clientes':10,'leads':25,'cliques':50,
       'horas_extras_realizadas':12,'ciclo_minutos':120,'ciclos_concluidos':10,
       'custo_logistico':120,'pedidos_expedidos':4,'itens_auditados':20,'itens_conformes':19}
    d=calcular_dashboard(r,b)
    assert d['marketing']['CAC']['valor']==20
    assert d['marketing']['CPL']['valor']==2
    assert d['marketing']['CPC']['valor']==1
    assert d['rh']['Turnover por desligamentos']['valor']==20
    assert d['rh']['Horas extras realizadas']['valor']==12
    assert d['producao']['Aderência ao plano']['valor']==80
    assert d['producao']['Tempo médio de ciclo']['valor']==12
    assert d['logistica']['Custo logístico por pedido']['valor']==30
    assert d['logistica']['Custos registrados por pedido']['valor']==20
    assert d['logistica']['Acuracidade por itens auditados']['valor']==95
    sem_anuncios=calcular_dashboard(r,{'marketing':200,'leads':25})
    assert sem_anuncios['marketing']['CPL']['valor'] is None
    assert calcular_dashboard(r,{})['producao']['Tempo médio de ciclo']['valor'] is None
    with pytest.raises(ValueError): BasesSemanais(itens_conformes=20,itens_auditados=19)


def test_metas_direcoes_fronteiras_e_ausencia_de_dados():
    r=SimpleNamespace(detalhes_simulacao={'operacao':{}},receita=1000,funcionarios=2)
    for custo,status in [(50,'Dentro da meta'),(60,'Dentro da meta'),(70,'Em alerta'),(80,'Em alerta'),(90,'Fora da meta')]:
        b=BasesSemanais(marketing=custo,novos_clientes=1,metas={'marketing.CAC':{'alvo':60,'alerta':80}}).model_dump(exclude_none=True)
        assert calcular_dashboard(r,b)['marketing']['CAC']['meta']['status']==status
    b=BasesSemanais(metas={'marketing.CAC':{'alvo':60,'alerta':80}}).model_dump(exclude_none=True)
    assert calcular_dashboard(r,b)['marketing']['CAC']['meta']['status']=='Sem dados'
    b=BasesSemanais(pedidos=8,leads=10,metas={'marketing.Conversão':{'alvo':80,'alerta':60}}).model_dump(exclude_none=True)
    assert calcular_dashboard(r,b)['marketing']['Conversão']['meta']['status']=='Dentro da meta'
    for metas in [{'marketing.CAC':{'alvo':80,'alerta':60}}, {'marketing.Conversão':{'alvo':60,'alerta':80}}, {'marketing.NPS':{'alvo':101,'alerta':20}}, {'producao.Inventado':{'alvo':0,'alerta':0}}]:
        with pytest.raises(ValueError): BasesSemanais(metas=metas)
