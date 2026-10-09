from .decisoes import completar_decisao
from copy import deepcopy
import pytest
from app.custos_campanhas import necessarios, orcamento, investimento_efetivo
from .test_portfolio import preparar


def contratar(d,midias,cotacoes=None):
    item=d['plano_comercial']['produtos'][0]
    item.update(midias=midias,servicos=[{'id':s['id'],'quantidade':s['quantidade']} for s in necessarios(midias)],servicos_cotados=cotacoes or [])
    d['marketing']=orcamento(midias,item['servicos'],cotacoes)['total']
    return d


def test_tv_producao_obrigatoria_nao_repetida_por_insercao(cliente,professor,monkeypatch):
    _,aluno,empresa,_,_,d=preparar(cliente,professor,monkeypatch)
    endpoint=f'/api/aluno/empresas/{empresa}/decisao'
    contratar(d,[{'id':'tv15','quantidade':2}])
    assert d['marketing']==39000
    for servicos in ([],d['plano_comercial']['produtos'][0]['servicos']*2,[{'id':'servico-tv15','quantidade':2}]):
        copia=deepcopy(d);copia['plano_comercial']['produtos'][0]['servicos']=servicos
        assert cliente.put(endpoint,headers=aluno,json=completar_decisao(copia)).status_code==422
    copia=deepcopy(d);copia['marketing']=36000
    assert cliente.put(endpoint,headers=aluno,json=completar_decisao(copia)).status_code==422
    d['plano_comercial']['custos_campanha']={'versao':2,'total':1,'investimento_efetivo':1000000}
    d['plano_comercial']['produtos'][0]['custos_campanha']={'total':1}
    d['plano_comercial']['produtos'][0]['servicos'][0]['preco_unitario']=1
    r=cliente.put(endpoint,headers=aluno,json=completar_decisao(d));assert r.status_code==200,r.text
    c=r.json()['plano_comercial']['produtos'][0]['custos_campanha']
    assert (c['veiculacao'],c['servicos'],c['total'])==(36000,3000,39000)
    assert c['detalhes_servicos'][0]['fonte']['url'].startswith('https://www.toranjafilms.com/')
    assert investimento_efetivo(r.json())==36000


@pytest.mark.parametrize('modo',['TRADICIONAL','STARTUP','LEGADO'])
def test_servicos_dre_caixa_snapshot_e_historico(cliente,professor,monkeypatch,modo):
    from app.servicos_midias import SERVICOS
    _,aluno,empresa,url,_,d=preparar(cliente,professor,monkeypatch,modo)
    contratar(d,[{'id':'radio-spot','quantidade':2}])
    r=cliente.put(f'/api/aluno/empresas/{empresa}/decisao',headers=aluno,json=completar_decisao(d));assert r.status_code==200,r.text
    assert cliente.post(url+'/fechar-rodada',headers=professor,json={'rodada':1,'evento':'NENHUM'}).status_code==200
    painel=cliente.get(f'/api/aluno/empresas/{empresa}',headers=aluno).json();r=painel['resultados'][0]
    assert r['dre']['marketing']==1199
    assert sum(p['custos_campanha']['total'] for p in r['produtos_resultado'])==1199
    assert sum(p['custos_campanha']['servicos'] for p in r['produtos_resultado'])==199
    if modo!='LEGADO':
        b=r['detalhes_simulacao']['balanco'];dfc=r['detalhes_simulacao']['dfc']
        assert b['caixa']+b['receber']+b['estoques']+b['imobilizado']==pytest.approx(b['pagar']+b['divida']+b['patrimonio'],abs=.01)
        assert dfc['caixa_inicial']+dfc['variacao']==pytest.approx(dfc['caixa_final'],abs=.01)
    alterado=deepcopy(SERVICOS['radio-spot']);alterado[0]['preco_unitario']=999
    monkeypatch.setitem(SERVICOS,'radio-spot',alterado)
    assert cliente.post(url+'/fechar-rodada',headers=professor,json={'rodada':2,'evento':'NENHUM'}).status_code==200
    novo=cliente.get(f'/api/aluno/empresas/{empresa}',headers=aluno).json()
    assert novo['resultados'][0]==r
    assert novo['resultados'][1]['dre']['marketing']==1199


