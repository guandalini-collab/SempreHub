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
        atualizar_selic(db)



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
    return {**receita_mensal_loja(setor, series), "fator_periodo": fator_periodo, "setor": setor}


# ---------------------------------------------------------------------------
# Custos da loja (aprovado em 17/11/2026: "tudo conforme a literatura; o que
# for de mercado, buscar"). Custo de manter estoque pelos componentes da
# literatura (capital + físicos; Azzi et al., 2014, via Andriolo): o capital é
# remunerado pela Selic do mês (BCB, SGS 4390); o espaço é o aluguel da loja,
# custo fixo publicado pela PAC (sem volume por m³, que não tem fonte).
# Despesas fixas: PAC 2024, tabela 10649 (despesas no ano por atividade), por
# unidade local e por mês, na escala da loja pequena (mesma razão 0,4348).
# ---------------------------------------------------------------------------
FONTE_DESPESAS = "IBGE, PAC 2024, tabela 10649 (despesas no ano, R$ mil) ÷ unidades locais (tabela 10645)"
UNIDADES_LOCAIS = {"colchoes": 86_846, "moveis": 86_846, "vestuario": 133_797, "bicicletas": 54_113,
                   "pet": 128_563, "mochilas": 31_665}
# R$ mil no ano: aluguéis e condomínios; serviços de terceiros; comunicação; energia, água e esgoto; impostos e taxas
DESPESAS_PAC = {
    "moveis": (2_611_318, 4_021_780, 272_476, 812_014, 1_087_929),
    "bicicletas": (1_964_644, 2_288_785, 200_462, 346_552, 909_926),
    "vestuario": (5_795_575, 5_590_573, 407_805, 1_361_614, 1_660_164),
    "mochilas": (2_147_201, 1_613_371, 142_182, 312_236, 315_296),
    "pet": (2_920_556, 4_833_821, 383_593, 679_956, 1_132_119),
}
DESPESAS_PAC["colchoes"] = DESPESAS_PAC["moveis"]
ROTULOS_DESPESAS = ("Aluguel e condomínio", "Serviços de terceiros (contabilidade, informática etc.)",
                    "Comunicação", "Energia, água e esgoto", "Impostos e taxas (IPTU, alvarás etc.)")
CHAVE_SELIC = "selic_mensal"
# BCB, SGS 4390 (Selic acumulada no mês, % a.m.), consultada em 17/11/2026.
SELIC_BASE = {"serie": {"202510": 1.28, "202511": 1.05, "202512": 1.22, "202601": 1.16, "202602": 1.00,
                        "202603": 1.21, "202604": 1.09, "202605": 1.07, "202606": 1.12, "202607": 1.22,
                        "202608": 1.09, "202609": 1.08, "202610": 1.07}, "consultado_em": "2026-11-17"}


def custos_fixos_loja(setor: str) -> dict:
    componentes = [round(v * 1000 / UNIDADES_LOCAIS[setor] / 12 * RAZAO_LOJA_PEQUENA, 2) for v in DESPESAS_PAC[setor]]
    return {"total": round(sum(componentes), 2), "componentes": dict(zip(ROTULOS_DESPESAS, componentes)),
            "fonte": FONTE_DESPESAS, "aviso": "Estimativa: média da atividade por loja, na escala da loja pequena (0,4348)."}


def selic_mensal(db=None) -> tuple[float, str]:
    """Última Selic mensal completa (% a.m. → fração)."""
    dados = SELIC_BASE
    if db is not None:
        from .models import SerieOficial
        registro = db.query(SerieOficial).filter_by(chave=CHAVE_SELIC).first()
        if registro and registro.dados:
            dados = registro.dados
    mes = max(dados["serie"])
    return dados["serie"][mes] / 100, mes


def atualizar_selic(db, abrir=urllib.request.urlopen, hoje=None) -> bool:
    from .models import SerieOficial, agora
    registro = db.query(SerieOficial).filter_by(chave=CHAVE_SELIC).first()
    if registro and registro.tentado_em and agora() - registro.tentado_em < timedelta(days=1):
        return False
    if registro is None:
        registro = SerieOficial(chave=CHAVE_SELIC, dados=None)
        db.add(registro)
    registro.tentado_em = agora()
    hoje = hoje or agora().date()
    try:
        url = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.4390/dados/ultimos/13?formato=json"
        with abrir(url, timeout=30) as resposta:
            dados = json.loads(resposta.read().decode("utf-8"))
        corrente = f"{hoje.year}{hoje.month:02d}"
        serie = {f"{d['data'][6:]}{d['data'][3:5]}": float(d["valor"]) for d in dados}
        serie = {p: v for p, v in serie.items() if p < corrente}  # só meses completos
        if not serie:
            raise ValueError("Série da Selic vazia.")
        registro.dados = {"serie": serie, "consultado_em": hoje.isoformat()}
        registro.erro = None
    except Exception as erro:
        registro.erro = str(erro)[:500]
        logging.getLogger(__name__).warning("Selic mensal não atualizada: %s", erro)
        db.commit()
        return False
    db.commit()
    return True


