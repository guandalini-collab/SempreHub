"""Relatórios leem rodadas encerradas, preservam evidências e isolam turmas."""

from copy import deepcopy
import csv
import io
import json
from types import SimpleNamespace

import pytest

from app.database import SessionLocal
from app.models import Empresa, Turma
from app.relatorios import gerar_relatorio, indicadores_rodada, relatorio_csv

from .conftest import cadastrar
from .test_equipes import _aprovar, _configurar, _criar_equipe, _fechar, _salvar
from .test_fluxo import _criar_turma, _entrar


def _url(turma_id, csv=False):
    return f"/api/professor/turmas/{turma_id}/relatorio" + (".csv" if csv else "")


def _fechar_individual(cliente, turma, professor):
    resposta = cliente.post(
        f"/api/professor/turmas/{turma['id']}/fechar-rodada",
        headers=professor, json={"evento": "NENHUM"},
    )
    assert resposta.status_code == 200, resposta.text


def test_relatorio_e_csv_restritos_ao_professor_da_turma(cliente, professor):
    turma = _criar_turma(cliente, professor)
    outro = cadastrar(cliente, "Outro docente", "relatorio-outro@iffar.edu.br", "PROFESSOR", "codigo-teste")
    aluno = cadastrar(cliente, "Aluno", "relatorio-aluno@aluno.iffar.edu.br")
    for csv_download in (False, True):
        url = _url(turma["id"], csv_download)
        assert cliente.get(url).status_code == 401
        assert cliente.get(url, headers=aluno).status_code == 403
        assert cliente.get(url, headers=outro).status_code == 404
        assert cliente.get(_url(99999, csv_download), headers=professor).status_code == 404
        assert cliente.get(url, headers=professor).status_code == 200


def test_turma_sem_rodadas_nao_recebe_pontuacao_inventada(cliente, professor):
    turma = _criar_turma(cliente, professor)
    aluno = cadastrar(cliente, "Ana", "relatorio-ana@aluno.iffar.edu.br")
    _entrar(cliente, aluno, turma["codigo"], "Empresa sem fechamento")
    relatorio = cliente.get(_url(turma["id"]), headers=professor).json()
    assert relatorio["rubrica"]["tipo"] == "PONTUACAO_DIDATICA"
    assert "não é nota institucional" in relatorio["rubrica"]["observacao"]
    assert relatorio["ranking"][0]["pontuacao_didatica"] is None
    assert relatorio["ranking"][0]["posicao"] is None
    assert relatorio["empresas"][0]["rodadas"] == []
    assert relatorio["empresas"][0]["resumo"]["patrimonio_sem_aportes"] is None


def test_historico_legado_sem_dfc_fabricada_ou_dados_atuais(cliente, professor):
    turma = _criar_turma(cliente, professor, total_rodadas=3)
    aluno = cadastrar(cliente, "Ana", "relatorio-legado@aluno.iffar.edu.br")
    empresa_id = _entrar(cliente, aluno, turma["codigo"], "Histórico Legado")
    resposta = cliente.put(f"/api/aluno/empresas/{empresa_id}/decisao", headers=aluno, json={"preco": 95})
    assert resposta.status_code == 200
    _fechar_individual(cliente, turma, professor)
    relatorio = cliente.get(_url(turma["id"]), headers=professor).json()
    primeira = deepcopy(relatorio["empresas"][0]["rodadas"][0])
    assert primeira["modo"] == "LEGADO"
    assert primeira["dfc"] is None and primeira["balanco"] is None
    assert primeira["indicadores"]["endividamento"] is None
    assert primeira["indicadores"]["roe"] is None
    assert primeira["indicadores"]["satisfacao"] is None
    assert primeira["participacao"]["proporcao_confirmada"] == 1.0
    assert primeira["participacao"]["assinaturas"] == []
    # O estado atual pode ser diferente: ele não preenche lacunas do passado.
    with SessionLocal() as db:
        empresa = db.get(Empresa, empresa_id)
        empresa.caixa = 987654.0
        if hasattr(Empresa, "estado_simulacao"):
            empresa.estado_simulacao = {"satisfacao": 99, "capital_aportado": 1000000}
        db.commit()
    _fechar_individual(cliente, turma, professor)
    novo = cliente.get(_url(turma["id"]), headers=professor).json()
    assert novo["empresas"][0]["rodadas"][0] == primeira
    assert novo["empresas"][0]["rodadas"][1]["participacao"]["proporcao_confirmada"] == 0.0
    assert novo["empresas"][0]["resumo"]["participacao"] == 0.5
    assert novo["empresas"][0]["resumo"]["lucro_acumulado"] == pytest.approx(sum(r["dre"]["lucro_liquido"] for r in novo["empresas"][0]["rodadas"]))


