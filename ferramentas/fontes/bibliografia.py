"""Bibliografia: valida DOIs no Crossref e busca estudos no OpenAlex (Semantic Scholar opcional).

Importante: o "resumo" devolvido é o resumo publicado pelos autores (abstract), não
uma síntese dos achados. Pela regra do professor, nenhuma obra é citada no manual sem
leitura do texto; a tabela serve para triagem e para a conferência de metadados.
"""
from __future__ import annotations

import os
import re
from datetime import date

from .rede import obter_json, url

CROSSREF = "https://api.crossref.org/works/"
OPENALEX = "https://api.openalex.org/works"
S2 = "https://api.semanticscholar.org/graph/v1/paper/DOI:"

TERMOS_SETORIAIS = {
    "ruptura": ["stockout consumer response", "out-of-stock retail", "ruptura de estoque"],
    "vestuario": ["apparel stockout", "fashion retail stockout", "apparel retail consumer behavior"],
    "moveis": ["furniture retail consumer", "mattress retail"],
    "bicicletas": ["bicycle retail market", "e-bike adoption"],
    "pet": ["pet food retail", "pet owners purchase behavior"],
    "mochilas": ["luggage retail", "backpack purchase behavior"],
}


def _contato() -> dict:
    # Crossref e OpenAlex pedem um e-mail de contato ("polite pool").
    email = os.environ.get("SEMPREHUB_EMAIL_CONTATO", "")
    return {"mailto": email} if email else {}


def limpar_doi(doi: str) -> str:
    doi = doi.strip()
    doi = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:\s*)", "", doi, flags=re.I)
    return doi.lower()


def _sem_tags(texto: str | None) -> str:
    return re.sub(r"<[^>]+>", " ", texto or "").replace("  ", " ").strip()


def resumo_openalex(indice: dict | None) -> str:
    """O OpenAlex entrega o resumo como índice invertido (palavra → posições)."""
    if not indice:
        return ""
    posicoes = {}
    for palavra, lista in indice.items():
        for p in lista:
            posicoes[p] = palavra
    return " ".join(posicoes[i] for i in sorted(posicoes))


def crossref(doi: str, obter=obter_json) -> dict:
    doi = limpar_doi(doi)
    endereco = url(CROSSREF + doi, _contato())
    m = obter(endereco)["message"]
    autores = "; ".join(f"{a.get('family', '')}, {a.get('given', '')}".strip(", ") for a in m.get("author", []))
    partes = (m.get("issued") or m.get("published") or {}).get("date-parts", [[None]])[0]
    return {"doi": doi, "titulo": " ".join(m.get("title", [])), "autores": autores,
            "ano": partes[0] if partes else None, "periodico": " ".join(m.get("container-title", [])),
            "volume": m.get("volume"), "numero": m.get("issue"), "paginas": m.get("page"),
            "editora": m.get("publisher"), "tipo": m.get("type"),
            "resumo_crossref": _sem_tags(m.get("abstract")), "fonte_metadados": "Crossref", "link_metadados": endereco}


def openalex_doi(doi: str, obter=obter_json) -> dict:
    endereco = url(f"{OPENALEX}/doi:{limpar_doi(doi)}", _contato())
    return _openalex_linha(obter(endereco), endereco)


def openalex_busca(termos: str, desde: int | None = None, so_aberto: bool = False, limite: int = 25,
                   obter=obter_json) -> list[dict]:
    filtros = ["type:article|review|book-chapter"]
    if desde:
        filtros.append(f"from_publication_date:{desde}-01-01")
    if so_aberto:
        filtros.append("is_oa:true")
    endereco = url(OPENALEX, {"search": termos, "filter": ",".join(filtros), "per-page": str(limite),
                              "sort": "relevance_score:desc", **_contato()})
    return [_openalex_linha(w, endereco) for w in obter(endereco).get("results", [])]


