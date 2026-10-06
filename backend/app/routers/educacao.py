"""Rotas de conteúdo didático, sem estado específico de turma ou empresa."""

from fastapi import APIRouter, HTTPException, Query

from ..educacao import (
    listar_analises,
    listar_categorias_midia,
    listar_midias,
    listar_referencias,
    listar_segmentacoes,
    obter_analise,
    obter_conteudo_educacional,
    obter_midia,
    obter_ressalvas,
)


router = APIRouter(prefix="/api/educacao", tags=["educação"])


@router.get("")
@router.get("/")
def conteudo_educacional():
    """Entrega o pacote completo para a biblioteca educacional."""
    return obter_conteudo_educacional()


@router.get("/referencias")
def referencias():
    return {"referencias": listar_referencias()}


@router.get("/analises")
def analises():
    return {"analises": listar_analises()}


@router.get("/analises/{slug}")
def analise(slug: str):
    item = obter_analise(slug)
    if item is None:
        raise HTTPException(status_code=404, detail="Análise educacional não encontrada.")
    return item


@router.get("/segmentacoes")
def segmentacoes():
    return {"segmentacoes": listar_segmentacoes()}


@router.get("/midias/categorias")
def categorias_midia():
    return {"categorias": listar_categorias_midia()}


@router.get("/midias")
def midias(categoria: str | None = Query(default=None, min_length=1, max_length=40)):
    itens = listar_midias(categoria)
    if categoria is not None and not itens:
        raise HTTPException(status_code=404, detail="Categoria de mídia não encontrada.")
    return {
        "midias": itens,
        "categorias": listar_categorias_midia(),
        "ressalvas": obter_ressalvas(),
    }


@router.get("/midias/{slug}")
def midia(slug: str):
    item = obter_midia(slug)
    if item is None:
        raise HTTPException(status_code=404, detail="Mídia educacional não encontrada.")
    return {"midia": item, "ressalvas": obter_ressalvas()}


@router.get("/ressalvas")
def ressalvas():
    return {"ressalvas": obter_ressalvas()}
