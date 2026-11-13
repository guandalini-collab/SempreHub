from .decisoes import completar_decisao
"""Fluxos HTTP dos dois motores avançados e congelamento da configuração."""

from copy import deepcopy

from .conftest import cadastrar
from .test_fluxo import _criar_turma, _entrar


def _fechar(cliente, professor, turma, rodada):
    resposta = cliente.post(
        f"/api/professor/turmas/{turma['id']}/fechar-rodada",
        headers=professor,
        json={"evento": "NENHUM", "rodada": rodada},
    )
    assert resposta.status_code == 200, resposta.text
    return resposta


def _decisao_avancada(cliente, aluno, empresa_id, rodada, marketing=0, plano_comercial=None,
                       contratar=0, demitir=0, pd=0, **simulacao):
    # Os cenários antigos que planejam produção representam uma empresa em
    # operação: o fundador recebe pró-labore e compõe uma jornada júnior.
    # Marketing continua explícito porque, sem catálogo publicado, ele deve ser
    # bloqueado pelo motor sistêmico.
    if simulacao.get("producao", 0) > 0:
        simulacao.setdefault("pro_labore", 1_500)
    dados = {
        "rodada": rodada, "preco": 100, "marketing": marketing,
        "contratar": contratar, "demitir": demitir, "pd": pd,
        "simulacao": simulacao,
    }
    if plano_comercial is not None:
        dados["plano_comercial"] = plano_comercial
    resposta = cliente.put(
        f"/api/aluno/empresas/{empresa_id}/decisao",
        headers=aluno,
        json=completar_decisao(dados),
    )
    assert resposta.status_code == 200, resposta.text
    return resposta


def test_tradicional_preserva_estoque_e_snapshot_da_rodada(cliente, professor):
    turma = _criar_turma(
        cliente, professor, modo_jogo="TRADICIONAL", demanda_base_por_empresa=40,
        total_rodadas=2,
    )
    aluno = cadastrar(cliente, "Ana", "avancado-tradicional@aluno.iffar.edu.br")
    empresa_id = _entrar(cliente, aluno, turma["codigo"], "Fábrica")
    _decisao_avancada(cliente, aluno, empresa_id, 1, comprar_mp=100, producao=100)
    _fechar(cliente, professor, turma, 1)

    primeira = cliente.get(f"/api/aluno/empresas/{empresa_id}", headers=aluno).json()
    estado_primeiro = deepcopy(primeira["resultados"][0]["detalhes_simulacao"]["estado_final"])
    assert primeira["resultados"][0]["detalhes_simulacao"]["modo"] == "TRADICIONAL"
    assert estado_primeiro["estoque_pa"]["quantidade"] > 0
    assert primeira["resultados"][0]["detalhes_simulacao"]["dfc"]["investimento"] == 0

    _decisao_avancada(cliente, aluno, empresa_id, 2, producao=0)
    _fechar(cliente, professor, turma, 2)
    final = cliente.get(f"/api/aluno/empresas/{empresa_id}", headers=aluno).json()
    assert len(final["resultados"]) == 2
    assert final["resultados"][0]["detalhes_simulacao"]["estado_final"] == estado_primeiro
    assert final["resultados"][1]["detalhes_simulacao"]["estado_inicial"]["estoque_pa"]["quantidade"] == estado_primeiro["estoque_pa"]["quantidade"]
    # Sem catálogo e campanha publicados, estoque não gera demanda por conta
    # própria. O foco deste cenário é a integridade dos snapshots.
    assert final["resultados"][1]["detalhes_simulacao"]["operacao"]["vendas"] == 0