def _openalex_linha(w: dict, endereco: str) -> dict:
    oa = w.get("open_access") or {}
    melhor = w.get("best_oa_location") or {}
    fonte = ((w.get("primary_location") or {}).get("source") or {})
    return {"doi": limpar_doi(w["doi"]) if w.get("doi") else "", "titulo": w.get("title") or w.get("display_name"),
            "ano": w.get("publication_year"), "periodico": fonte.get("display_name"),
            "autores": "; ".join(a["author"]["display_name"] for a in w.get("authorships", [])[:6]),
            "citacoes": w.get("cited_by_count"), "acesso_aberto": oa.get("is_oa"),
            "pdf_aberto": melhor.get("pdf_url") or oa.get("oa_url") or "",
            "resumo_publicado": resumo_openalex(w.get("abstract_inverted_index")),
            "id_openalex": w.get("id"), "fonte_metadados": "OpenAlex", "link_metadados": endereco}


def semantic_scholar(doi: str, obter=obter_json) -> dict:
    """Opcional: TL;DR e resumo. Sem chave a API limita a taxa; com chave, use S2_API_KEY."""
    chave = os.environ.get("S2_API_KEY")
    endereco = url(S2 + limpar_doi(doi), {"fields": "title,year,abstract,tldr,openAccessPdf"})
    d = obter(endereco, cabecalhos={"x-api-key": chave} if chave else None)
    return {"s2_tldr": (d.get("tldr") or {}).get("text", ""), "s2_resumo": d.get("abstract") or "",
            "s2_pdf": (d.get("openAccessPdf") or {}).get("url", "")}


def tabela(dois: list[str] | None = None, termos: list[str] | None = None, desde: int | None = None,
           so_aberto: bool = False, com_s2: bool = False, obter=obter_json) -> list[dict]:
    """Uma linha por obra. DOIs informados: Crossref (metadados oficiais) + OpenAlex (resumo, PDF aberto).
    Termos: busca no OpenAlex; cada DOI encontrado é conferido no Crossref."""
    linhas, vistos = [], set()

    def juntar(doi, base_oa=None):
        if doi in vistos:
            return
        vistos.add(doi)
        linha = {"doi": doi, "consultado_em": date.today().isoformat()}
        try:
            linha.update(crossref(doi, obter))
            linha["doi_conferido_crossref"] = True
        except Exception as e:  # noqa: BLE001
            linha.update({"doi_conferido_crossref": False, "erro_crossref": str(e)[:200]})
        try:
            oa = base_oa or openalex_doi(doi, obter)
            for k in ("citacoes", "acesso_aberto", "pdf_aberto", "resumo_publicado", "id_openalex"):
                linha[k] = oa.get(k)
            for k in ("titulo", "ano", "periodico", "autores"):
                linha.setdefault(k, oa.get(k))
        except Exception as e:  # noqa: BLE001
            linha["erro_openalex"] = str(e)[:200]
        if com_s2:
            try:
                linha.update(semantic_scholar(doi, obter))
            except Exception as e:  # noqa: BLE001
                linha["erro_s2"] = str(e)[:200]
        linha["resumo"] = linha.get("resumo_publicado") or linha.get("resumo_crossref") or ""
        linha["situacao_leitura"] = "não lido — só metadados e resumo publicado"
        linhas.append(linha)

    for d in dois or []:
        juntar(limpar_doi(d))
    for t in termos or []:
        for oa in openalex_busca(t, desde, so_aberto, obter=obter):
            if oa["doi"]:
                juntar(oa["doi"], oa)
    return linhas


def abnt(l: dict) -> str:
    """Referência ABNT aproximada para artigo de periódico — conferir antes de usar no manual."""
    autores = "; ".join(a.split(",")[0].upper() + ("," + a.split(",", 1)[1] if "," in a else "")
                        for a in (l.get("autores") or "").split("; ") if a)
    partes = [f"{autores}. {l.get('titulo', '')}. *{l.get('periodico', '')}*"]
    if l.get("volume"):
        partes.append(f"v. {l['volume']}")
    if l.get("numero"):
        partes.append(f"n. {l['numero']}")
    if l.get("paginas"):
        partes.append(f"p. {l['paginas']}")
    partes.append(f"{l.get('ano', '')}. DOI: {l.get('doi', '')}.")
    return ", ".join(partes)
