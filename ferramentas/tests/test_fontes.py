"""Testes offline: respostas simuladas no formato documentado de cada API."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fontes import bibliografia, indicadores, noticias, paginas, relatorio  # noqa: E402


def test_sgs():
    r = indicadores.sgs(4390, obter=lambda u: [{"data": "01/10/2026", "valor": "1,07"}])
    assert r[0]["valor"] == 1.07 and r[0]["periodo_referencia"] == "10/2026"
    assert "bcdata.sgs.4390" in r[0]["link"] and r[0]["situacao_codigo"] == "conferido"


SIDRA = [{"id": "7169", "variavel": "PMC - Número-índice", "unidade": "Número-índice", "resultados": [
    {"classificacoes": [{"id": "85", "categoria": {"90673": "Tecidos, vestuário e calçados"}}],
     "series": [{"serie": {"202608": "108.3", "202609": "101.8", "202610": "..."}}]}]}]


def test_sidra_e_pmc():
    r = indicadores.pmc("vestuario", obter=lambda u: SIDRA)
    assert len(r) == 4 and r[1]["periodo_referencia"] == "202609" and r[1]["valor"] == 101.8
    assert "85[90673]" in r[0]["link"]


META = {"variaveis": [{"id": 12606, "nome": "Número-índice (2022=100)", "unidade": "Número-índice"},
                      {"id": 2265, "nome": "IPCA - Variação acumulada em 12 meses", "unidade": "%"}],
        "classificacoes": [{"id": 544, "categorias": [
            {"id": 129331, "nome": "3.31 Fabricação de móveis"},
            {"id": 129318, "nome": "3.14 Confecção de artigos do vestuário e acessórios"}]}]}


def test_resolver_por_nome():
    achados = indicadores.sidra_resolver(8888, ["fabricacao de moveis"], obter=lambda u: META)
    assert achados == [{"classificacao": 544, "categoria": 129331, "nome": "3.31 Fabricação de móveis"}]


def test_pim_usa_categoria_resolvida():
    chamadas = []

    def obter(u):
        chamadas.append(u)
        return META if u.endswith("/metadados") else SIDRA
    r = indicadores.pim("moveis", obter=obter)
    assert any("544[129331]" in c for c in chamadas) and r[0]["situacao_codigo"] == "resolvido_por_nome"


def test_ipca_mensal_e_12_meses():
    r = indicadores.ipca(obter=lambda u: META if u.endswith("/metadados") else SIDRA)
    assert {x["codigo"] for x in r} == {"7060/63", "7060/2265"}


def test_focus():
    resp = {"value": [{"Indicador": "IPCA", "Data": "2026-11-13", "DataReferencia": "2026", "Mediana": 4.5, "baseCalculo": 0}]}
    r = indicadores.focus("IPCA", 2026, obter=lambda u: resp)
    assert r[0]["valor"] == 4.5 and "ExpectativasMercadoAnuais" in r[0]["link"]


def test_comex_corpo_e_leitura():
    enviados = []

    def enviar(u, corpo):
        enviados.append(corpo)
        return {"data": {"list": [{"year": "2026", "monthNumber": "9", "coNcm": "23091000",
                                   "metricFOB": "1500000", "metricKG": "800000"}]}}
    r = indicadores.comex("pet", de="2026-01", ate="2026-09", enviar=enviar)
    assert enviados[0]["filters"] == [{"filter": "ncm", "values": [23091000]}]
    assert enviados[0]["period"] == {"from": "2026-01", "to": "2026-09"}
    assert r[0]["periodo_referencia"] == "2026-09" and r[0]["valor"] == 1_500_000 and r[0]["kg"] == 800_000


def test_falha_de_uma_fonte_nao_derruba():
    def obter(u):
        raise RuntimeError("fora do ar")
    r = indicadores.macro(obter=obter)
    assert r and all(x["tipo"] == "falha" for x in r)


def test_bibliografia():
    cross = {"message": {"title": ["Measuring and mitigating the costs of stockouts"],
                         "author": [{"family": "Anderson", "given": "Eric T."}],
                         "issued": {"date-parts": [[2006, 11]]}, "container-title": ["Management Science"],
                         "volume": "52", "issue": "11", "page": "1751-1763"}}
    oa = {"doi": "https://doi.org/10.1287/mnsc.1060.0577", "title": "Measuring...", "publication_year": 2006,
          "abstract_inverted_index": {"Stockouts": [0], "are": [1], "costly": [2]},
          "open_access": {"is_oa": True, "oa_url": "https://x/pdf"}, "authorships": []}
    linhas = bibliografia.tabela(["https://doi.org/10.1287/MNSC.1060.0577"],
                                 obter=lambda u: cross if "crossref" in u else oa)
    l = linhas[0]
    assert l["doi"] == "10.1287/mnsc.1060.0577" and l["doi_conferido_crossref"]
    assert l["resumo"] == "Stockouts are costly" and l["pdf_aberto"] == "https://x/pdf" and l["ano"] == 2006
    assert "ANDERSON, Eric T." in bibliografia.abnt(l) and "p. 1751-1763" in bibliografia.abnt(l)
    assert "| 2006 |" in relatorio.markdown_bibliografia(linhas)


def test_gdelt_e_rss():
    g = noticias.gdelt('"mercado pet"', obter=lambda u: {"articles": [
        {"title": "Mercado pet cresce", "url": "https://v/1", "domain": "valor.globo.com", "seendate": "20261110T120000Z"}]})
    assert g[0]["data_publicacao"] == "2026-11-10" and g[0]["tipo"] == "jornalistico"
    xml = ("<rss><channel><item><title>Setor moveleiro em alta</title><link>https://a/1</link>"
           "<pubDate>Tue, 10 Nov 2026 10:00:00 -0300</pubDate><description>texto</description></item>"
           "<item><title>Outro assunto</title><link>https://a/2</link></item></channel></rss>")
    r = noticias.rss({"veiculo": "Agência Brasil", "url": "x"}, ['"setor moveleiro"'], obter=lambda u: xml)
    assert len(r) == 1 and r[0]["data_publicacao"] == "2026-11-10"


def test_paginas_e_relatorio(tmp_path):
    html = '<a href="/docs/panorama-2026.pdf">Panorama 2026</a><a href="/contato">Contato</a>'
    assert paginas.links("https://abc.org.br/", html) == [
        {"texto": "Panorama 2026", "link": "https://abc.org.br/docs/panorama-2026.pdf"}]
    regs = [{"tipo": "dado_oficial", "fonte": "BCB", "serie": "Selic", "codigo": "432", "periodo_referencia": "2026-11-13",
             "valor": 15.0, "unidade": "%", "situacao_codigo": "conferido", "link": "https://api"},
            {"tipo": "jornalistico", "veiculo": "V", "autor": "", "data_publicacao": "2026-11-10", "titulo": "T",
             "link": "https://n"}]
    md = relatorio.markdown("Teste", regs)
    assert md.index("Dados estatísticos oficiais") < md.index("Análises e notícias jornalísticas")
    relatorio.gravar(tmp_path, "t", "Teste", regs)
    assert (tmp_path / "t.csv").exists()
