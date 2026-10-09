from .decisoes import completar_decisao
import pytest

from app.database import SessionLocal
from app.models import Decisao, Empresa, EventoRodada, Resultado

from .conftest import cadastrar
from .test_fluxo import _criar_turma, _entrar


def _alterar_empresa(empresa_id, **campos):
    with SessionLocal() as db:
        empresa = db.get(Empresa, empresa_id)
        for nome, valor in campos.items():
            setattr(empresa, nome, valor)
        db.commit()


def _prever(cliente, aluno, empresa_id, decisao):
    resposta = cliente.post(
        f"/api/aluno/empresas/{empresa_id}/previsao", headers=aluno, json=decisao
    )
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


@pytest.mark.parametrize(
    "caixa,divida,emprestimo,amortizacao,aprovado,aplicada,juros",
    [
        (20000, 49000, 80000, 2000, 1000, 2000, 1200),
        (-1000, 10000, 5000, 3000, 0, 0, 330),
        (500, 10000, 0, 2000, 0, 500, 237.5),
        # O fechamento amortiza apenas dívida já existente, antes do novo crédito.
        (20000, 0, 5000, 3000, 5000, 0, 125),
    ],
)
def test_previa_financiamento_corresponde_ao_fechamento(
    cliente, professor, caixa, divida, emprestimo, amortizacao, aprovado, aplicada, juros
):
    turma = _criar_turma(cliente, professor)
    aluno = cadastrar(cliente, "Ana", "ana@aluno.iffar.edu.br")
    empresa_id = _entrar(cliente, aluno, turma["codigo"], "Ana", regime="SIMPLES_NACIONAL")
    _alterar_empresa(empresa_id, caixa=caixa, divida=divida)
    decisao = {"preco": 100, "emprestimo": emprestimo, "amortizacao": amortizacao}
    antes = cliente.get(f"/api/aluno/empresas/{empresa_id}", headers=aluno).json()
    for _ in range(2):
        previa = _prever(cliente, aluno, empresa_id, decisao)
        assert previa["emprestimo_aprovado"] == aprovado
        assert previa["amortizacao_aplicada"] == aplicada
        assert previa["caixa_disponivel"] == caixa + aprovado - aplicada
        assert previa["juros"] == pytest.approx(juros)
    assert cliente.get(f"/api/aluno/empresas/{empresa_id}", headers=aluno).json() == antes
    with SessionLocal() as db:
        assert db.query(Decisao).count() == 0
        assert db.query(Resultado).count() == 0
        assert db.query(EventoRodada).count() == 0

    assert cliente.put(f"/api/aluno/empresas/{empresa_id}/decisao", headers=aluno, json=completar_decisao(decisao)).status_code == 200
    assert cliente.post(f"/api/professor/turmas/{turma['id']}/fechar-rodada", headers=professor, json={"evento": "NENHUM"}).status_code == 200
    resultado = cliente.get(f"/api/aluno/empresas/{empresa_id}", headers=aluno).json()["resultados"][0]
    assert resultado["divida_final"] == previa["divida_prevista"]
    assert resultado["dre"]["juros"] == pytest.approx(previa["juros"])
    assert resultado["caixa_final"] == pytest.approx(previa["caixa_disponivel"] + resultado["dre"]["lucro_liquido"])


def test_previa_regime_e_capacidade_correspondem_ao_fechamento(cliente, professor):
    turma = _criar_turma(cliente, professor)
    aluno = cadastrar(cliente, "Ana", "ana@aluno.iffar.edu.br")
    empresa_id = _entrar(cliente, aluno, turma["codigo"], "Ana")
    _alterar_empresa(empresa_id, autoeficacia=20)
    decisao = {"preco": 100, "contratar": 2}
    previa = _prever(cliente, aluno, empresa_id, decisao)
    assert previa["regime"] == "SIMPLES_NACIONAL"
    assert previa["funcionarios"] == 2
    assert previa["folha"] == pytest.approx(5800)
    assert previa["capacidade"] == pytest.approx(324)
    assert len(previa["alertas"]) == 2
    cliente.put(f"/api/aluno/empresas/{empresa_id}/decisao", headers=aluno, json=completar_decisao(decisao))
    cliente.post(f"/api/professor/turmas/{turma['id']}/fechar-rodada", headers=professor, json={"evento": "NENHUM"})
    resultado = cliente.get(f"/api/aluno/empresas/{empresa_id}", headers=aluno).json()["resultados"][0]
    assert resultado["regime"] == previa["regime"]
    assert resultado["capacidade"] == previa["capacidade"]
    assert resultado["dre"]["folha"] == previa["folha"]


