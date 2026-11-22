from .decisoes import completar_decisao
from copy import deepcopy
import pytest
from .conftest import cadastrar
from .test_fluxo import _criar_turma, _entrar
from .test_mercado import edicao, fontes_documentadas


def preparar(cliente,professor,monkeypatch,modo='TRADICIONAL'):
    from app.routers import mercado
    cat=edicao();p=deepcopy(cat['produtos'][0]);p.update(id='produto-2',nome='Produto dois',custo_unitario=80,evidencia_custo={'url':'https://www.ibge.gov.br/produto','trecho':'Produto dois R$ 80,00 por unidade ou cliente/mês.'});cat['produtos'].append(p)
    if modo=='STARTUP':
        for p in cat['produtos']:p.update(natureza='SERVICO_DIGITAL',unidade='cliente/mês')
    monkeypatch.setattr(mercado,'gerar_json',lambda *a:(cat,{'https://www.ibge.gov.br/produto'}))
    turma=_criar_turma(cliente,professor,modo_jogo=modo,total_rodadas=3,demanda_base_por_empresa=20)
    aluno=cadastrar(cliente,'Ana',f'portfolio-{modo}@aluno.iffar.edu.br');empresa=_entrar(cliente,aluno,turma['codigo'],'Portfólio')
    url=f"/api/professor/turmas/{turma['id']}"
    r=cliente.post(url+'/mercado/pesquisar',headers=professor,json={'setor':'Pet Shop','noticias':1,'analises':1,'produtos':2});assert r.status_code==200,r.text
    eid=r.json()['id'];assert cliente.post(url+f'/mercado/{eid}/publicar',headers=professor,json={}).status_code==200
    mix={'estrategia_preco':'COMPETITIVO','posicionamento':'PRECO','canais':['DIRETO'],'cobertura':'LOCAL','intensidade':'BAIXA','midias':[{'id':'email','quantidade':100}]}
    # Startup usa produtos da pesquisa; os demais modos, o catálogo fixo (Pet Shop).
    p1,p2=('produto-1','produto-2') if modo=='STARTUP' else ('pet-brinquedo','pet-guia')
    plano={'edicao_id':eid,'produto_id':p1,**mix,'produtos':[{'produto_id':p1,**mix,'preco':100,'peso':1,'revisado':True,'servicos':[{'id':'servico-email','quantidade':1}]},{'produto_id':p2,**mix,'preco':200,'peso':1,'revisado':True,'servicos':[{'id':'servico-email','quantidade':1}]}]}
    # Duas linhas comercializadas exigem duas campanhas auditáveis.
    decisao={'rodada':1,'preco':1,'marketing':1114,'plano_comercial':plano}
    if modo == 'TRADICIONAL':
        # Empresa física minimamente operante: fundador remunerado, insumo,
        # capacidade de fábrica já instalada e verba de escoamento.
        decisao.update(contratar_tecnicos=1)
        decisao['simulacao']={
            'producao':100, 'comprar_mp':100, 'pro_labore':2_000,
            'orcamento_logistico':10_000,
        }
    elif modo == 'STARTUP':
        # A nuvem não substitui atendimento humano; o fundador ativo faz parte
        # da capacidade inicial do SaaS.
        decisao.update(contratar=1)
        decisao['simulacao']={'capacidade_nuvem':300,'pro_labore':2_000}
    return turma,aluno,empresa,url,eid,decisao


