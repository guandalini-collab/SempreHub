"""Invariantes do motor Startup, sem banco ou efeitos colaterais."""

from copy import deepcopy

import pytest

from app.motor import startup


def _entrada(estado=None, simulacao=None):
    empresa = {
        "caixa": 10_000.0, "divida": 0.0, "funcionarios": 0,
        "marca": 0.0, "qualidade": 0.0, "classe_dornelas": "SERIAL",
        "estado_simulacao": deepcopy(estado),
    }
    decisao = {
        "preco": 100.0, "marketing": 1_000.0, "pd": 0.0, "networking": 0.0,
        "contratar": 0, "demitir": 0, "emprestimo": 0.0, "amortizacao": 0.0,
        "simulacao": {"capacidade_nuvem": 300, **(simulacao or {})},
    }
    parametros = {
        "preco_referencia": 100.0, "salario_base": 2_000.0,
        "custos_fixos_mensais": 500.0, "taxa_juros_mensal": .025,
        "taxa_cheque_especial": .08, "limite_credito": 50_000.0,
        "configuracao_simulacao": {},
    }
    return empresa, decisao, parametros


def test_aporte_nao_e_receita_e_dilui_fundadores():
    empresa, decisao, parametros = _entrada(simulacao={"aporte": 10_000, "valuation": 100_000})
    original = deepcopy(empresa)
    preparo = startup.preparar(empresa, decisao, parametros, 1)
    resultado = startup.apurar(preparo, 100, lambda receita, cmv: (0.0, 0.0))

    assert empresa == original
    assert resultado["dre"]["receita"] == 10_000
    assert resultado["dre"]["lucro_liquido"] < resultado["dre"]["receita"]
    assert resultado["detalhes"]["operacao"]["aporte"] == 10_000
    assert resultado["detalhes"]["operacao"]["participacao_fundadores"] == pytest.approx(10 / 11)


def test_churn_afeta_base_inicial_mas_nuvem_nao_apaga_clientes():
    estado = {"clientes": 100, "satisfacao": 20, "rh": {"moral": 80, "qualificacao": 0}}
    empresa, decisao, parametros = _entrada(estado, {"capacidade_nuvem": 20})
    preparo = startup.preparar(empresa, decisao, parametros, 1)
    resultado = startup.apurar(preparo, 500, lambda receita, cmv: (0.0, 0.0))
    operacao = resultado["detalhes"]["operacao"]

    assert operacao["clientes_iniciais"] == 100
    assert operacao["clientes_perdidos"] > 0
    assert operacao["clientes_finais"] > operacao["clientes_atendidos"]
    assert resultado["estado"]["clientes"] == operacao["clientes_finais"]
    assert operacao["clientes_nao_atendidos"] > 0


def test_credito_tem_receita_na_dre_e_caixa_no_vencimento():
    empresa, decisao, parametros = _entrada(simulacao={"vendas_prazo": 1, "prazo_recebimento": 2})
    p1 = startup.preparar(empresa, decisao, parametros, 1)
    r1 = startup.apurar(p1, 20, lambda receita, cmv: (0.0, 0.0))
    assert r1["dre"]["receita"] == 2_000
    assert r1["detalhes"]["dfc"]["recebimentos"] == 0
    assert r1["estado"]["receber"]

    empresa2 = {**empresa, "caixa": r1["caixa"], "estado_simulacao": r1["estado"]}
    p2 = startup.preparar(empresa2, {**decisao, "simulacao": {"capacidade_nuvem": 300}}, parametros, 2)
    r2 = startup.apurar(p2, 0, lambda receita, cmv: (0.0, 0.0))
    assert r2["detalhes"]["dfc"]["recebimentos"] == 2_000


def test_denominadores_zero_sao_nulos():
    empresa, decisao, parametros = _entrada(simulacao={"capacidade_nuvem": 0})
    resultado = startup.apurar(startup.preparar(empresa, decisao, parametros, 1), 100, lambda r, c: (0, 0))
    operacao = resultado["detalhes"]["operacao"]
    assert operacao["cac"] is None
    assert operacao["ltv"] is None
    assert operacao["runway"] is not None
