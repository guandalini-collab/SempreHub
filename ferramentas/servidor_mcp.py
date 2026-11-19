"""Servidor MCP local para o Claude Desktop (roda no computador do professor, com a internet dele).

Instalação: pip install "mcp[cli]"
Configuração: ver ferramentas/README.md (claude_desktop_config.json).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:  # SDK MCP 2.x
    from mcp.server.mcpserver import MCPServer as Servidor  # noqa: E402
except ImportError:  # SDK MCP 1.x
    from mcp.server.fastmcp import FastMCP as Servidor  # noqa: E402

from fontes import bibliografia, indicadores, noticias, paginas, relatorio  # noqa: E402

app = Servidor("semprehub-fontes")
ESTADO = Path(__file__).resolve().parent / "saida" / "estado-paginas.json"


@app.tool()
def indicadores_macro() -> list[dict]:
    """Selic (meta e acumulada no mês), dólar, juros ao consumidor, endividamento das famílias (BCB/SGS),
    IPCA mensal e em 12 meses (IBGE/SIDRA 7060) e medianas do Boletim Focus. Cada registro traz período
    de referência, data da consulta e link."""
    return indicadores.macro()


@app.tool()
def indicadores_setor(setor: str) -> list[dict]:
    """PMC (volume e receita nominal), PIM-PF e importações (Comex Stat) do setor:
    vestuario, colchoes, moveis, bicicletas, pet ou mochilas."""
    return indicadores.setor(setor)


@app.tool()
def serie_sgs(codigo: int, ultimos: int = 12) -> list[dict]:
    """Últimas observações de uma série do SGS do Banco Central."""
    return indicadores.sgs(codigo, ultimos)


@app.tool()
def publicacoes_associacoes() -> list[dict]:
    """Links novos (relatórios, boletins, PDFs) nas páginas das associações sem API. Não extrai números."""
    return paginas.monitorar(ESTADO)


@app.tool()
def tabela_bibliografica(dois: list[str] | None = None, termos: list[str] | None = None,
                         desde: int | None = None, so_aberto: bool = False) -> str:
    """Confere DOIs no Crossref e busca estudos no OpenAlex; devolve tabela em Markdown com título, ano,
    DOI, resumo publicado e PDF aberto. O resumo é o dos autores — não substitui a leitura."""
    return relatorio.markdown_bibliografia(bibliografia.tabela(dois, termos, desde, so_aberto))


@app.tool()
def metadados_doi(doi: str) -> dict:
    """Metadados oficiais de um DOI no Crossref (autores, título, periódico, volume, páginas, ano)."""
    return bibliografia.crossref(doi)


@app.tool()
def noticias_setor(setor: str, dias: int = 30) -> list[dict]:
    """Notícias recentes (GDELT e feeds RSS conferidos) sobre o setor ou "ruptura". Marcadas como
    jornalísticas, com veículo, autor, data de publicação e link."""
    return noticias.setor(setor, dias)


if __name__ == "__main__":
    app.run()