@pytest.mark.parametrize('modo',['TRADICIONAL','STARTUP','LEGADO'])
def test_portfolio_apura_sem_duplicar_caixa_ou_capacidade(cliente,professor,monkeypatch,modo):
    _,aluno,empresa,url,eid,d=preparar(cliente,professor,monkeypatch,modo)
    endpoint=f'/api/aluno/empresas/{empresa}/decisao'
    produtos=d['plano_comercial']['produtos']
    if modo=='STARTUP':
        incompleto=deepcopy(d);incompleto['plano_comercial']['produtos'].pop()
        assert cliente.put(endpoint,headers=aluno,json=completar_decisao(incompleto)).status_code==422
    else:
        # Catálogo fixo: a equipe escolhe o sortimento, mas só itens do setor.
        fora=deepcopy(d);fora['plano_comercial']['produtos'][1]['produto_id']='moveis-mesa-em-l'
        assert cliente.put(endpoint,headers=aluno,json=completar_decisao(fora)).status_code==422
    duplicado=deepcopy(d);duplicado['plano_comercial']['produtos'][1]['produto_id']=produtos[0]['produto_id']
    assert cliente.put(endpoint,headers=aluno,json=completar_decisao(duplicado)).status_code==422
    # A confirmação visual por produto deixou de ser obrigatória; o conteúdo continua validado.
    for produto in d['plano_comercial']['produtos']:
        produto['revisado'] = False
    d['plano_comercial']['produtos'][1]['custo_unitario']=.01
    r=cliente.put(endpoint,headers=aluno,json=completar_decisao(d));assert r.status_code==200,r.text
    assert r.json()['preco']==150
    assert r.json()['plano_comercial']['produtos'][1]['custo_unitario']==(80 if modo=='STARTUP' else 26.09)
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
        op=resultado['detalhes_simulacao']['operacao']
        # Revenda do catálogo (21/11/2026): o que foi comprado é vendido ou fica
        # em estoque; não há produção nem refugo.
        comprado=sum(c['comprado'] for c in estado['portfolio_compras'])
        assert comprado==100
        assert sum(l['vendas']+l['estoque_final']['quantidade'] for l in linhas)==comprado
        assert op['producao_real']==0 and op['refugo']==0
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
    monkeypatch.setattr(mercado,'gerar_json',lambda *args, **kwargs:(chamadas.append(args) or diagnostico(),{"https://www.ibge.gov.br/produto"}))
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
    monkeypatch.setattr(mercado,'gerar_json',lambda *args, **kwargs:(diagnostico(),{"https://www.ibge.gov.br/produto"}))
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
    igual=deepcopy(saved)
    igual[1]['midias']=[{'id':'email','quantidade':100}]
    a=atrativos(saved,100,30);b=atrativos(igual,100,30)
    # O produto com o dobro de mídia ganha participação (elasticidade 0,12).
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


def test_catalogo_propaganda_persiste_e_caixa_rende_selic(cliente,professor,monkeypatch):
    """Itens A, B e C (17/11/2026) no fechamento do modo Tradicional."""
    from .decisoes import completar_decisao
    turma,aluno,empresa,url,eid,d=preparar(cliente,professor,monkeypatch)
    base=f'/api/aluno/empresas/{empresa}'
    r=cliente.put(base+'/decisao',headers=aluno,json=completar_decisao(d));assert r.status_code==200,r.text
    f=cliente.post(url+'/fechar-rodada',headers=professor,json={'rodada':1,'evento':'NENHUM'});assert f.status_code==200,f.text
    res=cliente.get(base,headers=aluno).json()['resultados'][0]
    det=res['detalhes_simulacao']
    prop=det['configuracao']['propaganda']
    assert prop['persistencia']==.44 and prop['media']>0
    assert set(prop['estoques'])=={'pet-brinquedo','pet-guia'}
    op=det['operacao']
    assert op['taxa_aplicacao']>0 and op['rendimento_aplicacao']>0
    assert res['dre']['rendimento_aplicacao']==-op['rendimento_aplicacao']
    assert res['dre']['armazenagem']==0
    assert op['custo_oportunidade_estoque']==round(op['estoque_medio']*op['taxa_aplicacao'],2)
    # Mês seguinte sem propaganda: o estoque do mês anterior persiste (× 0,44)
    # e a loja continua disputando clientes (fator exp(0) = 1 no limite).
    estoques_1=prop['estoques']
    sem=deepcopy(d);sem['rodada']=2
    for item in sem['plano_comercial']['produtos']:item['midias']=[];item['servicos']=[]
    sem['plano_comercial']['midias']=[];sem['marketing']=0
    r=cliente.put(base+'/decisao',headers=aluno,json=completar_decisao(sem))
    assert r.status_code==200,r.text
    f=cliente.post(url+'/fechar-rodada',headers=professor,json={'rodada':2,'evento':'NENHUM'});assert f.status_code==200,f.text
    res2=cliente.get(base,headers=aluno).json()['resultados'][1]
    prop2=res2['detalhes_simulacao']['configuracao']['propaganda']
    for pid,valor in estoques_1.items():
        assert prop2['estoques'][pid]==pytest.approx(.44*valor)
    assert res2['detalhes_simulacao']['operacao']['comercial_ativo'] is True
    assert res2['demanda']>0
    # Item 2c: sem penalidade de 25% por posicionamento no catálogo.
    assert not any('atratividade reduzida em 25%' in a for a in res['alertas'])
    # Item 2: com catálogo fixo, a mídia não alimenta a marca.
    assert res['marca']==res2['marca']==0
    # Item 2e: no catálogo, o estado guarda o nível de serviço (OTIF) e a
    # satisfação não multiplica a atratividade.
    painel=cliente.get(base,headers=aluno).json()
    servico=painel['empresa']['estado_simulacao']['nivel_servico']
    assert 0<=servico['otif']<=1 and 0<=servico['taxa_ruptura']<=1
    # Resposta à falta (18/11/2026): a carteira de pedidos pendentes fica no
    # estado e o fechamento registra o destino dos clientes sem produto.
    assert isinstance(painel['empresa']['estado_simulacao']['pedidos_pendentes'], dict)
    assert 'resposta_ruptura' in res2['detalhes_simulacao']['operacao']


