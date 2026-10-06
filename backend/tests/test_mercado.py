from .conftest import cadastrar
from .test_fluxo import _criar_turma, _entrar


def edicao():
    fonte={"titulo":"Fonte de aquisição","url":"https://example.com/produto"}
    artigo={"titulo":"Mercado brasileiro","texto":"Dados de mercado consultados para esta edição.","data":"2026-10-06","fontes":[fonte]}
    return {"setor":"Eletrônicos e Tecnologia","comercio":"B2C","noticias":[artigo],"analises":[artigo],"produtos":[{"id":"produto-1","nome":"Produto de teste","descricao":"Descrição de produto de teste","custo_unitario":30,"unidade":"unidade","base_custo":"Preço público de aquisição, não custo industrial.","data":"2026-10-06","fontes":[fonte]}]}


def test_revisao_publicacao_custo_e_historico(cliente,professor,monkeypatch):
    from app.routers import mercado
    monkeypatch.setattr(mercado,"gerar_json",lambda *a:(edicao(),{"https://example.com/produto"}))
    turma=_criar_turma(cliente,professor,total_rodadas=3)
    aluno=cadastrar(cliente,"Ana","ana@aluno.iffar.edu.br")
    outro=cadastrar(cliente,"Bia","bia@aluno.iffar.edu.br")
    empresa=_entrar(cliente,aluno,turma["codigo"],"Empresa Ana")
    docente=f"/api/professor/turmas/{turma['id']}/mercado"
    base=f"/api/aluno/empresas/{empresa}"
    r=cliente.post(docente+"/pesquisar",headers=professor,json={"setor":"Eletrônicos e Tecnologia","noticias":1,"analises":1,"produtos":1})
    assert r.status_code==200,r.text
    eid=r.json()["id"]
    assert cliente.get(base+"/mercado-real",headers=aluno).json()["edicoes"]==[]
    assert cliente.get(base+"/mercado-real",headers=outro).status_code==404
    assert cliente.get(docente,headers=aluno).status_code==403
    assert cliente.post(docente+f"/{eid}/publicar",headers=professor,json={}).status_code==200
    assert cliente.put(docente+f"/{eid}",headers=professor,json=edicao()).status_code==409
    plano={"edicao_id":eid,"produto_id":"produto-1","estrategia_preco":"COMPETITIVO","posicionamento":"PRECO","canais":["DIRETO"],"cobertura":"LOCAL","intensidade":"MEDIA","midias":[{"id":"email","quantidade":100}],"estrategias":{"SWOT":"Análise da equipe"},"custo_unitario":1}
    decisao={"preco":60,"marketing":12,"plano_comercial":plano}
    r=cliente.put(base+"/decisao",headers=aluno,json=decisao)
    assert r.status_code==200,r.text
    assert r.json()["plano_comercial"]["custo_unitario"]==30
    assert cliente.put(base+"/decisao",headers=aluno,json={**decisao,"marketing":1}).status_code==422
    assert cliente.post(f"/api/professor/turmas/{turma['id']}/fechar-rodada",headers=professor,json={"evento":"NENHUM"}).status_code==200
    painel=cliente.get(base,headers=aluno).json()
    resultado=painel["resultados"][0]
    assert abs(resultado["dre"]["cmv"]-resultado["unidades_vendidas"]*30)<.01
    assert cliente.get(base+"/mercado-real",headers=aluno).json()["edicoes"][0]["rodada"]==1
    # O catálogo anterior continua válido e seu custo não pode ser removido.
    assert cliente.put(base+"/decisao",headers=aluno,json={"preco":60}).status_code==422
    assert cliente.put(base+"/decisao",headers=aluno,json=decisao).status_code==200
    monkeypatch.setattr(mercado,"gerar_json",lambda *a:({"texto":"Relatório empresarial: a rodada registrou vendas e custos conforme os demonstrativos."},set()))
    caminho=f"/api/professor/turmas/{turma['id']}/empresas/{empresa}/relatorio-empresarial/1"
    assert cliente.post(caminho,headers=professor,json={}).status_code==200
    monkeypatch.setattr(mercado,"gerar_json",lambda *a:(_ for _ in ()).throw(AssertionError("Não deve gerar novamente")))
    assert cliente.post(caminho,headers=professor,json={}).status_code==200
    assert len(cliente.get(base+"/relatorios-empresariais",headers=aluno).json())==1


