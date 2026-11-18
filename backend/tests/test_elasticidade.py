"""Elasticidade-preço da escolha entre lojas (Bijmolt, van Heerde e Pieters, 2005)."""
import pytest

from app.motor.portfolio import atrativos
from app.motor.simulacao import ELASTICIDADE_PRECO_ESCOLHA


def _item(preco):
    return {"produto_id": "pet-brinquedo", "peso": 1, "preco": preco, "custo_unitario": 35.8,
            "preco_mercado": 59.0, "canais": ["DIRETO"], "posicionamento": "PRECO",
            "midias": [{"id": "email", "quantidade": 100}], "custos_campanha": {"versao": 2, "investimento_efetivo": 0}}


def test_elasticidade_aprovada_e_referencia_do_catalogo():
    assert ELASTICIDADE_PRECO_ESCOLHA == 2.62
    no_mercado, metade = atrativos([_item(59.0), _item(29.5)], 100, 30)
    # Preço pela metade do preço de mercado do item: atratividade × 2^2,62.
    assert metade / no_mercado == pytest.approx(2 ** 2.62)


def test_propaganda_exponencial_com_persistencia():
    """Itens A e C: forma MNL (Cooper e Nakanishi, p. 35-36), λ mensal 0,44 (Clarke)."""
    import math
    from app.motor.portfolio import (ELASTICIDADE_PROPAGANDA, estoques_propaganda, beta_propaganda,
                                     contexto_propaganda, fator_propaganda, veiculacao_por_produto)
    assert ELASTICIDADE_PROPAGANDA == 0.12
    plano = {"produtos": [_item(59.0)]}
    veic = veiculacao_por_produto(plano)["pet-brinquedo"]
    assert veic > 0
    # Estoque: mês atual + 0,44 × mês anterior; meses sem plano contam zero.
    est = estoques_propaganda([plano, plano, None, plano], 0.44)["pet-brinquedo"]
    assert est == pytest.approx(veic * (1 + 0.44 + 0.44 ** 3))
    # β: elasticidade de curto prazo 0,12 na empresa média com 5 lojas.
    beta = beta_propaganda(5, 0.44)
    assert beta == pytest.approx(0.12 * (1 + .44 + .44 ** 2 + .44 ** 3) / 0.8)
    ctx = contexto_propaganda({1: {"pet-brinquedo": 100.0}, 2: {"pet-brinquedo": 0.0}}, 5, 0.44)
    assert ctx["media"] == 50.0
    propaganda = {"media": ctx["media"], "beta": ctx["beta"]}
    # Sem propaganda o fator é exp(0) = 1: a loja continua vendendo.
    assert fator_propaganda(0.0, propaganda) == 1.0
    assert fator_propaganda(100.0, propaganda) == pytest.approx(math.exp(2 * beta))
    # Ninguém anunciou: fator 1 para todos.
    assert fator_propaganda(0.0, {"media": 0.0, "beta": beta}) == 1.0
    # Elasticidade pontual MNL β(1 − s)X/média no ponto médio, mês corrente:
    soma = 1 + .44 + .44 ** 2 + .44 ** 3
    assert beta * (1 - 1 / 5) / soma == pytest.approx(0.12)


def test_atrativos_usam_estoque_de_propaganda():
    import math
    sem = _item(59.0) | {"midias": []}
    com = _item(59.0)
    propaganda = {"estoques": {"pet-brinquedo": 50.0}, "media": 50.0, "beta": 0.3}
    a_com, = atrativos([com], 100, 30, propaganda=propaganda)
    a_sem, = atrativos([sem], 100, 30, propaganda={**propaganda, "estoques": {}})
    assert a_sem > 0
    assert a_com / a_sem == pytest.approx(math.exp(0.3))


def test_concorrente_simulado_com_catalogo_usa_a_mesma_forma():
    """Item 2b: preço relativo ^ −2,62 × propaganda na média × força."""
    import math
    from app.motor.portfolio import atratividade_concorrente_catalogo
    ctx = {"media": 50.0, "beta": 0.26}
    assert atratividade_concorrente_catalogo(1.0, 1.0, ctx) == pytest.approx(math.exp(0.26))
    assert atratividade_concorrente_catalogo(0.9, 1.3, ctx) == pytest.approx((1 / .9) ** 2.62 * math.exp(.26) * 1.3)
    # Sem propaganda no mercado, o fator é 1.
    assert atratividade_concorrente_catalogo(1.0, 1.0, {"media": 0.0, "beta": .26}) == 1.0