def test_revenda_compra_mercadoria_sem_maquina(cliente,professor,monkeypatch):
    """Revenda aprovada em 21/11/2026: loja de catálogo começa sem máquina e a
    mercadoria comprada entra direto no estoque, ao custo do catálogo."""
    from .decisoes import completar_decisao
    from app.routers import mercado
    cat=edicao();monkeypatch.setattr(mercado,'gerar_json',lambda *a:(cat,{'https://www.ibge.gov.br/produto'}))
    turma=_criar_turma(cliente,professor,modo_jogo='TRADICIONAL',total_rodadas=3,demanda_base_por_empresa=20,
                       configuracao_simulacao={'fabrica_inicial':False})
    aluno=cadastrar(cliente,'Bia','revenda@aluno.iffar.edu.br');empresa=_entrar(cliente,aluno,turma['codigo'],'Revenda')
    url=f"/api/professor/turmas/{turma['id']}"
    eid=cliente.post(url+'/mercado/pesquisar',headers=professor,json={'setor':'Pet Shop','noticias':1,'analises':1,'produtos':2}).json()['id']
    assert cliente.post(url+f'/mercado/{eid}/publicar',headers=professor,json={}).status_code==200
    base=f'/api/aluno/empresas/{empresa}'
    assert cliente.get(base,headers=aluno).json()['empresa']['estado_simulacao']['maquinas']==[]
    mix={'estrategia_preco':'COMPETITIVO','posicionamento':'PRECO','canais':['DIRETO'],'cobertura':'LOCAL','intensidade':'BAIXA','midias':[{'id':'email','quantidade':100}]}
    plano={'edicao_id':eid,'produto_id':'pet-brinquedo',**mix,'produtos':[{'produto_id':pid,**mix,'preco':preco,'peso':1,'revisado':True,'servicos':[{'id':'servico-email','quantidade':1}]} for pid,preco in (('pet-brinquedo',59),('pet-guia',43))]}
    d={'rodada':1,'preco':1,'marketing':1114,'plano_comercial':plano,
       'simulacao':{'comprar_insumos_por_produto':{'pet-brinquedo':30,'pet-guia':10},'pro_labore':2000,'orcamento_logistico':10000}}
    dec=completar_decisao(d);dec['pd']=5000  # revenda: P&D desconsiderado
    r=cliente.put(base+'/decisao',headers=aluno,json=dec);assert r.status_code==200,r.text
    custos={p['produto_id']:p['custo_unitario'] for p in r.json()['plano_comercial']['produtos']}
    assert cliente.post(url+'/fechar-rodada',headers=professor,json={'rodada':1,'evento':'NENHUM'}).status_code==200
    painel=cliente.get(base,headers=aluno).json();res=painel['resultados'][0];estado=painel['empresa']['estado_simulacao']
    compras={c['produto_id']:c for c in estado['portfolio_compras']}
    assert compras['pet-brinquedo']['comprado']==30 and compras['pet-guia']['comprado']==10
    # Sem desconto por volume: custo do catálogo.
    assert compras['pet-brinquedo']['custo_unitario']==custos['pet-brinquedo']
    op=res['detalhes_simulacao']['operacao']
    assert op['producao_real']==0 and op['refugo']==0
    for l in res['produtos_resultado']:
        assert l['vendas']+l['estoque_final']['quantidade']==compras[l['produto_id']]['comprado']
    assert res['dre'].get('depreciacao',0)==0
    assert res['dre'].get('pd',0)==0
    # Estoque médio a custo sempre registrado (giro e GMROI do comprador; Levy; Grewal, 2026)
    assert op['estoque_medio']==round((0+sum(l['estoque_final']['valor'] for l in res['produtos_resultado']))/2,2)
    assert any('P&D foi desconsiderado' in a for a in res.get('alertas',[]))


