from copy import deepcopy
import pytest
from app.motor.versionamento import ENGINE_VERSION, LEGACY_ENGINE_VERSION, inicializar_indicadores, snapshot_para_leitura, versao_snapshot
from app.motor.tradicional import preparar, apurar
from app.motor import startup
from tests.test_tradicional import base, sem_tributos, proxima_empresa
from tests.test_startup import _entrada
from tests.test_avancado_api import _decisao_avancada, _fechar
from tests.test_fluxo import _criar_turma, _entrar
from tests.conftest import cadastrar
from app.database import SessionLocal
from app.models import Empresa, Turma
from app.relatorios import gerar_relatorio


def test_leitura_legacy_preserva_valores_e_nao_muta():
    s={'versao_motor':1,'operacao':{'oee':.72,'enps':40,'vendas':10},'balanco':{'caixa':-500}}
    antigo=deepcopy(s);leitura=snapshot_para_leitura(s)
    assert s==antigo
    assert leitura['engine_version']==LEGACY_ENGINE_VERSION
    assert leitura['operacao']==s['operacao']
    assert 'otif' not in leitura['operacao']
    assert snapshot_para_leitura(None) is None
    assert versao_snapshot(None)==LEGACY_ENGINE_VERSION


def test_inicializacao_unica_nao_reinicia_desgaste():
    e,d,p=base();e['estado_simulacao']['maquinas'][0]['condicao']=.3
    e['estado_simulacao']['indicadores_didaticos']={'performance':.2,'taxa_defeito':.4}
    antigo=deepcopy(e)
    c=preparar(e,d,p,1)
    assert e==antigo
    assert c['estado_inicial']==antigo['estado_simulacao']
    assert c['kpis']['disponibilidade']==.95
    assert c['kpis']['performance']==.995 and c['kpis']['qualidade_oee']==.98
    r=apurar(c,40,sem_tributos)
    assert r['detalhes']['engine_version']==ENGINE_VERSION
    c2=preparar(proxima_empresa(e,r),d,p,2)
    assert c2['kpis']['disponibilidade']==pytest.approx(.9)
    assert c2['kpis']['performance']==pytest.approx(.99)
    assert c2['estado']['maquinas'][0]['valor_liquido']==r['estado']['maquinas'][0]['valor_liquido']


def test_startup_tag_e_estado_atual_preservado():
    e,d,p=_entrada()
    c=startup.preparar(e,d,p,1)
    r=startup.apurar(c,20,sem_tributos)
    assert r['detalhes']['engine_version']==ENGINE_VERSION
    s=deepcopy(r['estado']);s['indicadores_didaticos']['performance']=.8
    inicializar_indicadores(s)
    assert s['indicadores_didaticos']['performance']==.8


@pytest.mark.parametrize('modo',['TRADICIONAL','STARTUP'])
def test_api_persistencia_historico_e_nota_sem_recalculo(cliente,professor,modo):
    turma=_criar_turma(cliente,professor,modo_jogo=modo,total_rodadas=3)
    aluno=cadastrar(cliente,'Ana',f'versao-{modo.lower()}@aluno.iffar.edu.br')
    empresa=_entrar(cliente,aluno,turma['codigo'],'Empresa versionada')
    _decisao_avancada(cliente,aluno,empresa,1,comprar_mp=100,producao=100)
    _fechar(cliente,professor,turma,1)
    with SessionLocal() as db:
        e=db.get(Empresa,empresa)
        assert e.resultados[0].detalhes_simulacao['engine_version']==ENGINE_VERSION
        # Histórico legado simulado apenas no banco isolado do teste.
        snapshot=deepcopy(e.resultados[0].detalhes_simulacao);snapshot.pop('engine_version')
        e.resultados[0].detalhes_simulacao=snapshot;db.commit()
    url=f'/api/professor/turmas/{turma["id"]}/relatorio'
    primeira=cliente.get(url,headers=professor).json()
    assert primeira['empresas'][0]['rodadas'][0]['engine_version']==LEGACY_ENGINE_VERSION
    with SessionLocal() as db:
        t=db.get(Turma,turma['id']);e=db.get(Empresa,empresa)
        assert e.resultados[0].detalhes_simulacao==snapshot
        antes=gerar_relatorio(t)['ranking'];pesos=gerar_relatorio(t)['rubrica']['pesos']
        atualizado=deepcopy(snapshot);atualizado['engine_version']=ENGINE_VERSION
        e.resultados[0].detalhes_simulacao=atualizado
        depois=gerar_relatorio(t)
        assert depois['ranking']==antes and depois['rubrica']['pesos']==pesos
        db.rollback()
    _decisao_avancada(cliente,aluno,empresa,2,producao=0)
    _fechar(cliente,professor,turma,2)
    historico=cliente.get(url,headers=professor).json()['empresas'][0]['rodadas']
    assert historico[0]==primeira['empresas'][0]['rodadas'][0]
    assert historico[1]['engine_version']==ENGINE_VERSION
    csv=cliente.get(url+'.csv',headers=professor)
    assert csv.status_code==200 and ENGINE_VERSION in csv.text and LEGACY_ENGINE_VERSION in csv.text
