#!/usr/bin/env python3
"""Gera HTML e PDF dos manuais sem depender de serviços externos.

Uso, a partir da raiz do repositório:
    python3 docs/gerar_manuais.py

O script usa Pandoc para converter Markdown em HTML e WeasyPrint
para imprimir o HTML em A4. As imagens e o CSS são locais, portanto a geração
é reproduzível mesmo sem internet.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
OUT = DOCS / "gerados"


def require(command: str) -> str:
    path = shutil.which(command)
    if not path:
        raise SystemExit(f"Comando necessário não encontrado: {command}")
    return path


def build(stem: str) -> None:
    source = DOCS / f"{stem}.md"
    html = OUT / f"{stem}.html"
    pdf = OUT / f"{stem}.pdf"
    subprocess.run(
        [
            require("pandoc"), str(source), "--from=markdown", "--to=html5",
            "--standalone", "--metadata", "lang=pt-BR",
            "--metadata", f"title=Manual SempreHub",
            "--css=../manual.css", "--output", str(html),
        ],
        check=True,
        cwd=DOCS,
    )
    # O Markdown é legível diretamente em docs/, enquanto o HTML fica em
    # docs/gerados/. Ajusta somente os caminhos relativos dos recursos locais.
    texto = html.read_text(encoding="utf-8")
    texto = texto.replace('src="diagramas/', 'src="../diagramas/')
    texto = texto.replace('src="../frontend/', 'src="../../frontend/')
    html.write_text(texto, encoding="utf-8")
    from weasyprint import HTML
    HTML(filename=str(html)).write_pdf(str(pdf))
    if not pdf.exists() or pdf.stat().st_size < 20_000:
        raise SystemExit(f"PDF inválido ou vazio: {pdf}")
    print(f"gerado {pdf.relative_to(ROOT)} ({pdf.stat().st_size:,} bytes)")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    build("manual-aluno")
    build("manual-professor")
    build("manual-midias")
    publicos = ROOT / "frontend" / "public" / "manuais"
    publicos.mkdir(parents=True, exist_ok=True)
    for nome in ("manual-aluno", "manual-professor", "manual-midias"):
        shutil.copyfile(OUT / f"{nome}.pdf", publicos / f"{nome}.pdf")


if __name__ == "__main__":
    main()