def test_revenda_estoque_medio_com_sobra(cliente,professor,monkeypatch):
    """Giro e GMROI do comprador usam o estoque médio a custo [(inicial + final) ÷ 2]
    (Levy; Grewal, 2026, p. 324-325); com sobra de mercadoria ele é positivo."""
    from .decisoes import completar_decisao
    from app.routers import mercado
    cat=edicao();monkeypatch.setattr(mercado,'gerar_json',lambda *a:(cat,{'https://www.ibge.gov.br/produto'}))
    turma=_criar_turma(cliente,professor,modo_jogo='TRADICIONAL',total_rodadas=3,demanda_base_por_empresa=20,
                       configuracao_simulacao={'fabrica_inicial':False})
    aluno=cadastrar(cliente,'Caio','sobra@aluno.iffar.edu.br');empresa=_entrar(cliente,aluno,turma['codigo'],'Sobra')
    url=f"/api/professor/turmas/{turma['id']}"
    eid=cliente.post(url+'/mercado/pesquisar',headers=professor,json={'setor':'Pet Shop','noticias':1,'analises':1,'produtos':2}).json()['id']
    assert cliente.post(url+f'/mercado/{eid}/publicar',headers=professor,json={}).status_code==200
    base=f'/api/aluno/empresas/{empresa}'
    mix={'estrategia_preco':'COMPETITIVO','posicionamento':'PRECO','canais':['DIRETO'],'cobertura':'LOCAL','intensidade':'BAIXA','midias':[{'id':'email','quantidade':100}]}
    plano={'edicao_id':eid,'produto_id':'pet-brinquedo',**mix,'produtos':[{'produto_id':pid,**mix,'preco':preco,'peso':1,'revisado':True,'servicos':[{'id':'servico-email','quantidade':1}]} for pid,preco in (('pet-brinquedo',59),('pet-guia',43))]}
    d={'rodada':1,'preco':1,'marketing':1114,'plano_comercial':plano,
       'simulacao':{'comprar_insumos_por_produto':{'pet-brinquedo':3000,'pet-guia':3000},'compras_prazo':1,'pro_labore':2000,'orcamento_logistico':10000}}
    r=cliente.put(base+'/decisao',headers=aluno,json=completar_decisao(d));assert r.status_code==200,r.text
    assert cliente.post(url+'/fechar-rodada',headers=professor,json={'rodada':1,'evento':'NENHUM'}).status_code==200
    res=cliente.get(base,headers=aluno).json()['resultados'][0]
    final=sum(l['estoque_final']['valor'] for l in res['produtos_resultado'])
    assert final>0
    assert res['detalhes_simulacao']['operacao']['estoque_medio']==round(final/2,2)


