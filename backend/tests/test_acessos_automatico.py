from datetime import datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo
from .conftest import cadastrar
from .test_fluxo import _entrar
from app.motor.regras_mei import regras_mei


def test_auto_data_fixa_e_acessos_com_autorizacao(cliente, professor):
    t = cliente.post('/api/professor/turmas', headers=professor,json={'nome':'Automática','modo_jogo':'TRADICIONAL'}).json()
    aluno = cadastrar(cliente,'Ana','auto@aluno.iffar.edu.br')
    eid = _entrar(cliente,aluno,t['codigo'],'Equipe Auto')
    url = f'/api/aluno/empresas/{eid}'
    p = cliente.get(url,headers=aluno).json()
    assert p['turma']['calendario']['inicio'] == datetime.now(ZoneInfo('America/Sao_Paulo')).date().isoformat()
    assert cliente.get(url,headers=aluno).json()['turma']['calendario']==p['turma']['calendario']
    assert cliente.post(url+'/acessos',headers=aluno,json={'aba':'financas'}).status_code==201
    rel = cliente.get(f"/api/professor/turmas/{t['id']}/acessos",headers=professor).json()
    assert rel['registros'][0]['aba']=='financas'
    assert rel['participantes'][0]['acessos']==1
    assert cliente.post(url+'/acessos',json={'aba':'financas'}).status_code==401
    outro=cadastrar(cliente,'Outro','outro@aluno.iffar.edu.br')
    assert cliente.post(url+'/acessos',headers=outro,json={'aba':'financas'}).status_code==404
    p2=cadastrar(cliente,'Professor 2','p2@iffar.edu.br','PROFESSOR','codigo-teste')
    assert cliente.get(f"/api/professor/turmas/{t['id']}/acessos",headers=p2).status_code==404


def test_mei_projetado_separado_da_regra_vigente():
    t=SimpleNamespace(configuracao_simulacao={'periodicidade':'SEMANAL','data_inicio_simulada':'2026-12-31','cenario_mei_plp186':True,'atividade_rural':True},rodada_atual=1,teto_mei_anual=81000)
    assert regras_mei(t)['teto_anual']==81000
    assert regras_mei(t,2)['teto_anual']==110000
    assert regras_mei(t,2)['limite_empregados']==2
    t.configuracao_simulacao['atividade_rural']=False
    assert regras_mei(t,2)['limite_empregados']==1
    assert 'ainda não vigente' in regras_mei(t,2)['estado']
    t.configuracao_simulacao['data_inicio_simulada']='2028-01-01'
    assert regras_mei(t)['teto_anual']==140000
    t.configuracao_simulacao['cenario_mei_plp186']=False
    assert regras_mei(t)['teto_anual']==81000