def test_previa_segunda_rodada_preserva_estado_e_historico(cliente, professor):
    turma = _criar_turma(cliente, professor, total_rodadas=2, caixa_inicial=50000)
    aluno = cadastrar(cliente, "Ana", "ana@aluno.iffar.edu.br")
    empresa_id = _entrar(cliente, aluno, turma["codigo"], "Franquia", regime="SIMPLES_NACIONAL", classe="FRANQUIA")
    decisao = {"preco": 100, "emprestimo": 5000, "contratar": 1, "marketing": 1000, "pd": 500}
    cliente.put(f"/api/aluno/empresas/{empresa_id}/decisao", headers=aluno, json=completar_decisao(decisao))
    cliente.post(f"/api/professor/turmas/{turma['id']}/fechar-rodada", headers=professor, json={"evento": "GREVE_LOGISTICA"})
    antes = cliente.get(f"/api/aluno/empresas/{empresa_id}", headers=aluno).json()
    assert antes["turma"]["rodada_atual"] == 2
    primeira = antes["resultados"][0]
    assert antes["empresa"]["caixa"] == primeira["caixa_final"]
    assert antes["empresa"]["divida"] == primeira["divida_final"]
    decisao2 = {"preco": 100, "amortizacao": 1000, "marketing": 700, "pd": 300}
    previa = _prever(cliente, aluno, empresa_id, decisao2)
    assert previa["rodada"] == 2
    assert previa["funcionarios"] == 1
    assert previa["divida_prevista"] == 4000
    assert previa["caixa_disponivel"] == pytest.approx(primeira["caixa_final"] - 1000)
    # Greve persiste por dois meses e a franquia paga 5% de royalties.
    assert previa["margem_unitaria"] == pytest.approx(100 * 0.95 - 40 * 1.4)
    assert cliente.get(f"/api/aluno/empresas/{empresa_id}", headers=aluno).json() == antes
    cliente.put(f"/api/aluno/empresas/{empresa_id}/decisao", headers=aluno, json=completar_decisao(decisao2))
    cliente.post(f"/api/professor/turmas/{turma['id']}/fechar-rodada", headers=professor, json={"evento": "NENHUM"})
    final = cliente.get(f"/api/aluno/empresas/{empresa_id}", headers=aluno).json()
    assert final["turma"]["status"] == "ENCERRADA"
    assert final["resultados"][0] == primeira
    assert final["eventos"][0] == antes["eventos"][0]
    assert [r["rodada"] for r in final["resultados"]] == [1, 2]
    segunda = final["resultados"][1]
    assert segunda["capacidade"] == previa["capacidade"]
    assert segunda["divida_final"] == previa["divida_prevista"]
    assert segunda["caixa_final"] == pytest.approx(previa["caixa_disponivel"] + segunda["dre"]["lucro_liquido"])
    despesas = sum(segunda["dre"][campo] for campo in ("folha", "custos_fixos", "marketing", "pd", "networking", "rescisoes", "juros"))
    assert despesas == pytest.approx(previa["gastos_previstos"])
    detalhe = cliente.get(f"/api/professor/turmas/{turma['id']}/empresas/{empresa_id}", headers=professor).json()
    assert detalhe["resultados"] == final["resultados"]
    assert [d["rodada"] for d in detalhe["decisoes"]] == [1, 2]
    assert detalhe["decisoes"][0]["emprestimo"] == 5000
    assert detalhe["decisoes"][1]["amortizacao"] == 1000
    assert cliente.post(f"/api/aluno/empresas/{empresa_id}/previsao", headers=aluno, json=decisao2).status_code == 422


def test_previa_validacao_e_acesso(cliente, professor):
    turma = _criar_turma(cliente, professor)
    aluno = cadastrar(cliente, "Ana", "ana@aluno.iffar.edu.br")
    outro = cadastrar(cliente, "Bia", "bia@aluno.iffar.edu.br")
    empresa_id = _entrar(cliente, aluno, turma["codigo"], "Ana")
    url = f"/api/aluno/empresas/{empresa_id}/previsao"
    assert cliente.post(url, json={"preco": 100}).status_code == 401
    assert cliente.post(url, headers=professor, json={"preco": 100}).status_code == 403
    assert cliente.post(url, headers=outro, json={"preco": 100}).status_code == 404
    for dados in ({"preco": 0}, {"preco": 100, "demitir": 1}, {"preco": 100, "amortizacao": 100}):
        assert cliente.post(url, headers=aluno, json=dados).status_code == 422
    sem_margem = _prever(cliente, aluno, empresa_id, {"preco": 30})
    assert sem_margem["ponto_equilibrio"] is None
