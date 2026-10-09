from .decisoes import completar_decisao
from copy import deepcopy
import pytest
from .conftest import cadastrar
from .test_fluxo import _criar_turma, _entrar
from .test_mercado import edicao


def preparar(cliente,professor,monkeypatch,modo='TRADICIONAL'):
    from app.routers import mercado
    cat=edicao();p=deepcopy(cat['produtos'][0]);p.update(id='produto-2',nome='Produto dois',custo_unitario=80);cat['produtos'].append(p)
    if modo=='STARTUP':
        for p in cat['produtos']:p.update(natureza='SERVICO_DIGITAL',unidade='cliente/mês')
    monkeypatch.setattr(mercado,'gerar_json',lambda *a:(cat,{'https://example.com/produto'}))
    turma=_criar_turma(cliente,professor,modo_jogo=modo,total_rodadas=3,demanda_base_por_empresa=20)
    aluno=cadastrar(cliente,'Ana',f'portfolio-{modo}@aluno.iffar.edu.br');empresa=_entrar(cliente,aluno,turma['codigo'],'Portfólio')
    url=f"/api/professor/turmas/{turma['id']}"
    r=cliente.post(url+'/mercado/pesquisar',headers=professor,json={'setor':'Eletrônicos e Tecnologia','noticias':1,'analises':1,'produtos':2});assert r.status_code==200,r.text
    eid=r.json()['id'];assert cliente.post(url+f'/mercado/{eid}/publicar',headers=professor,json={}).status_code==200
    mix={'estrategia_preco':'COMPETITIVO','posicionamento':'PRECO','canais':['DIRETO'],'cobertura':'LOCAL','intensidade':'BAIXA','midias':[]}
    plano={'edicao_id':eid,'produto_id':'produto-1',**mix,'produtos':[{'produto_id':'produto-1',**mix,'preco':100,'peso':1,'revisado':True},{'produto_id':'produto-2',**mix,'preco':200,'peso':1,'revisado':True}]}
    decisao={'rodada':1,'preco':1,'marketing':0,'plano_comercial':plano}
    if modo!='LEGADO':decisao['simulacao']={'producao':100,'comprar_mp':100,'capacidade_nuvem':100}
    return turma,aluno,empresa,url,eid,decisao


@pytest.mark.parametrize('modo',['TRADICIONAL','STARTUP','LEGADO'])
def test_portfolio_apura_sem_duplicar_caixa_ou_capacidade(cliente,professor,monkeypatch,modo):
    _,aluno,empresa,url,eid,d=preparar(cliente,professor,monkeypatch,modo)
    endpoint=f'/api/aluno/empresas/{empresa}/decisao'
    incompleto=deepcopy(d);incompleto['plano_comercial']['produtos'].pop()
    assert cliente.put(endpoint,headers=aluno,json=completar_decisao(incompleto)).status_code==422
    sem_revisao=deepcopy(d);sem_revisao['plano_comercial']['produtos'][1]['revisado']=False
    assert cliente.put(endpoint,headers=aluno,json=completar_decisao(sem_revisao)).status_code==422
    duplicado=deepcopy(d);duplicado['plano_comercial']['produtos'][1]['produto_id']='produto-1'
    assert cliente.put(endpoint,headers=aluno,json=completar_decisao(duplicado)).status_code==422
    d['plano_comercial']['produtos'][1]['custo_unitario']=.01
    r=cliente.put(endpoint,headers=aluno,json=completar_decisao(d));assert r.status_code==200,r.text
    assert r.json()['preco']==150
    assert r.json()['plano_comercial']['produtos'][1]['custo_unitario']==80
    assert cliente.post(url+'/fechar-rodada',headers=professor,json={'rodada':1,'evento':'NENHUM'}).status_code==200
    painel=cliente.get(f'/api/aluno/empresas/{empresa}',headers=aluno).json();resultado=painel['resultados'][0]
    linhas=resultado['produtos_resultado'];assert len(linhas)==2
    assert all(l['vendas']>0 for l in linhas)
    assert sum(l['vendas'] for l in linhas)==pytest.approx(resultado['unidades_vendidas'])
    assert sum(l['receita'] for l in linhas)==pytest.approx(resultado['dre']['receita'])
    assert sum(l['cmv'] for l in linhas)==pytest.approx(resultado['dre']['cmv'])
    if modo=='TRADICIONAL':
        estado=painel['empresa']['estado_simulacao'];stocks=estado['estoques_produtos']
        assert sum(s['estoque_pa']['quantidade'] for s in stocks.values())==estado['estoque_pa']['quantidade']
        assert sum(s['estoque_pa']['valor'] for s in stocks.values())==pytest.approx(estado['estoque_pa']['valor'])
        assert sum(l['vendas']+l['estoque_final']['quantidade'] for l in linhas)==100
    if modo!='LEGADO':
        b=resultado['detalhes_simulacao']['balanco'];dfc=resultado['detalhes_simulacao']['dfc']
        assert b['caixa']+b['receber']+b['estoques']+b['imobilizado']==pytest.approx(b['pagar']+b['divida']+b['patrimonio'],abs=.01)
        assert dfc['caixa_inicial']+dfc['variacao']==pytest.approx(dfc['caixa_final'],abs=.01)
    assert cliente.post(url+'/fechar-rodada',headers=professor,json={'rodada':2,'evento':'NENHUM'}).status_code==200
    final=cliente.get(f'/api/aluno/empresas/{empresa}',headers=aluno).json()
    assert final['resultados'][0]==resultado
    assert len(final['ultima_decisao']['plano_comercial']['produtos'])==2