def test_dependencias_panfletos_e_jingle(cliente,professor,monkeypatch):
    _,aluno,empresa,_,_,d=preparar(cliente,professor,monkeypatch)
    endpoint=f'/api/aluno/empresas/{empresa}/decisao'
    for midias in [[{'id':'flyer-impressao','quantidade':1000}],[{'id':'flyer-impressao','quantidade':1000},{'id':'flyer-distribuicao','quantidade':999}],[{'id':'jingle','quantidade':1}]]:
        contratar(d,midias)
        assert cliente.put(endpoint,headers=aluno,json=completar_decisao(d)).status_code==422
    contratar(d,[{'id':'flyer-impressao','quantidade':1000},{'id':'flyer-distribuicao','quantidade':1000}])
    assert d['marketing']==750
    assert cliente.put(endpoint,headers=aluno,json=completar_decisao({**d, 'rascunho': True})).status_code==200
    contratar(d,[{'id':'jingle','quantidade':1},{'id':'radio-spot','quantidade':3}])
    assert d['marketing']==3900
    assert not d['plano_comercial']['produtos'][0]['servicos']
    r=cliente.put(endpoint,headers=aluno,json=completar_decisao(d));assert r.status_code==200,r.text
    assert investimento_efetivo(r.json())==1500


def test_orcamento_sem_preco_publico_e_obrigatorio(cliente,professor,monkeypatch):
    _,aluno,empresa,_,_,d=preparar(cliente,professor,monkeypatch)
    endpoint=f'/api/aluno/empresas/{empresa}/decisao'
    contratar(d,[{'id':'empena','quantidade':1}])
    assert cliente.put(endpoint,headers=aluno,json=completar_decisao(d)).status_code==422
    cotacoes=[{'midia_id':'empena','valor':8100.25,'fonte_url':'https://fornecedor.example/orcamento'}]
    contratar(d,[{'id':'empena','quantidade':1}],cotacoes)
    r=cliente.put(endpoint,headers=aluno,json=completar_decisao(d));assert r.status_code==200,r.text
    c=r.json()['plano_comercial']['produtos'][0]['custos_campanha']
    assert c['total']==53100.25
    assert c['detalhes_servicos'][0]['fonte']['titulo']=='Cotação informada pela equipe'
    for defeito in [[],cotacoes*2,[{**cotacoes[0],'midia_id':'tv30'}],[{**cotacoes[0],'valor':0}],[{**cotacoes[0],'fonte_url':'javascript:alert(1)'}]]:
        copia=deepcopy(d);copia['plano_comercial']['produtos'][0]['servicos_cotados']=defeito
        assert cliente.put(endpoint,headers=aluno,json=completar_decisao(copia)).status_code==422


def test_catalogo_preserva_tarifas_e_fontes(cliente):
    from app.catalogo_campanhas import CAMPANHAS
    m=cliente.get('/api/educacao/campanhas').json()['midias']
    assert {c['id']:c['preco_unitario'] for c in m}=={i:p for i,n,c,p,u in CAMPANHAS}
    assert len(m)==62
    for midia in m:
        assert midia['escopo_pacote']
        for s in midia['servicos_obrigatorios']:
            assert s['preco_unitario']>0 and s['fonte']['url'].startswith('https://') and s['fonte']['trecho']
            assert s['fonte']['data_consulta']=='07/10/2026'
    assert next(c for c in m if c['id']=='tv30')['servicos_obrigatorios'][0]['preco_unitario']==3000
    assert orcamento([{'id':'tv30','quantidade':3}],necessarios([{'id':'tv30','quantidade':3}]))['total']==93000


def test_historico_sem_v2_nao_ganha_tarifas_novas():
    antigo={'marketing':500,'plano_comercial':{'midias':[{'id':'radio-spot','quantidade':1}]}}
    assert investimento_efetivo(antigo)==500
