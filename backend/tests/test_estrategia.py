from copy import deepcopy
from types import SimpleNamespace
import pytest
from pydantic import ValidationError
from app.motor.estrategia import avaliar, quadrante
from app.schemas import AnalisesEstrategicas
from .conftest import cadastrar
from .test_fluxo import _criar_turma, _entrar
from .test_mercado import edicao


def test_quadrantes_bcg_e_limites():
    assert quadrante(10, 1) == 'ESTRELA'
    assert quadrante(9.99, 1) == 'VACA'
    assert quadrante(10, .99) == 'INTERROGACAO'
    assert quadrante(-10, .99) == 'ABACAXI'


def test_criterios_independentes_cap_e_nao_muta():
    analises = AnalisesEstrategicas.model_validate({'swot': {'diretriz': 'INOVACAO'}, 'porter': {'rivalidade': {'intensidade': 1}}, 'bcg': [{'produto_id': 'p', 'nome': 'p', 'crescimento': 5, 'participacao': .8, 'classificacao': 'ESTRELA'}], 'pestel': {'juros_previstos': 0}, 'segmentacao': {'preco_maximo': 30, 'cobertura': 'LOCAL', 'canais': ['VAREJO'], 'midias': ['jornal']}}).model_dump()
    plano = {'produto_id': 'p', 'posicionamento': 'PRECO', 'cobertura': 'NACIONAL', 'canais': ['ECOMMERCE'], 'midias': [{'id': 'email'}], 'analises': analises}
    antes = deepcopy(plano)
    turma = SimpleNamespace(configuracao_simulacao={'nivel_concorrencia': 'ALTA'}, taxa_juros_mensal=.03)
    d = SimpleNamespace(plano_comercial=plano, preco=100, emprestimo=1000)
    r = avaliar(d, turma)
    assert {a['ferramenta'] for a in r['achados']} == {'SWOT', 'PORTER', 'BCG', 'PESTEL', 'SEGMENTACAO'}
    assert r['fator'] == .8
    assert len(r['achados']) == 8
    assert plano == antes
    d.plano_comercial = {'estrategias': {'SWOT': 'Texto antigo preservado'}}
    assert avaliar(d, turma)['fator'] == 1
    assert not avaliar(d, turma)['avaliada']


def test_dados_invalidos_rejeitados():
    for dado in ({'porter': {'rivalidade': {'intensidade': 11}}}, {'segmentacao': {'preco_maximo': float('nan')}}, {'swot': {'forcas': ['x' * 2001]}}):
        with pytest.raises(ValidationError):
            AnalisesEstrategicas.model_validate(dado)


@pytest.mark.parametrize('modo', ['LEGADO', 'TRADICIONAL', 'STARTUP'])
def test_segmentacao_afeta_vendas_e_resultado_preserva_historico(cliente, professor, monkeypatch, modo):
    from app.routers import mercado
    catalogo = edicao()
    if modo == 'STARTUP':
        catalogo['produtos'][0].update(natureza='SERVICO_DIGITAL', unidade='cliente/mês')
    monkeypatch.setattr(mercado, 'gerar_json', lambda *a: (catalogo, {'https://example.com/produto'}))
    turma = _criar_turma(cliente, professor, modo_jogo=modo, total_rodadas=2, demanda_base_por_empresa=100)
    alunos = [cadastrar(cliente, 'Ana', f'estrategia-{modo}-{i}@aluno.iffar.edu.br') for i in range(2)]
    empresas = [_entrar(cliente, aluno, turma['codigo'], f'Empresa {i}') for i, aluno in enumerate(alunos)]
    docente = f"/api/professor/turmas/{turma['id']}"
    r = cliente.post(docente + '/mercado/pesquisar', headers=professor, json={'setor': 'Eletrônicos e Tecnologia', 'noticias': 1, 'analises': 1, 'produtos': 1})
    assert r.status_code == 200, r.text
    eid = r.json()['id']
    assert cliente.post(docente + f'/mercado/{eid}/publicar', headers=professor, json={}).status_code == 200
    for i, (aluno, empresa) in enumerate(zip(alunos, empresas)):
        plano = {'edicao_id': eid, 'produto_id': 'produto-1', 'estrategia_preco': 'COMPETITIVO', 'posicionamento': 'PRECO', 'canais': ['DIRETO'], 'cobertura': 'LOCAL', 'intensidade': 'BAIXA', 'midias': [], 'analises': {'segmentacao': {'preco_maximo': 120 if i == 0 else 30}}}
        decisao = {'rodada': 1, 'preco': 100, 'plano_comercial': plano}
        if modo != 'LEGADO':
            decisao['simulacao'] = {'producao': 200, 'comprar_mp': 200, 'capacidade_nuvem': 300}
        r = cliente.put(f'/api/aluno/empresas/{empresa}/decisao', headers=aluno, json=decisao)
        assert r.status_code == 200, r.text
        assert r.json()['plano_comercial']['analises']['segmentacao']['preco_maximo'] == (120 if i == 0 else 30)
    assert cliente.post(docente + '/fechar-rodada', headers=professor, json={'rodada': 1, 'evento': 'NENHUM'}).status_code == 200
    resultados = [cliente.get(f'/api/aluno/empresas/{empresa}', headers=aluno).json()['resultados'][0] for aluno, empresa in zip(alunos, empresas)]
    bom, ruim = resultados
    assert bom['demanda'] > ruim['demanda']
    assert bom['unidades_vendidas'] > ruim['unidades_vendidas']
    assert bom['dre']['receita'] > ruim['dre']['receita']
    assert bom['dre']['lucro_liquido'] > ruim['dre']['lucro_liquido']
    assert any('público-alvo' in a for a in ruim['alertas'])
    if modo != 'LEGADO':
        assert ruim['detalhes_simulacao']['avaliacao_estrategica']['fator'] == .95
    assert cliente.post(docente + '/fechar-rodada', headers=professor, json={'rodada': 2, 'evento': 'NENHUM'}).status_code == 200
    final = cliente.get(f'/api/aluno/empresas/{empresas[1]}', headers=alunos[1]).json()
    assert final['resultados'][0] == ruim
    assert final['ultima_decisao']['plano_comercial']['analises']['segmentacao']['preco_maximo'] == 30


def test_efeito_nao_desaparece_com_uma_unica_empresa():
    from app.motor.avancado import _mercado
    from app.motor.simulacao import _dividir_mercado
    turma = SimpleNamespace(configuracao_simulacao={}, demanda_base_por_empresa=100, crescimento_mercado_mensal=0, preco_referencia=100, taxa_juros_mensal=.025)
    d = SimpleNamespace(preco=100, emprestimo=0, plano_comercial={'analises': {'segmentacao': {'preco_maximo': 30}}})
    p = {'atratividade': 1, 'avaliacao_estrategica': {'fator': .95}}
    demandas, bots = _mercado([p], [d], turma, 1, 1)
    assert demandas == [95]
    assert bots == []
    c = SimpleNamespace(decisao=d, atratividade=1, capacidade=200, alertas=[])
    _dividir_mercado([c], turma, 1, 1)
    assert c.demanda == 95
    assert c.vendas == 95