def test_startup_separa_aporte_de_receita_e_preserva_clientes_sem_nuvem(cliente, professor, monkeypatch):
    from app.routers import mercado
    from app.evidencias_mercado import Documento
    from .test_mercado import edicao

    monkeypatch.setattr(
        "app.evidencias_mercado.obter_documento",
        lambda url: Documento(
            '<meta property="article:published_time" content="2026-10-06">'
            '<main>Produto de teste R$ 30,00 por unidade ou cliente/mês.</main>'
        ),
    )
    catalogo = edicao()
    catalogo["produtos"][0].update(natureza="SERVICO_DIGITAL", unidade="cliente/mês")
    monkeypatch.setattr(mercado, "gerar_json", lambda *a: (catalogo, {"https://www.ibge.gov.br/produto"}))
    turma = _criar_turma(
        cliente, professor, modo_jogo="STARTUP", cenario="CRISE", demanda_base_por_empresa=100,
        total_rodadas=2,
    )
    aluno = cadastrar(cliente, "Bia", "avancado-startup@aluno.iffar.edu.br")
    empresa_id = _entrar(cliente, aluno, turma["codigo"], "Aplicativo")
    base_docente = f"/api/professor/turmas/{turma['id']}/mercado"
    pesquisa = cliente.post(
        base_docente + "/pesquisar", headers=professor,
        json={"setor": "Eletrônicos e Tecnologia", "noticias": 1, "analises": 1, "produtos": 1},
    )
    assert pesquisa.status_code == 200, pesquisa.text
    edicao_id = pesquisa.json()["id"]
    assert cliente.post(base_docente + f"/{edicao_id}/publicar", headers=professor, json={}).status_code == 200
    plano = {
        "edicao_id": edicao_id, "produto_id": "produto-1",
        "estrategia_preco": "VALOR", "posicionamento": "INOVACAO",
        "canais": ["ECOMMERCE"], "cobertura": "NACIONAL", "intensidade": "MEDIA",
        "midias": [{"id": "email", "quantidade": 100}],
        "produtos": [{
            "produto_id": "produto-1", "preco": 100, "peso": 1,
            "revisado": True, "estrategia_preco": "VALOR", "posicionamento": "INOVACAO",
            "canais": ["ECOMMERCE"], "cobertura": "NACIONAL", "intensidade": "MEDIA",
            "midias": [{"id": "email", "quantidade": 100}],
            "servicos": [{"id": "servico-email", "quantidade": 1}],
        }],
    }
    _decisao_avancada(
        cliente, aluno, empresa_id, 1, aporte=10_000, valuation=100_000,
        marketing=557, plano_comercial=plano, capacidade_nuvem=300,
        marketing_digital=100, pro_labore=1_500, contratar=1,
    )
    _fechar(cliente, professor, turma, 1)
    painel = cliente.get(f"/api/aluno/empresas/{empresa_id}", headers=aluno).json()
    resultado = painel["resultados"][0]
    operacao = resultado["detalhes_simulacao"]["operacao"]
    assert resultado["detalhes_simulacao"]["modo"] == "STARTUP"
    assert operacao["aporte"] == 10_000
    assert resultado["dre"]["receita"] != 10_000
    assert operacao["participacao_fundadores"] < 1
    # A capacidade contratada e o pró-labore cobrem a carteira inicial; o
    # importante aqui é que a operação não confunda aporte com receita.
    assert operacao["clientes_nao_atendidos"] == 0
    assert painel["empresa"]["estado_simulacao"]["clientes"] == operacao["clientes_finais"]


def test_modo_configuracao_e_cenario_ficam_congelados_apos_primeira_empresa(cliente, professor):
    turma = _criar_turma(cliente, professor, modo_jogo="TRADICIONAL", cenario="ZERO")
    aluno = cadastrar(cliente, "Caio", "avancado-config@aluno.iffar.edu.br")
    _entrar(cliente, aluno, turma["codigo"], "Oficina")
    resposta = cliente.put(
        f"/api/professor/turmas/{turma['id']}/parametros",
        headers=professor,
        json={"modo_jogo": "STARTUP", "cenario": "CRISE"},
    )
    assert resposta.status_code == 422
