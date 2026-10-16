from copy import deepcopy
from datetime import date, timedelta
import pytest
from app.motor.calendario import periodo, adaptar
from app.motor import tradicional, startup
from .test_tradicional import base, sem_tributos, proxima_empresa
from .test_startup import _entrada
from .test_fluxo import _criar_turma, _entrar
from .conftest import cadastrar


def cfg(inicio='2026-10-15',perfil='VAREJO'):
    return dict(periodicidade='SEMANAL',data_inicio_simulada=inicio,perfil_sazonal=perfil)


def test_calendario_real_sem_meses_de_quatro_semanas():
    c=cfg('2026-12-29')
    r=periodo(c,1)
    assert r['inicio']=='2026-12-29' and r['fim']=='2027-01-04'
    assert r['fator_mensal']==pytest.approx(7/31)
    assert periodo(cfg('2028-02-26'),1)['fator_mensal']==pytest.approx(4/29+3/31)
    assert periodo(c,2)['inicio']=='2027-01-05'
    assert periodo({},1) is None


def test_sazonalidade_por_perfil_e_antecipacao():
    antes=periodo(cfg('2026-10-15'),1)
    natal=periodo(cfg('2026-12-19'),1)
    pos=periodo(cfg('2026-12-26'),1)
    assert 'Pós-Dia das Crianças' in antes['sazonalidade']['eventos']
    assert natal['sazonalidade']['demanda']>antes['sazonalidade']['demanda']>pos['sazonalidade']['demanda']
    assert any(e['nome']=='Natal' for e in antes['proximos_eventos'])
    assert periodo(cfg(perfil='NEUTRO'),1)['sazonalidade']['demanda']==1
    assert periodo(cfg('2026-12-19','SERVICOS'),1)['sazonalidade']['demanda']<natal['sazonalidade']['demanda']


def test_taxa_composta_e_proporcionalidade_sem_mutacao():
    p={'taxa_juros_mensal':.08,'custos_fixos_mensais':3100,'configuracao_simulacao':cfg('2026-10-01')}
    original=deepcopy(p);a=adaptar(p,1)
    assert a['custos_fixos_mensais']==pytest.approx(700)
    assert (1+a['taxa_juros_mensal'])**(31/7)==pytest.approx(1.08)
    assert adaptar(a,1)==a and p==original


def test_tres_semanas_industria_conciliam_caixa_estoque_e_patrimonio():
    e,d,p=base();p['configuracao_simulacao'].update(cfg(perfil='NEUTRO'))
    p.update(salario_base=2000,custos_fixos_mensais=3100)
    d.update(contratar=1);d['simulacao'].update(salario=2500,beneficio=150,manutencao=1000,treinamento=100)
    historico=[]
    for semana in range(1,4):
        preparo=tradicional.preparar(e,d,p,semana)
        assert preparo['folha']==pytest.approx(round(2500*1.45*periodo(cfg(),semana)['fator_mensal'],2))
        assert preparo['capacidade_maquinas']==pytest.approx(240*periodo(cfg(),semana)['fator_mensal'])
        r=tradicional.apurar(preparo,20,sem_tributos)
        b=r['detalhes']['balanco'];dfc=r['detalhes']['dfc']
        assert b['ativo_total']-b['passivo_total']==pytest.approx(b['patrimonio'],abs=.01)
        assert dfc['caixa_inicial']+dfc['variacao']==pytest.approx(dfc['caixa_final'],abs=.01)
        assert r['detalhes']['operacao']['enps']==100
        historico.append(deepcopy(r));e=proxima_empresa(e,r);d['contratar']=0
    assert historico[0]['estado']!=historico[-1]['estado']


def test_startup_assinatura_mensal_e_custo_nuvem_proporcionais():
    e,d,p=_entrada();p['configuracao_simulacao'].update(cfg(perfil='NEUTRO'))
    pr=startup.preparar(e,d,p,1);r=startup.apurar(pr,20,sem_tributos)
    assert r['dre']['receita']==pytest.approx(round(r['vendas']*100*7/31,2))
    assert r['dre']['cmv']==pytest.approx(round(r['vendas']*10*7/31,2))
    assert r['detalhes']['operacao']['mrr']==pytest.approx(r['dre']['receita']/(7/31))


