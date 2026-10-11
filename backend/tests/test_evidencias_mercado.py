import pytest
from fastapi import HTTPException
from app import evidencias_mercado as provas
from app.routers.mercado import Edicao
from .test_mercado import edicao
from .test_fluxo import _criar_turma


@pytest.fixture
def fonte(monkeypatch):
    html = '<meta property="article:published_time" content="2026-10-06T12:00:00"><main>Produto de teste R$ 30,00 por unidade ou cliente/mês.</main>'
    monkeypatch.setattr(provas, 'obter_documento', lambda url: provas.Documento(html))


def test_preco_com_nome_trecho_e_data_documentados(fonte):
    provas.validar_evidencias(Edicao.model_validate(edicao()))


@pytest.mark.parametrize('alteracao', ['custo', 'trecho', 'nome', 'url', 'data', 'sem_prova'])
def test_recusa_url_valida_sem_sustentacao_do_dado(fonte, alteracao):
    dados = edicao()
    p = dados['produtos'][0]
    if alteracao == 'custo': p['custo_unitario'] = 2200
    if alteracao == 'trecho': p['evidencia_custo']['trecho'] = 'Produto de teste R$ 2.200,00 no atacado.'
    if alteracao == 'nome': p['nome'] = 'Smartphone de Última Geração'
    if alteracao == 'url': p['evidencia_custo']['url'] = 'https://example.com/outra'
    if alteracao == 'data': dados['analises'][0]['data'] = '2026-03'
    if alteracao == 'sem_prova': p.pop('evidencia_custo')
    with pytest.raises(HTTPException) as erro:
        provas.validar_evidencias(Edicao.model_validate(dados))
    assert erro.value.status_code == 422


def test_salva_e_publica_estimativa_sem_prova(cliente, professor, monkeypatch, fonte):
    from app.routers import mercado
    from app.models import ConteudoMercado
    from app.database import SessionLocal
    dados = edicao(); dados['produtos'][0].pop('evidencia_custo')
    monkeypatch.setattr(mercado, 'gerar_json', lambda *a: (dados, {'https://example.com/produto'}))
    turma = _criar_turma(cliente, professor)
    base = f"/api/professor/turmas/{turma['id']}/mercado"
    r = cliente.post(base + '/pesquisar', headers=professor, json={'setor':dados['setor'],'noticias':1,'analises':1,'produtos':1})
    assert r.status_code == 200
    p = r.json()["dados"]["produtos"][0]
    assert p["estado_indicador"] == "Estimativa do Modelo"
    assert p["custo_unitario"] == turma["parametros"]["custo_unitario"]
    assert p["alerta_professor"]
    assert cliente.post(base + f'/{r.json()["id"]}/publicar', headers=professor, json={}).status_code == 200
    with SessionLocal() as db:
        e = ConteudoMercado(turma_id=turma['id'], rodada=1, dados=dados)
        db.add(e); db.commit(); eid = e.id
    assert cliente.post(base + f'/{eid}/publicar', headers=professor, json={}).status_code == 409
    assert any(e['publicado'] for e in cliente.get(base, headers=professor).json()['edicoes'])


def test_consulta_nao_e_data_de_publicacao(monkeypatch, fonte):
    from datetime import datetime, timezone
    dados = edicao()
    dados['produtos'][0]['data'] = 'Consulta em ' + datetime.now(timezone.utc).date().isoformat()
    provas.validar_evidencias(Edicao.model_validate(dados))
    dados['noticias'][0]['data'] = dados['produtos'][0]['data']
    with pytest.raises(HTTPException): provas.validar_evidencias(Edicao.model_validate(dados))


def test_datas_de_jsonld_e_conteudo_oculto():
    doc = provas.Documento('<script type="application/ld+json">{"datePublished":"2025-12-05T10:00:00"}</script><script>Produto falso R$ 2.200,00</script><main>Conteúdo do artigo</main>')
    assert doc.datas == {'2025-12-05'}
    assert '2.200' not in doc.texto


@pytest.mark.parametrize('ip', ['127.0.0.1', '10.0.0.1', '169.254.169.254', '::1'])
def test_fonte_privada_bloqueada_antes_da_conexao(monkeypatch, ip):
    monkeypatch.setattr(provas.socket, 'getaddrinfo', lambda *a, **k: [(None,None,None,None,(ip,443))])
    with pytest.raises(ValueError): provas.obter_documento('https://example.com/fonte')


def test_fonte_inacessivel_nao_vira_evidencia(monkeypatch):
    def falhar(url): raise OSError('offline')
    monkeypatch.setattr(provas, 'obter_documento', falhar)
    with pytest.raises(HTTPException) as erro: provas.validar_evidencias(Edicao.model_validate(edicao()))
    assert erro.value.status_code == 422


@pytest.mark.parametrize('tipo, custo, estado', [
    ('custo_aquisicao', 30, 'Valor Calculado'),
    ('preco_varejo', 18, 'Estimativa do Modelo'),
])
def test_tres_caminhos_sem_desconto_duplicado(fonte, tipo, custo, estado):
    from types import SimpleNamespace
    dados = Edicao.model_validate(edicao())
    dados.produtos[0].tipo_documento = tipo
    turma = SimpleNamespace(custo_unitario=40)
    for _ in range(2):
        provas.validar_evidencias(dados, turma)
        assert dados.produtos[0].custo_unitario == custo
        assert dados.produtos[0].estado_indicador == estado
        assert dados.produtos[0].valor_documentado == 30


@pytest.mark.parametrize('falha', ['nome', 'trecho', 'offline'])
def test_fallback_numerico_alerta_e_nao_finge_prova(fonte, monkeypatch, falha):
    from types import SimpleNamespace
    dados = Edicao.model_validate(edicao())
    dados.noticias = []; dados.analises = []
    if falha == 'nome': dados.produtos[0].nome = 'Outro produto'
    if falha == 'trecho': dados.produtos[0].evidencia_custo.trecho = 'Texto sem nenhum preço real'
    if falha == 'offline':
        def indisponivel(url): raise OSError('offline')
        monkeypatch.setattr(provas, 'obter_documento', indisponivel)
    provas.validar_evidencias(dados, SimpleNamespace(custo_unitario=40))
    p = dados.produtos[0]
    assert p.custo_unitario == 40
    assert p.estado_indicador == 'Estimativa do Modelo'
    assert p.valor_documentado is None and p.alerta_professor


def test_fallback_nao_relaxa_artigos_ou_links(fonte, monkeypatch):
    from types import SimpleNamespace
    turma = SimpleNamespace(custo_unitario=40)
    dados = Edicao.model_validate(edicao())
    dados.noticias[0].data = '2020-01-01'
    with pytest.raises(HTTPException): provas.validar_evidencias(dados, turma)
    dados.noticias = []; dados.analises = []
    def insegura(url): raise provas.FonteInsegura('Fonte não pública.')
    monkeypatch.setattr(provas, 'obter_documento', insegura)
    with pytest.raises(HTTPException): provas.validar_evidencias(dados, turma)
