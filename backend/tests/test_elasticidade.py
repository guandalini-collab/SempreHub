"""Elasticidade-preço da escolha entre lojas (Bijmolt, van Heerde e Pieters, 2005)."""
import pytest

from app.motor.portfolio import atrativos
from app.motor.simulacao import ELASTICIDADE_PRECO_ESCOLHA


def _item(preco):
    return {"produto_id": "pet-brinquedo", "peso": 1, "preco": preco, "custo_unitario": 35.8,
            "preco_mercado": 59.0, "canais": ["DIRETO"], "posicionamento": "PRECO",
            "midias": [], "custos_campanha": {"versao": 2, "investimento_efetivo": 0}}


def test_elasticidade_aprovada_e_referencia_do_catalogo():
    assert ELASTICIDADE_PRECO_ESCOLHA == 2.62
    no_mercado, metade = atrativos([_item(59.0), _item(29.5)], 100, 30)
    # Preço pela metade do preço de mercado do item: atratividade × 2^2,62.
    assert metade / no_mercado == pytest.approx(2 ** 2.62)