# ---------------------------------------------------------------------------
# Equipe da loja (itens 1 e 2, aprovados em 22/11/2026).
# Item 1: limite de vendas = pessoas × receita por pessoa ocupada, na escala da
# loja pequena; o dono conta como uma pessoa (proporcional à dedicação).
# Produtividade = vendas líquidas ÷ empregados (Levy; Grewal, Retailing
# Management, 2026, p. 455); dono como a organização inteira na loja única
# (p. 466); direção do efeito do pessoal sobre as vendas, côncava, em Perdikaki,
# Kesavan e Swaminathan (2012, M&SOM 14(1):145-162) e Mani, Kesavan e
# Swaminathan (2015, POM 24(2):201-218). A fórmula de Mani et al. ficou como
# pendência do professor (14).
# Dados: PAC 2024, tabela 10645 (receita líquida de revenda e pessoal ocupado
# em 31/12 por atividade) e tabela 10647 (varejo por faixa de pessoal),
# consultadas na API do IBGE em 22/11/2026.
# ---------------------------------------------------------------------------
FONTE_PESSOAL = ("IBGE, PAC 2024, tabela 10645 (receita líquida de revenda ÷ pessoal ocupado em 31/12) "
                 "e tabela 10647 (varejo, faixa até 19 pessoas)")
# setor → (receita líquida de revenda no ano, R$ mil; pessoal ocupado em 31/12)
PESSOAL_PAC = {
    "moveis": (99_045_884, 362_219),
    "bicicletas": (62_158_025, 207_344),
    "vestuario": (126_040_112, 653_824),
    "mochilas": (40_913_827, 190_949),
    "pet": (125_829_641, 454_807),
}
PESSOAL_PAC["colchoes"] = PESSOAL_PAC["moveis"]
# Varejo (tabela 10647): receita operacional líquida (R$ mil) e pessoal ocupado.
VAREJO_TOTAL = (3_196_219_374, 7_647_251)
VAREJO_ATE_19 = (1_255_619_180, 3_991_871)
RAZAO_PRODUTIVIDADE_PEQUENA = round((VAREJO_ATE_19[0] / VAREJO_ATE_19[1])
                                    / (VAREJO_TOTAL[0] / VAREJO_TOTAL[1]), 4)  # 0,7526
AVISO_PESSOAL = ("Estimativa: a razão de produtividade loja pequena/média (0,7526) só é publicada para o varejo total; "
                 "o pessoal ocupado inclui os donos e é contado em 31/12.")

# Item 2: salário de referência = remuneração média por pessoa ocupada nas
# lojas até 19 pessoas (tabela 10647, gastos com salários, retiradas e outras
# remunerações ÷ pessoal ocupado), dividida por 13,333 porque o total anual já
# inclui 13º e 1/3 de férias, que o motor provisiona (tributos.fator_folha).
GASTOS_SALARIOS_ATE_19 = 97_793_101  # R$ mil no ano
SALARIO_REFERENCIA_PAC = round(GASTOS_SALARIOS_ATE_19 * 1000 / VAREJO_ATE_19[1] / (12 + 1 + 1 / 3), 2)
# Piso legal (CF, art. 7º, IV). Decreto nº 12.797, de 23/12/2025, art. 1º.
SALARIO_MINIMO = {2026: 1621.00}
FONTE_SALARIO_MINIMO = "Decreto nº 12.797, de 23/12/2025 (salário mínimo a partir de 1º/1/2026)"


def salario_minimo_vigente(ano: int | None = None) -> float:
    """Salário mínimo nacional do ano (último publicado quando o ano não consta)."""
    if ano in SALARIO_MINIMO:
        return SALARIO_MINIMO[ano]
    return SALARIO_MINIMO[max(SALARIO_MINIMO)]


def receita_por_pessoa(setor: str, series: dict | None = None) -> dict:
    """Receita mensal por pessoa ocupada, na escala da loja pequena, atualizada pela PMC."""
    receita_ano, pessoal = PESSOAL_PAC[setor]
    media = receita_ano * 1000 / pessoal / 12
    series = (series or BASE)["series"]
    fator, periodo = fator_atualizacao(series[str(ATIVIDADE_PMC[setor])])
    return {"valor": round(media * RAZAO_PRODUTIVIDADE_PEQUENA * fator, 2), "media_atividade": round(media, 2),
            "razao_loja_pequena": RAZAO_PRODUTIVIDADE_PEQUENA, "fator_pmc": round(fator, 4), "periodo_pmc": periodo,
            "fonte": FONTE_PESSOAL, "aviso": AVISO_PESSOAL}


