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


def _decisao_avancada(cliente, aluno, empresa_id, rodada, marketing=0, **simulacao):
    resposta = cliente.put(
        f"/api/aluno/empresas/{empresa_id}/decisao",
        headers=aluno,
        json={"rodada": rodada, "preco": 100, "marketing": marketing, "simulacao": simulacao},
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
    assert estado_primeiro["estoque_pa"]["quantidade"] == 60
    assert primeira["resultados"][0]["detalhes_simulacao"]["dfc"]["investimento"] == 0

    _decisao_avancada(cliente, aluno, empresa_id, 2, producao=0)
    _fechar(cliente, professor, turma, 2)
    final = cliente.get(f"/api/aluno/empresas/{empresa_id}", headers=aluno).json()
    assert len(final["resultados"]) == 2
    assert final["resultados"][0]["detalhes_simulacao"]["estado_final"] == estado_primeiro
    assert final["resultados"][1]["detalhes_simulacao"]["estado_inicial"]["estoque_pa"]["quantidade"] == 60
    assert final["resultados"][1]["detalhes_simulacao"]["operacao"]["vendas"] == 40


def test_startup_separa_aporte_de_receita_e_preserva_clientes_sem_nuvem(cliente, professor):
    turma = _criar_turma(
        cliente, professor, modo_jogo="STARTUP", cenario="CRISE", demanda_base_por_empresa=100,
        total_rodadas=2,
    )
    aluno = cadastrar(cliente, "Bia", "avancado-startup@aluno.iffar.edu.br")
    empresa_id = _entrar(cliente, aluno, turma["codigo"], "Aplicativo")
    _decisao_avancada(
        cliente, aluno, empresa_id, 1, aporte=10_000, valuation=100_000,
        marketing=100, capacidade_nuvem=20, marketing_digital=100,
    )
    _fechar(cliente, professor, turma, 1)
    painel = cliente.get(f"/api/aluno/empresas/{empresa_id}", headers=aluno).json()
    resultado = painel["resultados"][0]
    operacao = resultado["detalhes_simulacao"]["operacao"]
    assert resultado["detalhes_simulacao"]["modo"] == "STARTUP"
    assert operacao["aporte"] == 10_000
    assert resultado["dre"]["receita"] != 10_000
    assert operacao["participacao_fundadores"] < 1
    assert operacao["clientes_nao_atendidos"] > 0
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
