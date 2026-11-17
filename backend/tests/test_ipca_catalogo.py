"""Correção dos preços do catálogo pelo IPCA por subitem (tabela 7060)."""
import io
import json

from app.catalogo_fixo import ITENS, item
from app.ipca_catalogo import atualizar, fator, indice_do_produto, preco_corrigido, series_vigentes


def test_associacao_aprovada_subitem_item_ou_geral():
    assert indice_do_produto("colchoes", "Colchão de espuma D28 casal")[1] == "3101017.Colchão"
    assert indice_do_produto("moveis", "Mesa em L")[2] == "item"
    assert indice_do_produto("pet", "Ração seca premium (pacote de 10 kg ou mais)")[0] == 107666
    assert indice_do_produto("mochilas", "Mala de bordo rígida")[2] == "geral"
    assert indice_do_produto("mochilas", "Clutch")[1] == "4201015.Bolsa"
    assert all(indice_do_produto(i["setor"], i["nome"]) for i in ITENS)


def test_fator_acumula_so_meses_depois_da_coleta():
    variacoes = {"202610": 9.0, "202611": 9.0, "202612": 1.0, "202701": -0.5}
    valor, de, ate = fator(variacoes, "2026-11-16")
    assert (de, ate) == ("202612", "202701") and round(valor, 6) == round(1.01 * 0.995, 6)
    assert fator({}, "2026-11-16") == (1.0, None, None)


def test_preco_corrigido_e_atualizacao_pela_api(cliente):
    from app.database import SessionLocal
    resposta = [{"resultados": [
        {"classificacoes": [{"categoria": {"7493": "3101017.Colchão"}}], "series": [{"serie": {"202612": "2.00"}}]},
        {"classificacoes": [{"categoria": {"7169": "Índice geral"}}], "series": [{"serie": {"202612": "...", "202701": "0.30"}}]},
    ]}]
    abrir = lambda url, timeout: io.BytesIO(json.dumps(resposta).encode())
    with SessionLocal() as db:
        assert atualizar(db, abrir) is True
        assert atualizar(db, abrir) is False  # uma consulta por dia
        series = series_vigentes(db)["series"]
    d28 = item("colchoes-colchao-de-espuma-d28-casal")
    corrigido = preco_corrigido(d28, series=series)
    assert corrigido["preco"] == round(679 * 1.02, 2) and corrigido["periodo"] == "202612 a 202612"
    mala = item("mochilas-mala-de-bordo-rigida")
    assert preco_corrigido(mala, series=series)["fator"] == 1.003
