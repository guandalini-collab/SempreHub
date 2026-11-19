"""Indicadores oficiais: BCB (SGS e Focus), IBGE (SIDRA: IPCA, PMC, PIM) e Comex Stat (MDIC)."""
from __future__ import annotations

import unicodedata
from datetime import date, datetime

from . import catalogo
from .rede import enviar_json, obter_json, url

SGS_BASE = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados"
SIDRA_BASE = "https://servicodados.ibge.gov.br/api/v3/agregados"
COMEX_BASE = "https://api-comexstat.mdic.gov.br"


def _hoje() -> str:
    return date.today().isoformat()


def _sem_acento(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", t.lower()) if unicodedata.category(c) != "Mn")


def _registro(fonte, serie, codigo, periodo, valor, unidade, endereco, situacao, extra=None):
    r = {"tipo": "dado_oficial", "fonte": fonte, "serie": serie, "codigo": str(codigo),
         "periodo_referencia": periodo, "valor": valor, "unidade": unidade,
         "consultado_em": _hoje(), "link": endereco, "situacao_codigo": situacao}
    if extra:
        r.update(extra)
    return r


# ---------------------------------------------------------------- BCB / SGS
def sgs(codigo: int, ultimos: int = 1, obter=obter_json) -> list[dict]:
    nome, period, situacao, _ = catalogo.SGS.get(codigo, (f"Série SGS {codigo}", "?", "nao_catalogado", ""))
    endereco = url(SGS_BASE.format(codigo=codigo) + f"/ultimos/{ultimos}", {"formato": "json"})
    dados = obter(endereco)
    saida = []
    for d in dados:
        ref = datetime.strptime(d["data"], "%d/%m/%Y").date()
        periodo = ref.strftime("%m/%Y") if period == "mensal" else ref.isoformat()
        saida.append(_registro("Banco Central do Brasil (SGS)", nome, codigo, periodo,
                               float(str(d["valor"]).replace(",", ".")), "", endereco, situacao))
    return saida


# ---------------------------------------------------------------- BCB / Focus
def focus(indicador: str, ano: int | None = None, obter=obter_json) -> list[dict]:
    """Mediana mais recente do Focus para o indicador e o ano de referência."""
    ano = ano or date.today().year
    base = catalogo.FOCUS["base"] + catalogo.FOCUS["anuais"]
    filtro = f"Indicador eq '{indicador}' and DataReferencia eq '{ano}'"
    endereco = url(base, {"$filter": filtro, "$orderby": "Data desc", "$top": "5",
                          "$format": "json", "$select": "Indicador,Data,DataReferencia,Mediana,baseCalculo"})
    linhas = obter(endereco).get("value", [])
    # baseCalculo 0 = todas as respostas dos últimos 30 dias (conferir na documentação do BCB).
    linhas = [l for l in linhas if l.get("baseCalculo") in (0, None)] or linhas
    if not linhas:
        return []
    l = linhas[0]
    return [_registro("Banco Central do Brasil (Boletim Focus)", f"Mediana da expectativa de {indicador} para {ano}",
                      indicador, f"pesquisa de {l['Data']}", l["Mediana"], "", endereco,
                      catalogo.FOCUS["situacao"])]


# ---------------------------------------------------------------- IBGE / SIDRA
def sidra_metadados(tabela: int, obter=obter_json) -> dict:
    return obter(f"{SIDRA_BASE}/{tabela}/metadados")


def sidra_resolver(tabela: int, termos: list[str], obter=obter_json) -> list[dict]:
    """Categorias cujo nome contém algum dos termos, em qualquer classificação da tabela."""
    meta = sidra_metadados(tabela, obter)
    achados = []
    for cl in meta.get("classificacoes", []):
        for cat in cl.get("categorias", []):
            nome = _sem_acento(cat["nome"])
            if any(_sem_acento(t) in nome for t in termos):
                achados.append({"classificacao": cl["id"], "categoria": cat["id"], "nome": cat["nome"]})
    return achados


def sidra_variavel(tabela: int, termo: str, obter=obter_json) -> dict | None:
    for v in sidra_metadados(tabela, obter).get("variaveis", []):
        if _sem_acento(termo) in _sem_acento(v["nome"]):
            return {"id": v["id"], "nome": v["nome"], "unidade": v.get("unidade", "")}
    return None


def sidra(tabela: int, variavel: int, classificacao: str = "", periodos: str = "-1",
          obter=obter_json, rotulo: str = "", situacao: str = "conferido") -> list[dict]:
    """Consulta a API de agregados v3 (Brasil, N1). ``periodos='-1'`` = último período."""
    endereco = f"{SIDRA_BASE}/{tabela}/periodos/{periodos}/variaveis/{variavel}"
    endereco = url(endereco, {"localidades": "N1[all]", **({"classificacao": classificacao} if classificacao else {})})
    saida = []
    for var in obter(endereco):
        for res in var["resultados"]:
            cats = "; ".join(f"{list(c['categoria'].values())[0]}" for c in res.get("classificacoes", []))
            for s in res["series"]:
                for per, val in s["serie"].items():
                    if val in ("-", "...", "X", "", None):
                        continue
                    saida.append(_registro(f"IBGE (SIDRA, tabela {tabela})",
                                           rotulo or f"{var['variavel']}" + (f" — {cats}" if cats else ""),
                                           f"{tabela}/{variavel}", per, float(val), var.get("unidade", ""),
                                           endereco, situacao))
    return saida


def ipca(obter=obter_json) -> list[dict]:
    c = catalogo.IPCA
    saida = sidra(c["tabela"], c["variavel_mensal"], f"{c['classificacao']}[7169]", obter=obter,
                  rotulo="IPCA - variação mensal (índice geral)")
    v12 = sidra_variavel(c["tabela"], "acumulada em 12 meses", obter)
    if v12:
        saida += sidra(c["tabela"], v12["id"], f"{c['classificacao']}[7169]", obter=obter,
                       rotulo=f"IPCA - {v12['nome']} (índice geral)", situacao="resolvido_por_nome")
    return saida


def pmc(setor: str, obter=obter_json) -> list[dict]:
    from_atividade = {"vestuario": 90673, "mochilas": 90673, "colchoes": 31555, "moveis": 31555,
                      "bicicletas": 103158, "pet": 103158}
    ativ = from_atividade[setor]
    saida = []
    for nome, c in (("volume", catalogo.PMC["volume"]), ("receita nominal", catalogo.PMC["receita_nominal"])):
        saida += sidra(c["tabela"], c["variavel"], f"11046[{c['tipo_indice']}]|85[{ativ}]", periodos="-13",
                       obter=obter, rotulo=f"PMC — índice de {nome} — {catalogo.PMC['atividades'][ativ]}")
    return saida


def pim(setor: str, obter=obter_json) -> list[dict]:
    termos = catalogo.PIM["atividades_por_nome"].get(setor)
    if not termos:
        return []
    tabela = catalogo.PIM["tabela"]
    var = sidra_variavel(tabela, "número-índice", obter) or sidra_variavel(tabela, "indice", obter)
    if not var:
        raise RuntimeError(f"Variável de número-índice não encontrada na tabela {tabela}")
    saida = []
    for cat in sidra_resolver(tabela, termos, obter):
        saida += sidra(tabela, var["id"], f"{cat['classificacao']}[{cat['categoria']}]", periodos="-13",
                       obter=obter, rotulo=f"PIM-PF — {var['nome']} — {cat['nome']}", situacao="resolvido_por_nome")
    return saida


# ---------------------------------------------------------------- Comex Stat
def _campo(linha: dict, *nomes):
    baixa = {k.lower(): v for k, v in linha.items()}
    for n in nomes:
        if n.lower() in baixa:
            return baixa[n.lower()]
    return None


def comex(setor: str, fluxo: str = "import", de: str | None = None, ate: str | None = None,
          enviar=enviar_json) -> list[dict]:
    """Valor FOB (US$) e peso (kg) por mês, para os códigos do setor."""
    hoje = date.today()
    de = de or f"{hoje.year - 1}-{hoje.month:02d}"
    ate = ate or f"{hoje.year}-{hoje.month:02d}"
    cfg = catalogo.COMEX[setor]
    saida = []
    for nivel in ("chapter", "position", "subposition", "ncm"):
        if not cfg.get(nivel):
            continue
        corpo = {"flow": fluxo, "monthDetail": True, "period": {"from": de, "to": ate},
                 "filters": [{"filter": nivel, "values": cfg[nivel]}], "details": [nivel],
                 "metrics": ["metricFOB", "metricKG"]}
        endereco = f"{COMEX_BASE}/general?language=pt"
        resp = enviar(endereco, corpo)
        for l in (resp.get("data") or {}).get("list", []):
            # Os nomes dos campos da resposta não constam da documentação lida; a linha
            # original segue junto para conferência no primeiro uso.
            ano = _campo(l, "year", "ano", "coAno")
            mes = _campo(l, "monthNumber", "month", "mes", "coMes")
            periodo = f"{ano}-{int(mes):02d}" if mes not in (None, "") and str(mes).isdigit() else str(ano)
            cod = _campo(l, "coNcm", "ncm", "coSh6", "subposition", "coSh4", "position", "heading",
                         "coSh2", "chapter") or nivel
            saida.append(_registro("MDIC (Comex Stat)", f"{'Importação' if fluxo == 'import' else 'Exportação'} — {cfg['nota']}",
                                   cod, periodo, float(_campo(l, "metricFOB", "vlFob") or 0), "US$ FOB", endereco,
                                   cfg["situacao"], {"kg": float(_campo(l, "metricKG", "kgLiquido") or 0),
                                                     "consulta": corpo, "linha_original": l}))
    return saida


# ---------------------------------------------------------------- conjuntos
MACRO_SGS = (432, 4390, 1, 20740, 20750, 29037)


def macro(obter=obter_json) -> list[dict]:
    saida = []
    for codigo in MACRO_SGS:
        saida += _seguro(lambda c=codigo: sgs(c, obter=obter), f"SGS {codigo}")
    saida += _seguro(lambda: ipca(obter), "IPCA (SIDRA 7060)")
    for ind in catalogo.FOCUS["indicadores"]:
        saida += _seguro(lambda i=ind: focus(i, obter=obter), f"Focus {ind}")
    return saida


def setor(nome: str, obter=obter_json, enviar=enviar_json) -> list[dict]:
    saida = _seguro(lambda: pmc(nome, obter), f"PMC {nome}")
    saida += _seguro(lambda: pim(nome, obter), f"PIM {nome}")
    saida += _seguro(lambda: comex(nome, enviar=enviar), f"Comex {nome}")
    return saida


def _seguro(funcao, rotulo):
    """Uma fonte fora do ar não derruba as demais; a falha fica registrada na saída."""
    try:
        return funcao()
    except Exception as e:  # noqa: BLE001 — registrar e seguir
        return [{"tipo": "falha", "fonte": rotulo, "erro": str(e)[:300], "consultado_em": _hoje()}]