def test_relatorio_preserva_assinaturas_de_versoes_anteriores_sem_contar_como_atuais(cliente, professor):
    equipe = _criar_equipe(cliente, professor)
    _configurar(cliente, equipe)
    anterior = _salvar(cliente, equipe)
    _aprovar(cliente, equipe, equipe["alunos"][0], anterior["versao"])
    atual = _salvar(cliente, equipe, marketing=100)
    for aluno in equipe["alunos"]:
        _aprovar(cliente, equipe, aluno, atual["versao"])
    assert _fechar(cliente, equipe, professor).status_code == 200
    relatorio = cliente.get(_url(equipe["turma"]["id"]), headers=professor).json()
    rodada = relatorio["empresas"][0]["rodadas"][0]
    participacao = rodada["participacao"]
    assert participacao["proporcao_confirmada"] == 1.0
    assert len(participacao["assinaturas"]) == 4
    assert {a["versao"] for a in participacao["assinaturas"]} == {anterior["versao"], atual["versao"]}
    assert all(m["confirmou_versao"] for m in participacao["membros"])
    assert {m["aluno_id"] for m in participacao["membros"]} == {a["id"] for a in equipe["alunos"]}
    assert sum(a["acao"] == "APROVAR_DECISAO" for a in participacao["acoes"]) == 4
    assert all("senha" not in json.dumps(a) for a in participacao["acoes"])
    csv_resposta = cliente.get(_url(equipe["turma"]["id"], True), headers=professor)
    linhas = list(csv.DictReader(io.StringIO(csv_resposta.text.lstrip("\ufeff")), delimiter=";"))
    assert len(linhas) == 1
    assert len(json.loads(linhas[0]["Assinaturas"])) == 4
    assert json.loads(linhas[0]["Participação individual"])["proporcao_confirmada"] == 1.0
    assert "attachment" in csv_resposta.headers["Content-Disposition"]


def test_indicadores_zero_e_negativos_sao_nulos():
    resultado = SimpleNamespace(receita=0.0, lucro_liquido=-10.0)
    detalhes = {
        "estado_inicial": {"patrimonio": -100.0}, "estado_final": {"satisfacao": 45.0},
        "balanco": {"caixa": 0, "receber": 0, "estoques": 0, "imobilizado": 0, "pagar": 0, "divida": 0, "capital_giro": -50},
        "operacao": {"cac": None, "ltv": None, "churn": None, "runway": None},
    }
    indicadores = indicadores_rodada(resultado, detalhes)
    assert indicadores["margem_liquida"] is None
    assert indicadores["endividamento"] is None
    assert indicadores["roe"] is None
    assert indicadores["capital_giro"] == -50
    assert indicadores["satisfacao"] == 45
    assert all(indicadores[k] is None for k in ("cac", "ltv", "churn", "runway"))


