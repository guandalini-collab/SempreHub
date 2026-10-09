#!/usr/bin/env python3
"""Entrada única para gerar os três manuais institucionais. Requer ReportLab e Pillow."""
from gerar_manuais_reportlab import OUT,PUBLIC,build
if __name__=="__main__":
    OUT.mkdir(parents=True,exist_ok=True)
    PUBLIC.mkdir(parents=True,exist_ok=True)
    for nome in ("manual-aluno","manual-professor","manual-midias"):
        build(nome)
