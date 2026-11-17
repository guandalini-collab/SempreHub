"""Tamanho do mercado simulado pela PAC e pela PMC (Grupo 2, item 4).

Aprovado em 16/11/2026:
    mercado (R$/mês) = receita mensal estimada da loja pequena da atividade
                       × número de lojas na disputa (equipes + concorrentes simulados)
                       × sazonalidade do mês (IBGE/PMC)
                       × atualização pela receita nominal da PMC

- Receita por loja: PAC 2024, tabela 10645 (receita líquida de revenda ÷
  unidades locais com receita de revenda, por mês).
- Loja pequena: PAC 2024, tabela 10647 (varejo): receita da faixa até 19
  pessoas ÷ média do varejo = 0,4348. A razão só existe para o varejo total e
  é aplicada às atividades: ESTIMATIVA, identificada como tal.
- Atualização: PMC, tabela 8883 (índice de receita nominal, sem ajuste
  sazonal): média dos últimos 12 meses publicados ÷ média de 2024. A PMC
  cobre empresas com 20 ou mais pessoas ocupadas (aviso exibido).
- A disputa é em reais (opção B, aprovada em 17/11/2026, com base em Cooper
  e Nakanishi, Market-Share Analysis): cada loja recebe uma fatia em reais, e
  cada produto converte a sua parte em unidades pelo próprio preço.
"""
from __future__ import annotations

import json
import logging
import urllib.request
from datetime import timedelta
from statistics import mean

RAZAO_LOJA_PEQUENA = 0.4348
FONTE_PAC = "IBGE, PAC 2024, tabelas 10645 e 10647"
FONTE_PMC = "IBGE, PMC, tabela 8883 (receita nominal, sem ajuste sazonal)"
AVISO = ("Estimativa: a razão loja pequena/média (0,4348) só é publicada para o varejo total; "
         "a PMC cobre empresas com 20 ou mais pessoas ocupadas.")
CHAVE = "pmc_receita_nominal"

# setor → (atividade da PAC, receita líquida de revenda por unidade local, R$/mês)
RECEITA_LOJA = {
    "colchoes": ("4754+4757+4759 Móveis, iluminação e outros artigos de uso doméstico", 95_000.0),
    "moveis": ("4754+4757+4759 Móveis, iluminação e outros artigos de uso doméstico", 95_000.0),
    "vestuario": ("4781 Vestuário e complementos", 78_500.0),
    "bicicletas": ("47.6 Artigos culturais, recreativos e esportivos", 95_700.0),
    "pet": ("4783+4785+4789 Outros produtos novos e usados", 81_600.0),
    "mochilas": ("4782 Calçados, artigos de couro e de viagem", 107_700.0),
}
# setor → código da atividade na PMC (classificação 85)
ATIVIDADE_PMC = {"colchoes": 31555, "moveis": 31555, "vestuario": 90673,
                 "bicicletas": 103158, "pet": 103158, "mochilas": 90673}

# Série consultada na API do IBGE em 17/11/2026 (jan/2024 a set/2026).
BASE = {"consultado_em": "2026-11-17", "series": {
    "31555": dict(zip([f"{a}{m:02d}" for a in (2024, 2025, 2026) for m in range(1, 13)][:33], [
        100.76598, 93.87153, 98.13738, 101.62653, 108.47394, 105.29003, 111.19906, 107.71579, 99.30221, 105.46548, 132.20381, 129.32055,
        104.29020, 95.28463, 97.60151, 97.56696, 111.92258, 99.02666, 107.64854, 100.86835, 100.69707, 101.52267, 130.89992, 130.88347,
        104.19221, 88.29348, 99.93211, 96.33880, 113.15469, 104.22345, 106.11543, 101.15920, 99.47647])),
    "90673": dict(zip([f"{a}{m:02d}" for a in (2024, 2025, 2026) for m in range(1, 13)][:33], [
        87.60510, 77.31627, 88.74878, 92.04871, 112.64742, 112.11639, 111.53797, 105.66865, 94.37517, 102.90364, 121.57472, 195.82518,
        91.44645, 85.86005, 92.10114, 102.26039, 124.06853, 123.74655, 113.61702, 110.19839, 96.74348, 104.68825, 122.46243, 199.00588,
        96.45098, 84.27809, 98.49445, 102.76944, 133.00871, 125.34405, 110.98202, 108.32917, 101.80633])),
    "103158": dict(zip([f"{a}{m:02d}" for a in (2024, 2025, 2026) for m in range(1, 13)][:33], [
        96.29952, 87.61107, 103.03587, 90.29769, 104.18660, 94.69458, 106.52185, 96.78528, 94.17721, 105.77752, 130.27254, 136.23065,
        104.25821, 93.35797, 100.92223, 105.28825, 109.86262, 101.21155, 112.85763, 103.19337, 101.52634, 111.69087, 142.11341, 142.63844,
        110.23261, 91.23400, 115.33465, 109.09722, 115.10021, 110.97372, 114.54964, 109.91661, 107.54207])),
}}