def test_indicadores_usam_patrimonio_de_abertura_e_cheque_especial_como_passivo():
    resultado = SimpleNamespace(receita=1000.0, lucro_liquido=200.0)
    detalhes = {
        "estado_inicial": {"capital_aportado": 0},
        "estado_final": {"capital_aportado": 1000, "satisfacao": 90},
        "balanco": {"caixa": -100, "receber": 200, "estoques": 1000, "imobilizado": 500, "pagar": 100, "divida": 100, "patrimonio": 1400, "capital_giro": 1000},
        "operacao": {"cac": 10, "ltv": 200, "churn": 0.05, "runway": 3},
    }
    indicadores = indicadores_rodada(resultado, detalhes)
    assert indicadores["margem_liquida"] == 0.2
    assert indicadores["endividamento"] == pytest.approx(300 / 1700)
    assert indicadores["roe"] == 1.0  # abertura 1400 - 200 lucro - 1000 aporte
    assert indicadores["cac"] == 10
    detalhes["balanco_inicial"] = {"patrimonio": 1000}
    assert indicadores_rodada(resultado, detalhes)["roe"] == 0.2


def test_pontuacao_nao_recompensa_aporte_e_respeita_pesos_do_professor(cliente, professor):
    turma_dados = _criar_turma(cliente, professor)
    aluno1 = cadastrar(cliente, "Ana", "relatorio-aporte-ana@aluno.iffar.edu.br")
    aluno2 = cadastrar(cliente, "Bia", "relatorio-aporte-bia@aluno.iffar.edu.br")
    e1 = _entrar(cliente, aluno1, turma_dados["codigo"], "Sem aporte")
    e2 = _entrar(cliente, aluno2, turma_dados["codigo"], "Com aporte")
    _fechar_individual(cliente, turma_dados, professor)
    with SessionLocal() as db:
        turma = db.get(Turma, turma_dados["id"])
        # Objetos não persistidos nessas atribuições permitem testar a regra
        # antes e depois da migração aditiva, sem depender de dados de mercado.
        turma.configuracao_simulacao = {"peso_lucro": 0, "peso_patrimonio": 1, "peso_satisfacao": 0, "peso_participacao": 0}
        for empresa in turma.empresas:
            resultado = empresa.resultados[0]
            aporte = 100000 if empresa.id == e2 else 0
            resultado.detalhes_simulacao = {
                "modo": "STARTUP", "estado_inicial": {"capital_aportado": 0},
                "estado_final": {"capital_aportado": aporte, "satisfacao": 80},
                "balanco": {"patrimonio": 5000 + aporte},
            }
        relatorio = gerar_relatorio(turma)
        assert relatorio["rubrica"]["pesos"]["patrimonio"] == 1
        assert {r["patrimonio_sem_aportes"] for r in relatorio["ranking"]} == {5000.0}
        assert {r["pontuacao_didatica"] for r in relatorio["ranking"]} == {50.0}
        assert {r["empresa_id"] for r in relatorio["ranking"]} == {e1, e2}
        # Uma leitura do relatório não modifica o JSON usado como evidência.
        assert next(e for e in turma.empresas if e.id == e2).resultados[0].detalhes_simulacao["balanco"]["patrimonio"] == 105000


def test_csv_preserva_numeros_ausentes_e_protege_nome_com_formula():
    relatorio = {
        "rubrica": {"tipo": "PONTUACAO_DIDATICA"},
        "ranking": [{"empresa_id": 1, "pontuacao_didatica": None}],
        "empresas": [{"id": 1, "nome": "=SOMA(A1:A5)", "rodadas": [{
            "rodada": 1, "modo": "LEGADO", "dre": {"receita": 0, "lucro_liquido": -100},
            "indicadores": {k: None for k in ("margem_liquida", "endividamento", "roe", "capital_giro", "satisfacao", "cac", "ltv", "churn", "runway")},
            "dfc": None, "balanco": None, "operacao": None, "decisao": None,
            "participacao": {"assinaturas": []}, "alertas": [],
        }]}],
    }
    linhas = list(csv.DictReader(io.StringIO(relatorio_csv(relatorio).lstrip("\ufeff")), delimiter=";"))
    assert linhas[0]["Empresa"] == "'=SOMA(A1:A5)"
    assert linhas[0]["Lucro líquido"] == "-100"
    assert linhas[0]["ROE"] == ""
    assert linhas[0]["DFC"] == ""
