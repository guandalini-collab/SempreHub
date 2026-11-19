"""Monitor de páginas das associações sem API.

Não extrai números automaticamente: lista os links de PDF e de publicações da página e
compara com a coleta anterior. O que for novo vai para o relatório como "publicação a
conferir"; o número só entra no simulador ou no manual depois da leitura e da aprovação
do professor (regra do projeto: conferência literal antes de usar).
"""
from __future__ import annotations

import json
import re
from datetime import date
from html import unescape
from pathlib import Path
from urllib.parse import urljoin

from . import catalogo
from .rede import obter_texto

PALAVRAS = ("relat", "boletim", "panorama", "informe", "dados", "pesquisa", "estat", "conjuntura", ".pdf")


def links(pagina: str, html: str) -> list[dict]:
    achados = []
    for href, texto in re.findall(r'<a[^>]+href="([^"#]+)"[^>]*>(.*?)</a>', html, flags=re.I | re.S):
        texto = unescape(re.sub(r"<[^>]+>", " ", texto)).strip()
        alvo = urljoin(pagina, href)
        if any(p in (alvo + " " + texto).lower() for p in PALAVRAS):
            achados.append({"texto": " ".join(texto.split())[:160], "link": alvo})
    unicos = {a["link"]: a for a in achados}
    return list(unicos.values())


def monitorar(estado_arquivo: Path, obter=obter_texto) -> list[dict]:
    anterior = json.loads(estado_arquivo.read_text()) if estado_arquivo.exists() else {}
    atual, saida = {}, []
    for setor, paginas in catalogo.PAGINAS.items():
        for entidade, pagina in paginas:
            try:
                encontrados = links(pagina, obter(pagina))
            except Exception as e:  # noqa: BLE001
                saida.append({"tipo": "falha", "fonte": entidade, "erro": str(e)[:200]})
                continue
            atual[pagina] = [a["link"] for a in encontrados]
            vistos = set(anterior.get(pagina, []))
            for a in encontrados:
                if a["link"] not in vistos:
                    saida.append({"tipo": "publicacao_a_conferir", "setor": setor, "entidade": entidade,
                                  "pagina": pagina, "texto": a["texto"], "link": a["link"],
                                  "primeira_coleta": not anterior, "consultado_em": date.today().isoformat()})
    estado_arquivo.parent.mkdir(parents=True, exist_ok=True)
    estado_arquivo.write_text(json.dumps(atual, ensure_ascii=False, indent=1))
    return saida
