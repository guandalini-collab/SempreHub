from .decisoes import completar_decisao
from copy import deepcopy
import pytest
from pydantic import ValidationError
from app.motor.tradicional import preparar, apurar
from app.schemas import DecisaoSimulacao
from .test_tradicional import base, sem_tributos
from .test_fluxo import _criar_turma, _entrar
from .conftest import cadastrar


def test_horas_extras_aumentam_capacidade_e_reconciliam_dre_caixa():
    empresa, decisao, parametros = base()
    empresa["funcionarios"] = 1
    empresa["estado_simulacao"]["maquinas"][0]["capacidade"] = 1000
    parametros["salario_base"] = 2200
    decisao["simulacao"].update(producao=330, comprar_mp=330)
    normal = preparar(empresa, decisao, parametros, 1)
    extra = deepcopy(decisao)
    extra["simulacao"]["horas_extras"] = 40
    preparo = preparar(empresa, extra, parametros, 1)
    assert preparo["capacidade_produtiva"] > normal["capacidade_produtiva"]
    assert preparo["producao_real"] > normal["producao_real"]
    assert preparo["custo_horas_extras"] == 870
    resultado = apurar(preparo, 280, sem_tributos)
    dre, dfc = resultado["dre"], resultado["detalhes"]["dfc"]
    assert dre["horas_extras"] == 870
    assert dre["lucro_liquido"] == pytest.approx(dre["receita"] - sum(v for k,v in dre.items() if k not in ("receita", "lucro_liquido")))
    assert dfc["caixa_final"] == pytest.approx(dfc["caixa_inicial"] + dfc["operacional"] + dfc["investimento"] + dfc["financiamento"])
    assert empresa["estado_simulacao"]["maquinas"][0]["capacidade"] == 1000


def test_horas_extras_validacao():
    for valor in (-1, 41, float("nan"), float("inf")):
        with pytest.raises(ValidationError):
            DecisaoSimulacao(horas_extras=valor)


def test_nota_semestre_e_csv_no_professor(cliente, professor):
    turma = _criar_turma(cliente, professor, total_rodadas=1)
    aluno = cadastrar(cliente, "Ana", "nota-nova@aluno.iffar.edu.br")
    empresa = _entrar(cliente, aluno, turma["codigo"], "Empresa")
    url = f"/api/professor/turmas/{turma['id']}/relatorio"
    assert cliente.get(url, headers=professor).json()["ranking"][0]["nota_semestre"] is None
    cliente.put(f"/api/aluno/empresas/{empresa}/decisao", headers=aluno, json=completar_decisao({"preco":100}))
    resposta = cliente.post(f"/api/professor/turmas/{turma['id']}/fechar-rodada", headers=professor, json={"rodada":1,"evento":"NENHUM"})
    assert resposta.status_code == 200, resposta.text
    dados = cliente.get(url, headers=professor).json()
    linha = dados["ranking"][0]
    assert 0 <= linha["nota_semestre"] <= 10
    assert linha["nota_semestre"] == pytest.approx(round(linha["pontuacao_didatica"] / 10, 2), abs=.01)
    assert linha["nota_provisoria"] is False
    assert dados["rubrica"]["escala_nota"] == [0,10]
    assert cliente.get(url, headers=aluno).status_code == 403
    assert "Nota automática / 10" in cliente.get(url+".csv", headers=professor).text


def test_horas_extras_exigem_funcionario_e_nao_repetem(cliente, professor):
    turma = _criar_turma(cliente, professor, modo_jogo="TRADICIONAL", total_rodadas=2)
    aluno = cadastrar(cliente, "Ana", "extra-nova@aluno.iffar.edu.br")
    empresa = _entrar(cliente, aluno, turma["codigo"], "Fábrica", regime="SIMPLES_NACIONAL")
    url = f"/api/aluno/empresas/{empresa}/decisao"
    decisao = {"rodada":1,"preco":100,"simulacao":{"horas_extras":20,"comprar_mp":100,"producao":100}}
    assert cliente.put(url, headers=aluno, json=completar_decisao(decisao)).status_code == 422
    resposta = cliente.put(url, headers=aluno, json=completar_decisao({**decisao,"contratar":1}))
    assert resposta.status_code == 200, resposta.text
    for rodada in (1,2):
        r = cliente.post(f"/api/professor/turmas/{turma['id']}/fechar-rodada", headers=professor,json={"rodada":rodada,"evento":"NENHUM"})
        assert r.status_code == 200, r.text
    historico = cliente.get(f"/api/aluno/empresas/{empresa}",headers=aluno).json()["resultados"]
    assert historico[0]["detalhes_simulacao"]["dre"]["horas_extras"] > 0
    assert historico[1]["detalhes_simulacao"]["dre"]["horas_extras"] == 0