def fator_atualizacao(serie: dict[str, float]) -> tuple[float, str]:
    """Média dos últimos 12 meses ÷ média de 2024."""
    base = [v for p, v in serie.items() if p.startswith("2024")]
    meses = sorted(serie)[-12:]
    if len(base) < 12 or len(meses) < 12:
        raise ValueError("Série da PMC incompleta.")
    return mean(serie[p] for p in meses) / mean(base), f"{meses[0]} a {meses[-1]}"


def series_vigentes(db=None) -> dict:
    if db is not None:
        from .models import SerieOficial
        registro = db.query(SerieOficial).filter_by(chave=CHAVE).first()
        if registro and registro.dados:
            return dict(registro.dados)
    return dict(BASE)


def receita_mensal_loja(setor: str, series: dict | None = None) -> dict:
    """Receita mensal estimada de uma loja pequena da atividade, atualizada."""
    atividade, receita = RECEITA_LOJA[setor]
    series = (series or BASE)["series"]
    fator, periodo = fator_atualizacao(series[str(ATIVIDADE_PMC[setor])])
    return {"receita": round(receita * RAZAO_LOJA_PEQUENA * fator, 2), "atividade_pac": atividade,
            "receita_media_pac": receita, "razao_loja_pequena": RAZAO_LOJA_PEQUENA,
            "fator_pmc": round(fator, 4), "periodo_pmc": periodo,
            "fontes": [FONTE_PAC, FONTE_PMC], "aviso": AVISO}


def consultar(abrir=urllib.request.urlopen) -> dict:
    codigos = ",".join(sorted({str(c) for c in ATIVIDADE_PMC.values()}))
    url = ("https://servicodados.ibge.gov.br/api/v3/agregados/8883/periodos/202401-209912/variaveis/7169"
           f"?localidades=N1[all]&classificacao=11046[56735]|85[{codigos}]")
    with abrir(url, timeout=30) as resposta:
        dados = json.loads(resposta.read().decode("utf-8"))
    series = {}
    for resultado in dados[0]["resultados"]:
        codigo = next(c for c in resultado["classificacoes"] if c["id"] == "85")["categoria"]
        series[next(iter(codigo))] = {p: float(v) for p, v in resultado["series"][0]["serie"].items()
                                      if v not in ("-", "...", "X", "")}
    for serie in series.values():
        fator_atualizacao(serie)  # recusa série incompleta
    return series


def atualizar(db, abrir=urllib.request.urlopen) -> bool:
    from .models import SerieOficial, agora
    registro = db.query(SerieOficial).filter_by(chave=CHAVE).first()
    if registro and registro.tentado_em and agora() - registro.tentado_em < timedelta(days=1):
        return False
    if registro is None:
        registro = SerieOficial(chave=CHAVE, dados=None)
        db.add(registro)
    registro.tentado_em = agora()
    try:
        registro.dados = {"series": consultar(abrir), "consultado_em": agora().date().isoformat()}
        registro.erro = None
    except Exception as erro:
        registro.erro = str(erro)[:500]
        logging.getLogger(__name__).warning("PMC (receita nominal) não atualizada: %s", erro)
        db.commit()
        return False
    db.commit()
    return True


def ciclo() -> None:
    from .database import SessionLocal
    with SessionLocal() as db:
        atualizar(db)



def demanda_por_loja(turma, planos=None, fator_periodo: float = 1.0) -> dict | None:
    """Receita de mercado por loja no período (R$), ou None sem catálogo fixo.

    Opção B (aprovada em 17/11/2026): a disputa entre lojas é em reais
    (Cooper e Nakanishi, Market-Share Analysis, cap. 2, eq. 2.1, e cap. 4); as
    unidades são calculadas depois, produto a produto, pelo preço de cada um.
    """
    if getattr(turma, "modo_jogo", None) == "STARTUP":
        return None
    from .routers.mercado import chave_setor
    setor = chave_setor((turma.configuracao_simulacao or {}).get("setor_mercado"))
    if not setor:
        return None
    from .database import SessionLocal
    with SessionLocal() as db:
        series = series_vigentes(db)
    return {**receita_mensal_loja(setor, series), "fator_periodo": fator_periodo}