def test_ativacao_prospectiva_preserva_historico_e_bloqueia_reposicionamento(cliente,professor):
    turma=_criar_turma(cliente,professor,modo_jogo='TRADICIONAL')
    aluno=cadastrar(cliente,'Ana','calendario@aluno.iffar.edu.br');_entrar(cliente,aluno,turma['codigo'],'Calendário')
    url=f"/api/professor/turmas/{turma['id']}/calendario"
    r=cliente.put(url,headers=professor,json={'data_inicio':'2026-10-15','perfil_sazonal':'VAREJO'})
    assert r.status_code==200,r.text
    assert r.json()['calendario']['inicio']=='2026-10-15'
    assert cliente.put(url,headers=professor,json={'data_inicio':'2027-01-01'}).status_code==422
    c=cfg();c['rodada_inicio_calendario']=8
    assert periodo(c,7) is None and periodo(c,8)['inicio']=='2026-10-15'

@pytest.mark.parametrize('modo',['TRADICIONAL','STARTUP'])
def test_fluxo_http_tres_semanas_preserva_snapshots(cliente,professor,modo):
    from .test_avancado_api import _decisao_avancada, _fechar
    turma=_criar_turma(cliente,professor,modo_jogo=modo,total_rodadas=4,configuracao_simulacao=cfg())
    aluno=cadastrar(cliente,'Ana',f'semanas-{modo}@aluno.iffar.edu.br')
    eid=_entrar(cliente,aluno,turma['codigo'],'Semanas')
    primeiro=None
    for r in range(1,4):
        _decisao_avancada(cliente,aluno,eid,r,comprar_maquinas=1 if r==3 and modo=='TRADICIONAL' else 0,producao=10,comprar_mp=10,manutencao=300,capacidade_nuvem=100)
        _fechar(cliente,professor,turma,r)
        painel=cliente.get(f'/api/aluno/empresas/{eid}',headers=aluno).json()
        atual=painel['resultados'][-1]
        assert atual['detalhes_simulacao']['calendario']['inicio']==(date(2026,10,15)+timedelta(days=7*(r-1))).isoformat()
        assert atual['detalhes_simulacao']['engine_version']=='3.1.0-auto-calendar-projected-mei'
        if primeiro is None: primeiro=deepcopy(atual)
        assert painel['resultados'][0]==primeiro
        assert painel['turma']['calendario']['inicio']==(date(2026,10,15)+timedelta(days=7*r)).isoformat()


def test_migracao_depois_de_mes_nao_altera_mes_fechado(cliente,professor):
    from .test_avancado_api import _decisao_avancada, _fechar
    turma=_criar_turma(cliente,professor,modo_jogo='TRADICIONAL',total_rodadas=4)
    aluno=cadastrar(cliente,'Ana','migracao-semana@aluno.iffar.edu.br');eid=_entrar(cliente,aluno,turma['codigo'],'Migração')
    _decisao_avancada(cliente,aluno,eid,1);_fechar(cliente,professor,turma,1)
    antigo=cliente.get(f'/api/aluno/empresas/{eid}',headers=aluno).json()['resultados'][0]
    url=f"/api/professor/turmas/{turma['id']}/calendario"
    assert cliente.put(url,headers=professor,json={'data_inicio':'2026-10-15','perfil_sazonal':'VAREJO'}).status_code==200
    _decisao_avancada(cliente,aluno,eid,2);_fechar(cliente,professor,turma,2)
    painel=cliente.get(f'/api/aluno/empresas/{eid}',headers=aluno).json()
    assert painel['resultados'][0]==antigo
    assert painel['resultados'][1]['detalhes_simulacao']['calendario']['inicio']=='2026-10-15'
