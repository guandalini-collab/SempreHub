"""Tamanho do mercado pela PAC 2024 e atualização pela PMC (receita nominal)."""
import io
import json
from types import SimpleNamespace

import pytest

from app.mercado_pac import (BASE, RAZAO_LOJA_PEQUENA, atualizar, demanda_por_loja, fator_atualizacao,
                             receita_mensal_loja)


def test_receita_da_loja_pequena_atualizada_pela_pmc():
    fator, periodo = fator_atualizacao(BASE["series"]["31555"])
    assert periodo == "202510 a 202609"
    r = receita_mensal_loja("moveis")
    assert r["receita"] == pytest.approx(95_000 * RAZAO_LOJA_PEQUENA * fator, abs=.01)
    assert "Estimativa" in r["aviso"]


def test_mercado_em_reais_com_lojas_na_disputa(cliente):
    turma = SimpleNamespace(modo_jogo="TRADICIONAL", configuracao_simulacao={"setor_mercado": "Pet Shop"})
    d = demanda_por_loja(turma)
    assert d["receita"] == receita_mensal_loja("pet")["receita"]
    assert demanda_por_loja(SimpleNamespace(modo_jogo="STARTUP", configuracao_simulacao={"setor_mercado": "Pet Shop"})) is None
    from app.motor.avancado import _mercado
    turma = SimpleNamespace(modo_jogo="TRADICIONAL", configuracao_simulacao={"setor_mercado": "Pet Shop", "concorrentes_virtuais": 2},
                            demanda_base_por_empresa=100, crescimento_mercado_mensal=.5, preco_referencia=50, taxa_juros_mensal=.025)
    decisao = SimpleNamespace(preco=50, emprestimo=0, plano_comercial={"produtos": []})
    p = {"atratividade": 1e9, "comercial_ativo": True, "avaliacao_estrategica": {"fator": 1}, "parametros": {}}
    demandas, bots = _mercado([p], [decisao], turma, 3, 1)
    # Mercado = loja pequena × 3 lojas (1 equipe + 2 concorrentes), em reais; sem crescimento sem fonte.
    assert sum(demandas) + sum(b["receita"] for b in bots) == pytest.approx(d["receita"] * 3, rel=1e-6)
    assert p["parametros"]["mercado_em_reais"] is True


def test_fatia_em_reais_vira_unidades_pelo_preco_de_cada_produto():
    from app.motor.portfolio import pesos_em_valor, unidades_da_receita
    itens = [{"preco": 29.0}, {"preco": 187.0}]
    pesos = [1.0, 1.0]  # mesma fatia de receita para cada produto
    assert unidades_da_receita(2_160.0, itens, pesos) == pytest.approx(1_080 / 29 + 1_080 / 187)
    pv = pesos_em_valor(itens, pesos)
    assert pv[0] / sum(pv) * unidades_da_receita(2_160.0, itens, pesos) * 29 == pytest.approx(1_080)


def test_atualizacao_pela_api_recusa_serie_incompleta(cliente):
    from app.database import SessionLocal
    serie = {f"2024{m:02d}": 100.0 for m in range(1, 13)} | {f"2025{m:02d}": 110.0 for m in range(1, 13)}
    resposta = [{"resultados": [{"classificacoes": [{"id": "85", "categoria": {c: "x"}}], "series": [{"serie": serie}]}
                                for c in ("31555", "90673", "103158")]}]
    with SessionLocal() as db:
        assert atualizar(db, lambda url, timeout: io.BytesIO(json.dumps(resposta).encode())) is True
    from app.mercado_pac import series_vigentes
    with SessionLocal() as db:
        assert fator_atualizacao(series_vigentes(db)["series"]["31555"])[0] == pytest.approx(1.1)


def test_custos_da_loja_pela_pac_e_capital_pela_selic(cliente):
    import datetime
    from app.mercado_pac import (atualizar_selic, custos_da_turma, custos_fixos_loja, selic_mensal)
    moveis = custos_fixos_loja("moveis")
    # Aluguel: R$ 2.611.318 mil ÷ 86.846 lojas ÷ 12 meses × 0,4348.
    assert moveis["componentes"]["Aluguel e condomínio"] == pytest.approx(2_611_318_000 / 86_846 / 12 * RAZAO_LOJA_PEQUENA, abs=.01)
    assert moveis["total"] == pytest.approx(sum(moveis["componentes"].values()), abs=.05)
    turma = SimpleNamespace(modo_jogo="LEGADO", configuracao_simulacao={"setor_mercado": "Móveis Residenciais"})
    custos = custos_da_turma(turma)
    assert custos["custos_fixos"]["total"] == moveis["total"] and custos["taxa_capital_estoque"] == pytest.approx(.0107)
    from app.database import SessionLocal
    dados = [{"data": "01/10/2026", "valor": "1.07"}, {"data": "01/11/2026", "valor": "0.51"}]
    with SessionLocal() as db:
        assert atualizar_selic(db, lambda url, timeout: io.BytesIO(json.dumps(dados).encode()), hoje=datetime.date(2026, 11, 17))
        assert selic_mensal(db) == (pytest.approx(.0107), "202610")  # novembro incompleto fica fora
    from app.motor.avancado import parametros
    from app.models import Turma
    with SessionLocal() as db:
        t = Turma(nome="x", modo_jogo="TRADICIONAL", configuracao_simulacao={"setor_mercado": "Pet Shop"})
        p = parametros(t)
    assert p["custos_fixos_mensais"] == custos_fixos_loja("pet")["total"]
    assert p["configuracao_simulacao"]["custo_armazenagem_m3"] == 0.0
    # Item B: sem despesa de armazenagem; o caixa positivo rende a Selic do mês.
    assert p["configuracao_simulacao"]["custo_armazenagem"] == 0.0
    assert p["rendimento_caixa_mensal"] == pytest.approx(.0107)