# ---------------------------------------------------------------------------
# Canal de venda (opção A, aprovada em 23/11/2026). Canal é o meio de vender e
# entregar (Levy; Grewal, 2026, p. 103); os capítulos 3 e 4 não dão número que
# ligue canal a demanda, por isso não há fator de canal na atratividade. O
# mercado da loja é dividido entre a parte vendida em lojas e a parte vendida
# pela internet segundo a PAC 2023 (tabela 9349, empresas com 20 ou mais
# pessoas ocupadas; demais formas — televendas, porta a porta etc. — ficam
# fora da disputa e as duas partes são renormalizadas). Quem vende pela
# internet usa o marketplace e paga a tarifa do anúncio Clássico do Mercado
# Livre da categoria (o varejista paga parte da receita à plataforma; Levy;
# Grewal, 2026, p. 84).
# ---------------------------------------------------------------------------
FONTE_CANAIS = ("IBGE, PAC 2023, tabela 9349 (receita bruta de revenda por forma de comercialização, "
                "empresas varejistas com 20 ou mais pessoas ocupadas), consultada em 23/11/2026")
# R$ mil em 2023: (lojas, internet)
CANAIS_PAC = {
    "moveis": (27_596_373, 7_228_616),      # 1.5.3 Móveis, iluminação e artigos de uso doméstico
    "vestuario": (74_888_395, 10_618_506),  # 1.3.2 Artigos do vestuário e complementos
    "bicicletas": (22_986_389, 3_788_987),  # 1.5.6 Artigos culturais, recreativos e esportivos
    "pet": (37_159_347, 8_942_249),         # 1.5.8 Outros produtos novos
    "mochilas": (17_627_213, 4_392_832),    # 1.3.3 Calçados, artigos de couro e viagem
}
CANAIS_PAC["colchoes"] = CANAIS_PAC["moveis"]
AVISO_CANAIS = ("A PAC mede as formas de venda só nas empresas com 20 ou mais pessoas; colchões estão em "
                "móveis e pet em outros produtos novos.")
# Mercado Livre, "Tarifas de venda" (busca de categoria), anúncio Clássico,
# consultada em 23/11/2026: https://www.mercadolivre.com.br/landing/custos-de-venda/tarifas-de-venda
FONTE_TARIFA_MARKETPLACE = ("Mercado Livre, Tarifas de venda, anúncio Clássico por categoria, consultada em "
                            "23/11/2026 (https://www.mercadolivre.com.br/landing/custos-de-venda/tarifas-de-venda)")
TARIFA_MARKETPLACE = {"colchoes": .115, "moveis": .115, "vestuario": .14, "bicicletas": .115,
                      "pet": .125, "mochilas": .14}
# Pet: ração e petiscos 14%; coleiras e areia higiênica 12,5% (demais linhas).
TARIFA_MARKETPLACE_LINHA = {("pet", "Alimentação"): .14}


def participacao_canais(setor: str) -> dict:
    """Partes da loja e da internet no mercado do jogo (renormalizadas)."""
    lojas, internet = CANAIS_PAC[setor]
    total = lojas + internet
    return {"loja": lojas / total, "internet": internet / total,
            "internet_pac": round(internet / total, 4), "fonte": FONTE_CANAIS, "aviso": AVISO_CANAIS}


def tarifa_marketplace(produto_id: str) -> float:
    """Tarifa de venda do marketplace (Clássico) para um item do catálogo fixo."""
    from .catalogo_fixo import item as item_catalogo
    ficha = item_catalogo(produto_id)
    if not ficha:
        return 0.0
    return TARIFA_MARKETPLACE_LINHA.get((ficha["setor"], ficha["linha"]), TARIFA_MARKETPLACE.get(ficha["setor"], 0.0))


def custos_da_turma(turma) -> dict | None:
    """Custos fixos, taxa de capital do estoque e parâmetros de pessoal para turmas com catálogo fixo."""
    if getattr(turma, "modo_jogo", None) == "STARTUP":
        return None
    from .routers.mercado import chave_setor
    setor = chave_setor((turma.configuracao_simulacao or {}).get("setor_mercado"))
    if not setor:
        return None
    from .database import SessionLocal
    with SessionLocal() as db:
        taxa, mes = selic_mensal(db)
        series = series_vigentes(db)
    return {"custos_fixos": custos_fixos_loja(setor), "taxa_capital_estoque": taxa,
            "selic_referencia": mes, "fonte_selic": "BCB, SGS 4390 (Selic acumulada no mês)",
            "receita_por_pessoa": receita_por_pessoa(setor, series),
            "salario_referencia": SALARIO_REFERENCIA_PAC, "salario_minimo": salario_minimo_vigente(),
            "fonte_salario_minimo": FONTE_SALARIO_MINIMO, "setor": setor}
