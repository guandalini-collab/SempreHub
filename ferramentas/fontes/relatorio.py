"""Relatórios em Markdown, CSV e JSON, separando dado oficial, publicação a conferir e notícia."""
from __future__ import annotations

import csv
import json
from pathlib import Path

SECOES = (
    ("dado_oficial", "Dados estatísticos oficiais"),
    ("publicacao_a_conferir", "Publicações novas das associações (a conferir antes de usar)"),
    ("jornalistico", "Análises e notícias jornalísticas (não são dado oficial)"),
    ("falha", "Fontes que falharam nesta coleta"),
)


def _fmt(v):
    if isinstance(v, float):
        return f"{v:,.4f}".replace(",", "X").replace(".", ",").replace("X", ".").rstrip("0").rstrip(",")
    return "" if v is None else str(v)


def markdown(titulo: str, registros: list[dict]) -> str:
    linhas = [f"# {titulo}", ""]
    for tipo, nome in SECOES:
        grupo = [r for r in registros if r.get("tipo") == tipo]
        if not grupo:
            continue
        linhas += [f"## {nome}", ""]
        if tipo == "dado_oficial":
            linhas += ["| Fonte | Série | Código | Período de referência | Valor | Unidade | Situação do código | Link |",
                       "|---|---|---|---|---|---|---|---|"]
            for r in grupo:
                linhas.append(f"| {r['fonte']} | {r['serie']} | {r['codigo']} | {r['periodo_referencia']} | "
                              f"{_fmt(r['valor'])} | {r['unidade']} | {r['situacao_codigo']} | [consulta]({r['link']}) |")
        elif tipo == "jornalistico":
            linhas += ["| Data de publicação | Veículo | Autor | Título | Link |", "|---|---|---|---|---|"]
            for r in sorted(grupo, key=lambda x: x.get("data_publicacao", ""), reverse=True):
                linhas.append(f"| {r['data_publicacao']} | {r['veiculo']} | {r['autor'] or '—'} | "
                              f"{r['titulo'].replace('|', '/')} | [abrir]({r['link']}) |")
        elif tipo == "publicacao_a_conferir":
            linhas += ["| Setor | Entidade | Texto do link | Link |", "|---|---|---|---|"]
            for r in grupo:
                linhas.append(f"| {r['setor']} | {r['entidade']} | {r['texto'].replace('|', '/')} | [abrir]({r['link']}) |")
        else:
            linhas += [f"- {r.get('fonte')}: {r.get('erro')}" for r in grupo]
        linhas.append("")
    return "\n".join(linhas)


def gravar(pasta: Path, nome: str, titulo: str, registros: list[dict]) -> dict:
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / f"{nome}.json").write_text(json.dumps(registros, ensure_ascii=False, indent=1, default=str))
    (pasta / f"{nome}.md").write_text(markdown(titulo, registros))
    planos = [r for r in registros if r.get("tipo") != "falha"]
    if planos:
        campos = sorted({k for r in planos for k, v in r.items() if not isinstance(v, (dict, list))})
        with open(pasta / f"{nome}.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=campos, extrasaction="ignore")
            w.writeheader()
            w.writerows(planos)
    return {"json": str(pasta / f"{nome}.json"), "md": str(pasta / f"{nome}.md")}


def markdown_bibliografia(linhas: list[dict]) -> str:
    saida = ["# Tabela bibliográfica", "",
             "O resumo é o publicado pelos autores (abstract), não uma síntese de achados. "
             "Nenhuma obra deve ser citada no manual sem a leitura do texto.", "",
             "| Ano | Título | Periódico | DOI | DOI no Crossref | Acesso aberto | PDF aberto | Resumo publicado |",
             "|---|---|---|---|---|---|---|---|"]
    for l in sorted(linhas, key=lambda x: (x.get("ano") or 0), reverse=True):
        resumo = (l.get("resumo") or "").replace("|", "/")
        resumo = resumo[:400] + ("…" if len(resumo) > 400 else "")
        pdf = f"[PDF]({l['pdf_aberto']})" if l.get("pdf_aberto") else "—"
        saida.append(f"| {l.get('ano') or ''} | {(l.get('titulo') or '').replace('|', '/')} | {l.get('periodico') or ''} | "
                     f"[{l['doi']}](https://doi.org/{l['doi']}) | {'sim' if l.get('doi_conferido_crossref') else 'não'} | "
                     f"{'sim' if l.get('acesso_aberto') else 'não'} | {pdf} | {resumo} |")
    return "\n".join(saida)
