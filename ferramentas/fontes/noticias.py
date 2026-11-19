"""Notícias: GDELT (sem chave), RSS, The Guardian e NYT (com chave).

Regra de curadoria: tudo o que sai daqui é marcado como ``tipo = "jornalistico"`` e
nunca se mistura aos dados oficiais. Guarda-se só título, veículo, autor, data, link e
um trecho curto do resumo do próprio feed — o texto integral não é copiado.
"""
from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from datetime import date, datetime
from email.utils import parsedate_to_datetime

from .rede import obter_json, obter_texto, url

GDELT = "https://api.gdeltproject.org/api/v2/doc/doc"
GUARDIAN = "https://content.guardianapis.com/search"
NYT = "https://api.nytimes.com/svc/search/v2/articlesearch.json"

TERMOS = {
    "vestuario": ['"varejo de moda"', '"setor de vestuário"', '"indústria têxtil"'],
    "colchoes": ['"indústria de colchões"', 'colchões varejo'],
    "moveis": ['"setor moveleiro"', '"indústria moveleira"'],
    "bicicletas": ['"indústria de bicicletas"', '"bicicletas elétricas"'],
    "pet": ['"mercado pet"', '"setor pet"'],
    "mochilas": ['"artigos de viagem"', 'mochilas "volta às aulas"'],
    "ruptura": ['"ruptura de estoque"', '"falta de produtos" varejo'],
}

# Feeds conferidos ficam com conferido=True após o primeiro teste (``python -m fontes conferir``).
FEEDS = [
    {"veiculo": "Agência Brasil (últimas notícias)", "url": "https://agenciabrasil.ebc.com.br/feed/ultimasnoticias/feed.xml",
     "conferido": False, "nota": "endereço visto em diretório de feeds (feeder.co); conferir"},
    # Acrescente aqui os feeds de Valor, Exame, InfoMoney, Retail Dive e HBR depois de
    # conferir o endereço na página do próprio veículo.
]


def _trecho(texto: str, n: int = 280) -> str:
    texto = " ".join((texto or "").split())
    return texto if len(texto) <= n else texto[: n - 1].rsplit(" ", 1)[0] + "…"


def _item(veiculo, titulo, link, data_pub, autor="", resumo="", origem=""):
    return {"tipo": "jornalistico", "veiculo": veiculo, "autor": autor or "", "data_publicacao": data_pub,
            "titulo": titulo, "link": link, "trecho": _trecho(resumo), "coletado_por": origem,
            "consultado_em": date.today().isoformat()}


def gdelt(termos: str, dias: int = 30, idioma: str = "portuguese", limite: int = 50, obter=obter_json) -> list[dict]:
    # O GDELT só aceita parênteses em torno de termos ligados por OR.
    grupo = f"({termos})" if " OR " in termos else termos
    consulta = f"{grupo} sourcelang:{idioma}" if idioma else grupo
    endereco = url(GDELT, {"query": consulta, "mode": "artlist", "format": "json",
                           "maxrecords": str(limite), "timespan": f"{dias}d", "sort": "datedesc"})
    try:
        resposta = obter(endereco)
    except ValueError as e:  # o GDELT responde em texto quando recusa a consulta
        raise RuntimeError(f"GDELT recusou a consulta {consulta!r}: resposta não é JSON") from e
    saida = []
    for a in resposta.get("articles", []):
        bruto = a.get("seendate", "")  # formato AAAAMMDDTHHMMSSZ
        try:
            data_pub = datetime.strptime(bruto, "%Y%m%dT%H%M%SZ").date().isoformat()
        except ValueError:
            data_pub = bruto
        saida.append(_item(a.get("domain", ""), a.get("title", ""), a.get("url", ""), data_pub,
                           origem="GDELT DOC 2.0 (data = primeira detecção pelo GDELT)"))
    return saida


def rss(feed: dict, termos: list[str] | None = None, obter=obter_texto) -> list[dict]:
    raiz = ET.fromstring(obter(feed["url"]))
    saida = []
    for it in raiz.iter("item"):
        titulo = (it.findtext("title") or "").strip()
        resumo = it.findtext("description") or ""
        if termos and not any(t.strip('"').lower() in (titulo + " " + resumo).lower() for t in termos):
            continue
        data_txt = it.findtext("pubDate") or ""
        try:
            data_pub = parsedate_to_datetime(data_txt).date().isoformat()
        except (TypeError, ValueError):
            data_pub = data_txt
        autor = it.findtext("{http://purl.org/dc/elements/1.1/}creator") or it.findtext("author") or ""
        saida.append(_item(feed["veiculo"], titulo, (it.findtext("link") or "").strip(), data_pub, autor, resumo,
                           origem="RSS"))
    return saida


def guardian(termos: str, desde: str | None = None, obter=obter_json) -> list[dict]:
    chave = os.environ.get("GUARDIAN_API_KEY")
    if not chave:
        return [{"tipo": "falha", "fonte": "The Guardian", "erro": "defina GUARDIAN_API_KEY (chave gratuita)"}]
    endereco = url(GUARDIAN, {"q": termos, "api-key": chave, "show-fields": "byline,trailText",
                              "order-by": "newest", **({"from-date": desde} if desde else {})})
    saida = []
    for r in obter(endereco)["response"]["results"]:
        f = r.get("fields", {})
        saida.append(_item("The Guardian", r["webTitle"], r["webUrl"], r["webPublicationDate"][:10],
                           f.get("byline", ""), f.get("trailText", ""), "Guardian Open Platform"))
    return saida


def nyt(termos: str, obter=obter_json) -> list[dict]:
    chave = os.environ.get("NYT_API_KEY")
    if not chave:
        return [{"tipo": "falha", "fonte": "The New York Times", "erro": "defina NYT_API_KEY"}]
    endereco = url(NYT, {"q": termos, "sort": "newest", "api-key": chave})
    saida = []
    for d in (obter(endereco).get("response") or {}).get("docs") or []:
        saida.append(_item("The New York Times", (d.get("headline") or {}).get("main", ""), d.get("web_url", ""),
                           (d.get("pub_date") or "")[:10], (d.get("byline") or {}).get("original", ""),
                           d.get("abstract", ""), "NYT Article Search"))
    return saida


def setor(nome: str, dias: int = 30, obter=obter_json, obter_txt=obter_texto) -> list[dict]:
    termos = TERMOS[nome]
    saida = []
    try:
        saida += gdelt(" OR ".join(termos), dias, obter=obter)
    except Exception as e:  # noqa: BLE001
        saida.append({"tipo": "falha", "fonte": "GDELT", "erro": str(e)[:200]})
    for f in FEEDS:
        try:
            saida += rss(f, termos, obter=obter_txt)
        except Exception as e:  # noqa: BLE001
            saida.append({"tipo": "falha", "fonte": f["veiculo"], "erro": str(e)[:200]})
    return saida
