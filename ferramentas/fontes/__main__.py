"""Linha de comando.

Exemplos (rodar dentro da pasta ``ferramentas``):
  python -m fontes macro
  python -m fontes setor vestuario
  python -m fontes boletim                      # macro + 6 setores + páginas + notícias
  python -m fontes bibliografia --doi 10.1287/mnsc.1060.0577 --termos "apparel stockout" --desde 2020
  python -m fontes noticias vestuario --dias 30
  python -m fontes conferir                     # testa cada código do catálogo na API real
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from . import bibliografia, catalogo, indicadores, noticias, paginas, relatorio

SETORES = ("vestuario", "colchoes", "moveis", "bicicletas", "pet", "mochilas")
SAIDA = Path(__file__).resolve().parent.parent / "saida"


def _pasta() -> Path:
    return SAIDA / date.today().isoformat()


def conferir() -> list[dict]:
    """Chama cada código uma vez e informa se a API respondeu e o que respondeu."""
    resultado = []

    def teste(rotulo, funcao):
        try:
            r = funcao()
            ok = [x for x in r if x.get("tipo") != "falha"]
            resultado.append({"item": rotulo, "ok": bool(ok), "amostra": (ok[:1] or r[:1])})
        except Exception as e:  # noqa: BLE001
            resultado.append({"item": rotulo, "ok": False, "erro": str(e)[:300]})

    for codigo in catalogo.SGS:
        teste(f"SGS {codigo}", lambda c=codigo: indicadores.sgs(c))
    teste("IPCA SIDRA 7060", indicadores.ipca)
    for ind in catalogo.FOCUS["indicadores"]:
        teste(f"Focus {ind}", lambda i=ind: indicadores.focus(i))
    for s in SETORES:
        teste(f"PMC {s}", lambda x=s: indicadores.pmc(x))
        teste(f"PIM {s}", lambda x=s: indicadores.pim(x))
        teste(f"Comex {s}", lambda x=s: indicadores.comex(x))
    for f in noticias.FEEDS:
        teste(f"RSS {f['veiculo']}", lambda f=f: noticias.rss(f))
    teste("GDELT", lambda: noticias.gdelt('"varejo"', 7, limite=3))
    teste("Crossref", lambda: [bibliografia.crossref("10.1287/mnsc.1060.0577")])
    teste("OpenAlex", lambda: [bibliografia.openalex_doi("10.1287/mnsc.1060.0577")])
    return resultado


def main(argv=None):
    p = argparse.ArgumentParser(prog="fontes", description="Coleta de fontes públicas do SempreHub")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("macro")
    s = sub.add_parser("setor"); s.add_argument("nome", choices=SETORES)
    sub.add_parser("boletim")
    sub.add_parser("paginas")
    n = sub.add_parser("noticias"); n.add_argument("nome", choices=SETORES + ("ruptura",)); n.add_argument("--dias", type=int, default=30)
    b = sub.add_parser("bibliografia")
    b.add_argument("--doi", nargs="*", default=[]); b.add_argument("--termos", nargs="*", default=[])
    b.add_argument("--setor", choices=tuple(bibliografia.TERMOS_SETORIAIS))
    b.add_argument("--desde", type=int); b.add_argument("--aberto", action="store_true"); b.add_argument("--s2", action="store_true")
    sub.add_parser("conferir")
    a = p.parse_args(argv)

    pasta = _pasta()
    if a.cmd == "macro":
        print(relatorio.gravar(pasta, "macro", f"Indicadores macroeconômicos — {date.today():%d/%m/%Y}", indicadores.macro()))
    elif a.cmd == "setor":
        regs = indicadores.setor(a.nome)
        print(relatorio.gravar(pasta, f"setor-{a.nome}", f"Indicadores do setor {a.nome} — {date.today():%d/%m/%Y}", regs))
    elif a.cmd == "paginas":
        regs = paginas.monitorar(SAIDA / "estado-paginas.json")
        print(relatorio.gravar(pasta, "paginas", "Publicações das associações", regs))
    elif a.cmd == "noticias":
        regs = noticias.setor(a.nome, a.dias)
        print(relatorio.gravar(pasta, f"noticias-{a.nome}", f"Notícias — {a.nome} — últimos {a.dias} dias", regs))
    elif a.cmd == "boletim":
        regs = indicadores.macro()
        for s_ in SETORES:
            regs += indicadores.setor(s_)
        regs += paginas.monitorar(SAIDA / "estado-paginas.json")
        for s_ in SETORES:
            regs += noticias.setor(s_, 30)
        print(relatorio.gravar(pasta, "boletim", f"Boletim de fontes — {date.today():%d/%m/%Y}", regs))
    elif a.cmd == "bibliografia":
        termos = a.termos + (bibliografia.TERMOS_SETORIAIS[a.setor] if a.setor else [])
        linhas = bibliografia.tabela(a.doi, termos, a.desde, a.aberto, a.s2)
        pasta.mkdir(parents=True, exist_ok=True)
        (pasta / "bibliografia.json").write_text(json.dumps(linhas, ensure_ascii=False, indent=1))
        (pasta / "bibliografia.md").write_text(relatorio.markdown_bibliografia(linhas))
        print({"md": str(pasta / "bibliografia.md"), "obras": len(linhas)})
    elif a.cmd == "conferir":
        r = conferir()
        pasta.mkdir(parents=True, exist_ok=True)
        (pasta / "conferencia.json").write_text(json.dumps(r, ensure_ascii=False, indent=1, default=str))
        for x in r:
            print(("OK   " if x["ok"] else "FALHA"), x["item"], "" if x["ok"] else x.get("erro", x.get("amostra")))


if __name__ == "__main__":
    main()