def test_curva_abc_planilha(cliente,professor,monkeypatch):
    """Planilha da curva ABC: produtos em ordem de vendas, cortes editáveis e fórmulas
    (Levy; Grewal, 2026, p. 347-348)."""
    from io import BytesIO
    from openpyxl import load_workbook
    from .decisoes import completar_decisao
    from app.routers import mercado
    cat=edicao();monkeypatch.setattr(mercado,'gerar_json',lambda *a:(cat,{'https://www.ibge.gov.br/produto'}))
    turma=_criar_turma(cliente,professor,modo_jogo='TRADICIONAL',total_rodadas=3,demanda_base_por_empresa=20,
                       configuracao_simulacao={'fabrica_inicial':False})
    aluno=cadastrar(cliente,'Bia','abc@aluno.iffar.edu.br');empresa=_entrar(cliente,aluno,turma['codigo'],'Loja ABC')
    url=f"/api/professor/turmas/{turma['id']}"
    eid=cliente.post(url+'/mercado/pesquisar',headers=professor,json={'setor':'Pet Shop','noticias':1,'analises':1,'produtos':2}).json()['id']
    assert cliente.post(url+f'/mercado/{eid}/publicar',headers=professor,json={}).status_code==200
    base=f'/api/aluno/empresas/{empresa}'
    assert cliente.get(base+'/curva-abc.xlsx',headers=aluno).status_code==404
    mix={'estrategia_preco':'COMPETITIVO','posicionamento':'PRECO','canais':['DIRETO'],'cobertura':'LOCAL','intensidade':'BAIXA','midias':[{'id':'email','quantidade':100}]}
    plano={'edicao_id':eid,'produto_id':'pet-brinquedo',**mix,'produtos':[{'produto_id':pid,**mix,'preco':preco,'peso':1,'revisado':True,'servicos':[{'id':'servico-email','quantidade':1}]} for pid,preco in (('pet-brinquedo',59),('pet-guia',43))]}
    d={'rodada':1,'preco':1,'marketing':1114,'plano_comercial':plano,
       'simulacao':{'comprar_insumos_por_produto':{'pet-brinquedo':40,'pet-guia':10},'compras_prazo':1,'pro_labore':2000,'orcamento_logistico':10000}}
    assert cliente.put(base+'/decisao',headers=aluno,json=completar_decisao(d)).status_code==200
    assert cliente.post(url+'/fechar-rodada',headers=professor,json={'rodada':1,'evento':'NENHUM'}).status_code==200
    r=cliente.get(base+'/curva-abc.xlsx',headers=aluno)
    assert r.status_code==200 and 'spreadsheetml' in r.headers['content-type']
    wb=load_workbook(BytesIO(r.content))
    ws=wb['Curva ABC']
    assert ws['C4'].value==0.70 and ws['C5'].value==0.90
    assert ws['A8'].value==1 and ws['A9'].value==2
    assert ws['E8'].value>=ws['E9'].value  # ordem decrescente de vendas
    assert ws['L8'].value.startswith('=IF(OR(A8=1,J8<=$C$4)')
    assert 'Como usar' in wb.sheetnames


def test_compra_aceita_ate_60_produtos():
    """A compra por produto acompanha o limite do plano comercial (60), não 10."""
    from pydantic import ValidationError
    from app.schemas import DecisaoSimulacao
    def erros_do_campo(n):
        try:
            DecisaoSimulacao.model_validate({'comprar_insumos_por_produto': {f'p{i}': 1 for i in range(n)}})
            return []
        except ValidationError as e:
            return [x for x in e.errors() if x['loc'] and x['loc'][0] == 'comprar_insumos_por_produto']
    assert erros_do_campo(60) == []
    assert erros_do_campo(61)


def test_aviso_de_produtos_some_no_catalogo_fixo():
    from app.routers.mercado import _aviso_sobre_produtos
    assert _aviso_sobre_produtos("Sem evidência verificável de produtos físicos; campo produtos omitido conforme instrução de não pesquisar catálogo nesta turma.")
    assert not _aviso_sobre_produtos("Itens retirados porque a página citada não pôde ser conferida.")
