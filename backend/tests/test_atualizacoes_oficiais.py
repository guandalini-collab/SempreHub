from datetime import date,timedelta
from types import SimpleNamespace
import pytest
from app import atualizacoes_oficiais as a
from app.fontes_oficiais import fonte_oficial
from app.database import SessionLocal
from app.models import BoletimOficial, ConsultaOficial, agora
from .test_fluxo import _criar_turma,_entrar
from .conftest import cadastrar

URL='https://www.ibge.gov.br/indicador'
TEXTO='O indicador oficial apresentou variação de 1,2% no período de referência.'


def boletim():
    return {'itens':[dict(titulo='Indicador oficial da atividade',tema='ECONOMIA',resumo=TEXTO,
        instituicao='IBGE',url=URL,publicado_em='2026-10-30',referencia='Outubro de 2026',
        vigencia_inicio=None,vigencia_fim=None,condicoes=None,trecho=TEXTO)]}


@pytest.mark.parametrize('url,ok',[(URL,True),('https://api.bcb.gov.br/serie',True),
 ('https://www.ipea.gov.br/pesquisa',True),('https://fgv.br/estudo',True),
 ('https://ibge.gov.br.evil.com/estudo',False),('https://ibge.gov.br@evil.com/',False),
 ('https://noticia.com/',False),('http://www.ibge.gov.br/',False),('https://ibge.gov.br:8443/',False)])
def test_dominio_institucional(url,ok):
    assert fonte_oficial(url)==ok


def test_evidencia_obrigatoria_e_data(monkeypatch):
    monkeypatch.setattr(a,'obter_documento',lambda url,somente_oficial:SimpleNamespace(texto=a.normalizar(TEXTO)))
    assert a.validar_boletim(boletim(),{URL},date(2026,11,4))['itens'][0]['instituicao']=='IBGE'
    with pytest.raises(ValueError):a.validar_boletim(boletim(),set(),date(2026,11,4))
    with pytest.raises(ValueError):a.validar_boletim(boletim(),{URL},date(2026,10,1))
    monkeypatch.setattr(a,'obter_documento',lambda url,somente_oficial:SimpleNamespace(texto='outro conteúdo'))
    with pytest.raises(ValueError):a.validar_boletim(boletim(),{URL},date(2026,11,4))


def test_execucao_unica_e_falha_preserva_historico(cliente,monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY','somente-teste')
    chamadas=[]
    def gerar(*args):chamadas.append(1);return boletim(),{URL}
    monkeypatch.setattr(a,'gerar_json',gerar)
    monkeypatch.setattr(a,'obter_documento',lambda url,somente_oficial:SimpleNamespace(texto=a.normalizar(TEXTO)))
    assert a.atualizar()
    assert not a.atualizar()
    assert len(chamadas)==1
    with SessionLocal() as db:
        salvo=a.consultar(db)
        assert len(salvo['itens'])==1 and not salvo['consulta_vencida']
        c=db.get(ConsultaOficial,1);c.tentado_em=agora()-timedelta(hours=7);db.commit()
    monkeypatch.setattr(a,'gerar_json',lambda *args:(_ for _ in ()).throw(ValueError('falha')))
    assert not a.atualizar()
    with SessionLocal() as db:
        assert db.query(BoletimOficial).count()==1
        assert a.consultar(db)['itens']==salvo['itens']
        assert a.consultar(db)['erro']
        c=db.get(ConsultaOficial,1);c.tentado_em=agora()-timedelta(minutes=16);db.commit()
    # Falhas voltam a ser tentadas em prazo curto, sem recálculo dos dados já
    # publicados e sem liberar uma sequência contínua de chamadas.
    monkeypatch.setattr(a,'gerar_json',gerar)
    assert a.atualizar()
    assert len(chamadas)==2


def test_permissoes_e_nao_dispara_api_sem_chave(cliente,professor):
    t=_criar_turma(cliente,professor,modo_jogo='TRADICIONAL')
    aluno=cadastrar(cliente,'Ana','oficial@aluno.iffar.edu.br')
    outro=cadastrar(cliente,'Bia','oficial-outra@aluno.iffar.edu.br')
    eid=_entrar(cliente,aluno,t['codigo'],'Oficial')
    url=f'/api/aluno/empresas/{eid}/atualizacoes-oficiais'
    assert cliente.get(url).status_code==401
    assert cliente.get(url,headers=outro).status_code==404
    r=cliente.get(url,headers=aluno)
    assert r.status_code==200 and not r.json()['habilitado']
    assert cliente.get(f"/api/professor/turmas/{t['id']}/atualizacoes-oficiais",headers=professor).status_code==200


def test_pesquisa_nao_aceita_citacao_de_portal(monkeypatch):
    from app import inteligencia_mercado as ia
    from fastapi import HTTPException
    monkeypatch.setenv('OPENAI_API_KEY','somente-teste')
    vistos=[]
    def solicitar(corpo,chave):
        vistos.append(corpo)
        return 'Texto sem comprovação oficial',{'https://noticia.com/tributo'}
    monkeypatch.setattr(ia,'_solicitar',solicitar)
    with pytest.raises(HTTPException) as e:ia.gerar_json('Pesquise',{},True)
    assert e.value.status_code==502
    assert 'gov.br' in vistos[0]['tools'][0]['filters']['allowed_domains']
    assert len(vistos)==1


def test_leitura_recusa_fonte_nao_oficial_antes_de_acessar_rede(monkeypatch):
    from app import evidencias_mercado as provas
    monkeypatch.setattr(provas.socket,'getaddrinfo',lambda *args,**kwargs:(_ for _ in ()).throw(AssertionError('A rede não deve ser consultada.')))
    with pytest.raises(provas.FonteInsegura):provas.obter_documento('https://portal-comercial.example/noticia')
