"""Replicação do ajuste sazonal X-13ARIMA-SEATS da PMC (IBGE).

Aprovado em 16/11/2026 (revisão pela literatura): os fatores sazonais da
procura vêm da replicação do ajuste que o IBGE aplica à PMC, com as
especificações da Nota metodológica IBGE 01/2022 (modelos ARIMA, outliers e
efeitos de calendário por série), e não mais da média simples mês ÷ ano.

- Série: PMC, tabela 8882, índice de volume sem ajuste sazonal (variável 7169).
- Colchões e Móveis usam "Móveis e eletrodomésticos" (2759), a série que o
  IBGE ajusta; Vestuário e Mochilas usam "Tecidos, vestuário e calçados"
  (90673, ajuste ADITIVO); Bicicletas e Pet usam "Outros artigos de uso
  pessoal e doméstico" (103158).
- Regressores de Carnaval (Páscoa −47, janela de 4 dias antes) e Corpus
  Christi (Páscoa +60, 3 dias depois), centrados pela média de cada mês.
- Fatores combinados (sazonal + calendário, tabela D16) previstos para 24
  meses. No ajuste aditivo, o efeito em pontos de índice é convertido em
  percentual pelo nível médio da série ajustada nos últimos 12 meses
  (conversão identificada na tela).
- Revisão anual: quando a PMC publica um ano completo novo, o servidor refaz
  a replicação. Sem o programa X-13 ou com falha, vale a última edição.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import statistics
import subprocess
import tempfile
import urllib.request
from datetime import date, timedelta
from pathlib import Path

ESTADO = "Replicação do ajuste sazonal X-13ARIMA-SEATS do IBGE (PMC)"
FONTE = "IBGE, PMC, tabela 8882 (volume sem ajuste sazonal); especificações da Nota metodológica IBGE 01/2022"
CHAVE = "sazonalidade_x13"
ARQUIVO_BASE = Path(__file__).with_name("sazonalidade_x13_base.json")

SERIES = {
    "VESTUARIO": dict(codigo=90673, nome="Tecidos, vestuário e calçados", ini=2000, transf="none", modo="add",
                      arima="(2 1 2)(1 1 1)",
                      vars="TC2003.May LS2017.Jan AO2020.Mar TC2020.Apr TC2020.Aug TC2021.Mar TC2021.May"),
    "MOVEIS": dict(codigo=2759, nome="Móveis e eletrodomésticos", ini=2000, transf="log", modo="mult",
                   arima="(1 1 0)(0 1 1)", vars="easter[8] TC2020.Mar AO2020.Apr LS2020.Jun AO2021.Mar"),
    "OUTROS": dict(codigo=103158, nome="Outros artigos de uso pessoal e doméstico", ini=2003, transf="log",
                   modo="mult", arima="(1 1 1)(1 1 1)",
                   vars="td easter[1] TC2019.May AO2020.Mar TC2020.Apr LS2020.Jun AO2021.Jul"),
}


def pascoa(ano: int) -> date:
    """Domingo de Páscoa (algoritmo gregoriano de Meeus/Jones/Butcher)."""
    b, c = ano // 100, ano % 100
    d = (19 * (ano % 19) + b - b // 4 - (b - (8 * b + 13) // 25) + 15) % 30
    e = (32 + 2 * (b % 4) + 2 * (c // 4) - d - (c % 4)) % 7
    f = d + e - 7 * ((ano % 19 + 11 * d + 22 * e) // 451) + 114
    return date(ano, f // 31, f % 31 + 1)


def _regressor(ini: int, fim: int, base: int, anos: range) -> dict:
    bruto = {}
    for a in anos:
        alvo = pascoa(a) + timedelta(days=base)
        for m in range(1, 13):
            bruto[(a, m)] = 0.0
        dias = [alvo + timedelta(days=k) for k in range(ini, fim + 1)]
        for d in dias:
            bruto[(d.year, d.month)] = bruto.get((d.year, d.month), 0.0) + 1 / len(dias)
    media = {m: statistics.mean(bruto[(a, m)] for a in anos) for m in range(1, 13)}
    return {(a, m): bruto[(a, m)] - media[m] for a in anos for m in range(1, 13)}


def encontrar_binario() -> str | None:
    """Programa X-13: variável X13_BIN, binário oficial no PATH ou pacote x13binary."""
    candidato = os.environ.get("X13_BIN")
    if candidato and os.path.exists(candidato):
        return candidato
    for nome in ("x13as_ascii", "x13as", "x13as_html"):
        caminho = shutil.which(nome)
        if caminho:
            return caminho
    try:
        import x13binary
        return x13binary.find_x13_bin()
    except Exception:
        return None


def replicar(series: dict[str, dict[str, float]], binario: str | None = None, meses_previstos: int = 24) -> dict:
    """Roda o X-13 para as três séries ({chave: {"AAAAMM": índice}}) e devolve a edição."""
    binario = binario or encontrar_binario()
    if not binario:
        raise RuntimeError("Programa X-13ARIMA-SEATS não encontrado no servidor.")
    ultimo = max(max(s) for s in series.values())
    anos = range(1999, int(ultimo[:4]) + 4)
    carnaval, corpus = _regressor(-4, -1, -47, anos), _regressor(1, 3, 60, anos)
    previsto, detalhes = {}, {}
    with tempfile.TemporaryDirectory() as pasta:
        with open(os.path.join(pasta, "feriados.dat"), "w") as f:
            for a in anos:
                for m in range(1, 13):
                    f.write(f"{a} {m} {carnaval[(a, m)]:.6f} {corpus[(a, m)]:.6f}\n")
        for chave, s in SERIES.items():
            dados = sorted((p, v) for p, v in series[chave].items() if int(p[:4]) >= s["ini"])
            with open(os.path.join(pasta, f"{chave}.dat"), "w") as f:
                for p, v in dados:
                    f.write(f"{p[:4]} {int(p[4:])} {v}\n")
            spec = (f'series{{ title="{chave}" file="{chave}.dat" format="datevalue" period=12 }}\n'
                    f"transform{{ function={s['transf']} }}\n"
                    f"regression{{\n variables=({s['vars']})\n user=(carnaval corpus)\n"
                    ' file="feriados.dat" format="datevalue" usertype=holiday\n}\n'
                    f"arima{{ model={s['arima']} }}\noutlier{{ types=(all) }}\n"
                    f"forecast{{ maxlead={meses_previstos} maxback=0 }}\n"
                    f"x11{{ mode={s['modo']} save=(d11 d16) appendfcst=yes }}\n")
            with open(os.path.join(pasta, f"{chave}.spc"), "w") as f:
                f.write(spec)
            r = subprocess.run([binario, chave], cwd=pasta, capture_output=True, text=True, timeout=300)
            d11, d16 = (_ler(os.path.join(pasta, f"{chave}.{ext}")) for ext in ("d11", "d16"))
            if r.returncode != 0 or not d16:
                raise RuntimeError(f"X-13 falhou na série {s['nome']}.")
            futuros = {p: v for p, v in d16.items() if p > dados[-1][0]}
            if s["modo"] == "add":
                nivel = statistics.mean(v for p, v in sorted(d11.items())[-12:])
                fatores = {p: round(1 + v / nivel, 4) for p, v in futuros.items()}
                detalhes[chave] = {"ajuste": "aditivo",
                                   "conversao": f"1 + efeito ÷ nível médio da série ajustada nos 12 meses até {dados[-1][0]} ({nivel:.2f})"}
            else:
                fatores = {p: round(v, 4) for p, v in futuros.items()}
                detalhes[chave] = {"ajuste": "multiplicativo"}
            previsto[chave] = fatores
            detalhes[chave].update(atividade=s["nome"], codigo=s["codigo"], arima=s["arima"])
    return {"metodo": "X13", "estado": ESTADO, "fonte": FONTE, "dados_ate": ultimo,
            "rodado_em": date.today().isoformat(), "previsto": previsto, "detalhes": detalhes}


def _ler(caminho: str) -> dict[str, float]:
    if not os.path.exists(caminho):
        return {}
    saida = {}
    for linha in open(caminho).read().splitlines()[2:]:
        partes = linha.split()
        if len(partes) >= 2:
            saida[partes[0]] = float(partes[1])
    return saida


def consultar_ibge(abrir=urllib.request.urlopen) -> dict[str, dict[str, float]]:
    codigos = ",".join(str(s["codigo"]) for s in SERIES.values())
    url = ("https://servicodados.ibge.gov.br/api/v3/agregados/8882/periodos/200001-209912/variaveis/7169"
           f"?localidades=N1[all]&classificacao=11046[56734]|85[{codigos}]")
    with abrir(url, timeout=60) as resposta:
        dados = json.loads(resposta.read().decode("utf-8"))
    por_codigo = {}
    for resultado in dados[0]["resultados"]:
        categoria = next(c for c in resultado["classificacoes"] if c["id"] == "85")["categoria"]
        por_codigo[int(next(iter(categoria)))] = {p: float(v) for p, v in resultado["series"][0]["serie"].items()
                                                  if v not in ("-", "...", "X", "")}
    return {chave: por_codigo[s["codigo"]] for chave, s in SERIES.items()}


def edicao_base() -> dict:
    return json.loads(ARQUIVO_BASE.read_text(encoding="utf-8"))


def edicao_vigente(db) -> dict:
    from ..models import SerieOficial
    registro = db.query(SerieOficial).filter_by(chave=CHAVE).first() if db is not None else None
    return dict(registro.dados) if registro and registro.dados else edicao_base()


def atualizar(db, hoje=None, abrir=urllib.request.urlopen, binario=None) -> bool:
    """Revisão anual: refaz a replicação quando a PMC tem um ano completo novo."""
    from ..models import SerieOficial, agora
    hoje = hoje or date.today()
    atual = edicao_vigente(db)
    registro = db.query(SerieOficial).filter_by(chave=CHAVE).first()
    if int(str(atual.get("dados_ate", "000000"))[:4]) >= hoje.year - 1 and str(atual.get("dados_ate", "")).endswith("12"):
        return False
    if registro and registro.tentado_em and agora() - registro.tentado_em < timedelta(days=1):
        return False
    if registro is None:
        registro = SerieOficial(chave=CHAVE, dados=None)
        db.add(registro)
    registro.tentado_em = agora()
    try:
        series = consultar_ibge(abrir)
        if max(max(s) for s in series.values()) < f"{hoje.year - 1}12":
            raise ValueError("A PMC ainda não publicou dezembro do último ano.")
        registro.dados = replicar(series, binario)
        registro.erro = None
    except Exception as erro:
        registro.erro = str(erro)[:500]
        logging.getLogger(__name__).warning("Replicação X-13 não atualizada: %s", erro)
        db.commit()
        return False
    db.commit()
    return True


def ciclo() -> None:
    from ..database import SessionLocal
    with SessionLocal() as db:
        atualizar(db)