def diagnostico():
    from app.schemas import AnalisesEstrategicas
    a=AnalisesEstrategicas().model_dump()
    for k in ['forcas','fraquezas','oportunidades','ameacas']:a['swot'][k]=['Observação fundamentada no mercado.']
    for k in ['politico','economico','social','tecnologico','ambiental','legal']:a['pestel'][k]=['Hipótese para analisar com as fontes.']
    for v in a['porter'].values():v.update(intensidade=7,justificativa='Concorrência observada nas condições informadas.')
    retorno = {k:a[k] for k in ['swot','porter','pestel']}
    retorno["concorrentes"]=[{"nome":"Concorrente de referência (projeção)","tipo":"REFERENCIA_PROJETADA",**{k:"Projeção: cenário de referência do setor para comparação didática." for k in ("perfil","porte_mercado","portfolio","diferencial","precos","promocoes","canais","presenca_digital","reputacao","ponto_fraco")},"fontes":[],"projecoes":[{"campo":"Preço","estimativa":"Projeção: referência de R$ 100","premissas":"Preço de referência do cenário usado como base; não representa uma empresa real."}]}]
    return retorno


def test_diagnostico_cache_autorizacao_e_protecao(cliente,professor,monkeypatch):
    from app.routers import mercado
    _,aluno,empresa,url,eid,d=preparar(cliente,professor,monkeypatch)
    chamadas=[]
    monkeypatch.setattr(mercado,'gerar_json',lambda *args, **kwargs:(chamadas.append(args) or diagnostico(),{"https://example.com/produto"}))
    endpoint=f'/api/aluno/empresas/{empresa}/diagnostico/{eid}'
    primeiro=cliente.post(endpoint,headers=aluno,json={});assert primeiro.status_code==200,primeiro.text
    assert cliente.post(endpoint,headers=aluno,json={}).json()==primeiro.json()
    assert len(chamadas)==1
    assert chamadas[0][2] is True
    assert "fontes_pesquisa" not in primeiro.json()["dados"]
    assert "fontes" not in primeiro.json()["dados"]["concorrentes"][0]
    assert "fontes_pesquisa" in cliente.get(url+f"/empresas/{empresa}/diagnosticos",headers=professor).json()[0]["dados"]
    outro=cadastrar(cliente,'Bia','privacidade@aluno.iffar.edu.br')
    assert cliente.post(endpoint,headers=outro,json={}).status_code in (403,404)
    docente=cliente.get(url+f'/empresas/{empresa}/diagnosticos',headers=professor)
    assert docente.status_code==200 and len(docente.json())==1
    d['plano_comercial']['analises']={'diagnostico_automatico':True,'swot':{'forcas':['Texto adulterado'],'diretriz':'PRECO'},'porter':{'rivalidade':{'intensidade':1}}}
    salvo=cliente.put(f'/api/aluno/empresas/{empresa}/decisao',headers=aluno,json=completar_decisao(d))
    assert salvo.status_code==200,salvo.text
    a=salvo.json()['plano_comercial']['analises']
    assert a['swot']['forcas']==primeiro.json()['dados']['swot']['forcas']
    assert a['swot']['diretriz']=='PRECO'
    assert a['porter']['rivalidade']['intensidade']==7
    assert a['diagnostico_automatico']


