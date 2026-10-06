"""Conteúdo educacional neutro, referenciado e seguro para consumo pela UI."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.educacao import (
    listar_analises,
    listar_midias,
    listar_referencias,
    obter_conteudo_educacional,
    obter_midia,
)
from app.routers.educacao import router


def _cliente():
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_catalogo_tem_referencias_e_as_seis_analises_pedidas():
    referencias = listar_referencias()
    analises = listar_analises()
    assert len(referencias) >= 6
    assert {item["slug"] for item in analises} == {"porter", "pestel", "mercado", "swot", "financeira"}
    assert all(item["referencias"] for item in analises)
    assert all(item["localizacao"] for item in referencias)


def test_pestel_tem_seis_fatores_e_segmentacao_tem_quatro_bases():
    pestel = next(item for item in listar_analises() if item["slug"] == "pestel")
    assert {item["chave"] for item in pestel["itens"]} == {
        "politico", "economico", "social", "tecnologico", "ecologico", "legal",
    }
    segmentacoes = obter_conteudo_educacional()["segmentacoes"]
    assert {item["slug"] for item in segmentacoes} == {
        "demografica", "geografica", "psicografica", "comportamental",
    }
    assert all(item["criterios"] and item["exemplo"] for item in segmentacoes)


def test_catalogo_de_midias_cobre_categorias_e_campos_neutros():
    midias = listar_midias()
    assert len(midias) >= 20
    assert {item["categoria"] for item in midias} == {
        "DIGITAL", "TRADICIONAL", "OOH", "AUDIO_ENTRETENIMENTO", "INFLUENCIA_MATERIAIS",
    }
    assert all(item["finalidade"] and item["custo_entrada"] for item in midias)
    assert all("tipo de empresa" not in str(item).lower() for item in midias)
    assert all("adequad" not in str(item).lower() for item in midias)
    assert all(item["pagamento_prazo"] and item["efeito_caixa"] for item in midias)


def test_midias_podem_ser_filtradas_e_sao_copias():
    digital = listar_midias("digital")
    assert digital and all(item["categoria"] == "DIGITAL" for item in digital)
    digital[0]["nome"] = "alterado no teste"
    assert listar_midias("DIGITAL")[0]["nome"] != "alterado no teste"
    assert obter_midia("google-ads")["nome"] == "Google Ads (busca e sites parceiros)"
    assert obter_midia("nao-existe") is None


def test_api_entrega_biblioteca_e_erros_claros():
    cliente = _cliente()
    resposta = cliente.get("/api/educacao")
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["versao"] == 1
    assert corpo["ressalvas"]["neutralidade"]
    assert cliente.get("/api/educacao/analises/porter").status_code == 200
    assert cliente.get("/api/educacao/midias?categoria=OOH").status_code == 200
    assert len(cliente.get("/api/educacao/midias?categoria=OOH").json()["midias"]) >= 5
    assert cliente.get("/api/educacao/analises/desconhecida").status_code == 404
    assert cliente.get("/api/educacao/midias?categoria=desconhecida").status_code == 404


def test_ressalvas_separam_preco_didatico_de_regra_fiscal():
    corpo = _cliente().get("/api/educacao/ressalvas").json()["ressalvas"]
    assert "não são cotação" in corpo["precos"].lower()
    assert "hipótese configurável" in corpo["iof"]
    assert "não substitui" in corpo["retencoes"]
    assert "DFC" in corpo["caixa"]