def test_recusa_fontes_nao_confirmadas(cliente,professor,monkeypatch):
    from app.routers import mercado
    monkeypatch.setattr(mercado,"gerar_json",lambda *a:(edicao(),set()))
    turma=_criar_turma(cliente,professor)
    base=f"/api/professor/turmas/{turma['id']}/mercado"
    assert cliente.post(base+"/pesquisar",headers=professor,json={"setor":"Eletrônicos","noticias":1,"analises":1,"produtos":1}).status_code==502
    assert cliente.get(base,headers=professor).json()["edicoes"]==[]


def test_concorrentes_externos_disputam_demanda_no_basico(cliente,professor):
    turma=_criar_turma(cliente,professor,configuracao_simulacao={"concorrentes_virtuais":5})
    aluno=cadastrar(cliente,"Ana","concorrencia-basico@aluno.iffar.edu.br")
    empresa=_entrar(cliente,aluno,turma["codigo"],"Empresa em competição")
    assert cliente.put(f"/api/aluno/empresas/{empresa}/decisao",headers=aluno,json={"preco":100}).status_code==200
    assert cliente.post(f"/api/professor/turmas/{turma['id']}/fechar-rodada",headers=professor,json={"evento":"NENHUM"}).status_code==200
    resultado=cliente.get(f"/api/aluno/empresas/{empresa}",headers=aluno).json()["resultados"][0]
    assert 0<resultado["participacao_mercado"]<.5
    balanco=resultado["balanco_basico"]
    assert abs(balanco["ativo_total"]-balanco["passivo_total"]-balanco["patrimonio_liquido"])<.01


def test_custo_catalogo_aplicado_servico_digital(cliente,professor,monkeypatch):
    from app.routers import mercado
    monkeypatch.setattr(mercado,"gerar_json",lambda *a:(edicao(),{"https://example.com/produto"}))
    turma=_criar_turma(cliente,professor,modo_jogo="STARTUP",cenario="CRISE")
    aluno=cadastrar(cliente,"Bia","catalogo-startup@aluno.iffar.edu.br")
    empresa=_entrar(cliente,aluno,turma["codigo"],"Serviço digital")
    docente=f"/api/professor/turmas/{turma['id']}/mercado"
    eid=cliente.post(docente+"/pesquisar",headers=professor,json={"setor":"Tecnologia","noticias":1,"analises":1,"produtos":1}).json()["id"]
    cliente.post(docente+f"/{eid}/publicar",headers=professor,json={})
    plano={"edicao_id":eid,"produto_id":"produto-1","estrategia_preco":"VALOR","posicionamento":"INOVACAO","canais":["ECOMMERCE"],"cobertura":"NACIONAL","intensidade":"BAIXA","midias":[]}
    resposta=cliente.put(f"/api/aluno/empresas/{empresa}/decisao",headers=aluno,json={"rodada":1,"preco":100,"plano_comercial":plano,"simulacao":{"capacidade_nuvem":300}})
    assert resposta.status_code==200,resposta.text
    assert resposta.json()["simulacao"]["canal"]=="DIGITAL"
    assert cliente.post(f"/api/professor/turmas/{turma['id']}/fechar-rodada",headers=professor,json={"rodada":1,"evento":"NENHUM"}).status_code==200
    resultado=cliente.get(f"/api/aluno/empresas/{empresa}",headers=aluno).json()["resultados"][0]
    assert resultado["unidades_vendidas"]>0
    assert abs(resultado["dre"]["cmv"]-resultado["unidades_vendidas"]*30)<.01


def test_integracao_organiza_citacoes_sem_inventar_fontes(monkeypatch):
    import io
    import json
    from app import inteligencia_mercado
    monkeypatch.setenv("OPENAI_API_KEY", "credencial-de-teste")
    respostas=iter([
        {"status":"completed","output":[{"content":[{"type":"output_text","text":"Aquisição documentada a R$ 30 por unidade.","annotations":[{"type":"url_citation","url":"https://example.com/produto"}]}]}]},
        {"status":"completed","output":[{"content":[{"type":"output_text","text":json.dumps(edicao())}]}]},
    ])
    requisicoes=[]
    def abrir(req,timeout):
        requisicoes.append(json.loads(req.data))
        return io.BytesIO(json.dumps(next(respostas)).encode())
    monkeypatch.setattr(inteligencia_mercado.urllib.request,"urlopen",abrir)
    dados,fontes=inteligencia_mercado.gerar_json("Pesquise produtos e devolva JSON",{},True)
    assert dados["produtos"][0]["custo_unitario"]==30
    assert fontes=={"https://example.com/produto"}
    assert requisicoes[0]["tools"][0]["type"]=="web_search_preview"
    assert requisicoes[1]["text"]["format"]["type"]=="json_object"
    assert "tools" not in requisicoes[1]