def test_diagnostico_invalido_pode_repetir(cliente,professor,monkeypatch):
    from app.routers import mercado
    _,aluno,empresa,url,eid,_=preparar(cliente,professor,monkeypatch)
    monkeypatch.setattr(mercado,'gerar_json',lambda *args, **kwargs:({'swot':{},'porter':{},'pestel':{}},set()))
    endpoint=f'/api/aluno/empresas/{empresa}/diagnostico/{eid}'
    assert cliente.post(endpoint,headers=aluno,json={}).status_code==502
    assert cliente.get(url+f'/empresas/{empresa}/diagnosticos',headers=professor).json()==[]
    monkeypatch.setattr(mercado,'gerar_json',lambda *args, **kwargs:(diagnostico(),{"https://example.com/produto"}))
    assert cliente.post(endpoint,headers=aluno,json={}).status_code==200


def test_manual_cobre_catalogo(cliente):
    campanhas=cliente.get('/api/educacao/campanhas').json()['midias']
    manual=cliente.get('/api/educacao/manual-midias').json()['midias']
    assert {m['id'] for m in campanhas}=={m['id'] for m in manual}
    assert all(len(m['descricao'])>40 and m['unidade'] and m['quando_usar'] for m in manual)
    assert 'não inclui' in next(m['descricao'] for m in manual if m['id']=='flyer-distribuicao')


def test_midias_por_produto_somadas_e_influenciam_distribuicao(cliente,professor,monkeypatch):
    from app.motor.portfolio import atrativos
    _,aluno,empresa,_,_,d=preparar(cliente,professor,monkeypatch)
    itens=d['plano_comercial']['produtos']
    itens[0]['midias']=[{'id':'email','quantidade':100}]
    itens[1]['midias']=[{'id':'email','quantidade':200}]
    for item in itens:item['servicos']=[{'id':'servico-email','quantidade':1}]
    d['marketing']=1126
    r=cliente.put(f'/api/aluno/empresas/{empresa}/decisao',headers=aluno,json=completar_decisao(d))
    assert r.status_code==200,r.text
    saved=r.json()['plano_comercial']['produtos']
    base=deepcopy(saved)
    for p in base:p.update(midias=[],custos_campanha=None)
    a=atrativos(saved,100,30);b=atrativos(base,100,30)
    assert a[1]/a[0]>b[1]/b[0]
    d['marketing']=12
    assert cliente.put(f'/api/aluno/empresas/{empresa}/decisao',headers=aluno,json=completar_decisao(d)).status_code==422


def test_estoque_historico_nao_e_clonado_no_portfolio():
    from app.motor.portfolio import produzir
    estado={'produto_estoque_original':'original','estoque_mp':{'quantidade':10,'valor':300},'estoque_pa':{'quantidade':7,'valor':210}}
    itens=[{'produto_id':'novo','peso':1,'custo_unitario':80},{'produto_id':'original','peso':1,'custo_unitario':30}]
    produzir(estado,itens,{'comprar_mp':0,'producao':0},100,100,1)
    assert estado['estoques_produtos']['original']['estoque_pa']=={'quantidade':7,'valor':210}
    assert estado['estoques_produtos']['novo']['estoque_pa']=={'quantidade':0,'valor':0}
    assert estado['estoque_pa']=={'quantidade':7,'valor':210}
