"""Tamanho do mercado pela PAC 2024 e atualização pela PMC (receita nominal)."""
import io
import json
from types import SimpleNamespace

import pytest

from app.mercado_pac import (BASE, RAZAO_LOJA_PEQUENA, atualizar, demanda_por_loja, fator_atualizacao,
                             preco_medio_mercado, receita_mensal_loja)


def test_receita_da_loja_pequena_atualizada_pela_pmc():
    fator, periodo = fator_atualizacao(BASE["series"]["31555"])
    assert periodo == "202510 a 202609"
    r = receita_mensal_loja("moveis")
    assert r["receita"] == pytest.approx(95_000 * RAZAO_LOJA_PEQUENA * fator, abs=.01)
    assert "Estimativa" in r["aviso"]


def test_demanda_em_unidades_pelo_preco_de_mercado_e_lojas_na_disputa(cliente):
    turma = SimpleNamespace(modo_jogo="TRADICIONAL", configuracao_simulacao={"setor_mercado": "Pet Shop"})
    planos = [{"produtos": [{"preco_mercado": 59.0, "peso": 1}, {"preco_mercado": 43.0, "peso": 1}]}]
    assert preco_medio_mercado(planos) == 51.0
    d = demanda_por_loja(turma, planos)
    assert d["unidades"] == pytest.approx(receita_mensal_loja("pet")["receita"] / 51.0)
    assert demanda_por_loja(SimpleNamespace(modo_jogo="STARTUP", configuracao_simulacao={"setor_mercado": "Pet Shop"}), planos) is None
    from app.motor.avancado import _mercado
    turma = SimpleNamespace(modo_jogo="TRADICIONAL", configuracao_simulacao={"setor_mercado": "Pet Shop", "concorrentes_virtuais": 2},
                            demanda_base_por_empresa=100, crescimento_mercado_mensal=.5, preco_referencia=50, taxa_juros_mensal=.025)
    decisao = SimpleNamespace(preco=50, emprestimo=0, plano_comercial=planos[0])
    p = {"atratividade": 1e9, "comercial_ativo": True, "avaliacao_estrategica": {"fator": 1}}
    demandas, bots = _mercado([p], [decisao], turma, 3, 1)
    # Mercado = loja pequena × 3 lojas (1 equipe + 2 concorrentes); sem crescimento sem fonte.
    assert sum(demandas) + sum(b["unidades_vendidas"] for b in bots) == pytest.approx(d["unidades"] * 3, rel=1e-6)


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
