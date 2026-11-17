"""Correção dos preços do catálogo fixo pelo IPCA (Grupo 2, item 1).

Aprovado em 16/11/2026: o preço conferido na coleta é corrigido pela variação
mensal do IPCA (IBGE, tabela 7060, variável 63) do subitem do produto. Regra de
associação aprovada: subitem quando o nome corresponde claramente ao produto;
item (nível acima) quando o produto pertence com certeza ao grupo; IPCA geral
quando não há item que o contenha com segurança.

A correção acumula os meses posteriores ao mês da coleta até o último mês
publicado. A série fica gravada em ``series_oficiais`` e é consultada uma vez
por dia; se a consulta falhar, vale a última gravação (ou nenhuma correção).
"""
from __future__ import annotations

import json
import logging
import urllib.request
from datetime import timedelta

TABELA, VARIAVEL, CLASSIFICACAO = 7060, 63, 315
CHAVE = "ipca_catalogo"
FONTE = "IBGE, IPCA, tabela 7060 (variação mensal por subitem)"

GERAL = (7169, "Índice geral", "geral")
I = {  # código da categoria 315 → (nome oficial, nível)
    7493: ("3101017.Colchão", "subitem"),
    7488: ("3101.Mobiliário", "item"),
    7517: ("3103.Cama, mesa e banho", "item"),
    7489: ("3101002.Móvel para sala", "subitem"),
    7490: ("3101003.Móvel para quarto", "subitem"),
    7492: ("3101015.Móvel para copa e cozinha", "subitem"),
    107649: ("4101009.Camisa/camiseta masculina", "subitem"),
    107650: ("4103011.Camisa/camiseta infantil", "subitem"),
    7572: ("4102.Roupa feminina", "item"),
    7561: ("4101002.Calça comprida masculina", "subitem"),
    7573: ("4102002.Calça comprida feminina", "subitem"),
    47644: ("4101006.Bermuda/short masculino", "subitem"),
    7575: ("4102004.Saia", "subitem"),
    7563: ("4101005.Agasalho masculino", "subitem"),
    7560: ("4101.Roupa masculina", "item"),
    7559: ("41.Roupas", "subgrupo"),
    7736: ("7201019.Bicicleta", "subitem"),
    107666: ("7201020.Alimento para animais", "subitem"),
    47661: ("7201256.Serviço de higiene para animais", "subitem"),
    47647: ("4201040.Mochila", "subitem"),
    107652: ("4201015.Bolsa", "subitem"),
    7605: ("4201.Calçados e acessórios", "item"),
}

# (setor, trecho do nome do produto) → código; a primeira regra que casar vale.
REGRAS = (
    ("colchoes", "Colchão", 7493),
    ("colchoes", "Base box", 7488), ("colchoes", "Box baú", 7488),
    ("colchoes", "Travesseiro", 7517), ("colchoes", "Protetor", 7517),
    ("moveis", "Sofá", 7489), ("moveis", "Rack", 7489), ("moveis", "Painel", 7489), ("moveis", "Mesa de centro", 7489),
    ("moveis", "Guarda-roupa", 7490), ("moveis", "Cômoda", 7490), ("moveis", "Cabeceira", 7490), ("moveis", "Cama", 7490),
    ("moveis", "Cozinha compacta", 7492), ("moveis", "Armário aéreo", 7492),
    ("moveis", "Mesa de jantar", 7488), ("moveis", "Cadeira", 7488), ("moveis", "Escrivaninha", 7488), ("moveis", "Mesa em L", 7488),
    ("vestuario", "Camiseta básica masculina", 107649), ("vestuario", "Regata", 107649),
    ("vestuario", "Camiseta infantil", 107650), ("vestuario", "Camiseta básica feminina", 7572),
    ("vestuario", "Calça jeans masculina", 7561), ("vestuario", "Calça jeans feminina", 7573),
    ("vestuario", "Bermuda", 47644), ("vestuario", "Saia", 7575), ("vestuario", "Casaco masculino", 7563),
    ("vestuario", "Calça térmica", 7560), ("vestuario", "Moletom", 7559), ("vestuario", "Jaqueta jeans", 7559),
    ("bicicletas", "Bicicleta", 7736), ("bicicletas", "Mountain bike", 7736), ("bicicletas", "Speed", 7736),
    ("pet", "Ração", 107666), ("pet", "Petisco", 107666),
    ("mochilas", "Mochila", 47647), ("mochilas", "Bolsa", 107652), ("mochilas", "Clutch", 107652),
    ("mochilas", "Pochete", 7605), ("mochilas", "Carteira", 7605),
)
SERVICOS = {"banho_e_tosa": 47661}


def indice_do_produto(setor: str, nome: str) -> tuple[int, str, str]:
    for s, trecho, codigo in REGRAS:
        if s == setor and nome.startswith(trecho):
            return (codigo, *I[codigo])
    return GERAL


def _mes_seguinte(periodo: str) -> str:
    ano, mes = int(periodo[:4]), int(periodo[4:])
    return f"{ano + (mes == 12)}{1 if mes == 12 else mes + 1:02d}"


def fator(variacoes: dict[str, float] | None, data_coleta: str) -> tuple[float, str | None, str | None]:
    """Fator acumulado dos meses posteriores ao da coleta; (1, None, None) sem dados."""
    if not variacoes:
        return 1.0, None, None
    inicio = _mes_seguinte(data_coleta[:4] + data_coleta[5:7])
    meses = sorted(p for p in variacoes if p >= inicio)
    valor = 1.0
    for p in meses:
        valor *= 1 + float(variacoes[p]) / 100
    return valor, (meses[0] if meses else None), (meses[-1] if meses else None)


def consultar(inicio: str, abrir=urllib.request.urlopen) -> dict[str, dict[str, float]]:
    codigos = ",".join(str(c) for c in [GERAL[0], *I])
    url = (f"https://servicodados.ibge.gov.br/api/v3/agregados/{TABELA}/periodos/{inicio}-209912"
           f"/variaveis/{VARIAVEL}?localidades=N1[all]&classificacao={CLASSIFICACAO}[{codigos}]")
    with abrir(url, timeout=30) as resposta:
        dados = json.loads(resposta.read().decode("utf-8"))
    series = {}
    for resultado in dados[0]["resultados"]:
        codigo = next(iter(resultado["classificacoes"][0]["categoria"]))
        serie = resultado["series"][0]["serie"]
        series[codigo] = {p: float(v) for p, v in serie.items() if v not in ("-", "...", "X", "")}
    return series


def series_vigentes(db) -> dict:
    from .models import SerieOficial
    registro = db.query(SerieOficial).filter_by(chave=CHAVE).first() if db is not None else None
    return dict(registro.dados) if registro and registro.dados else {}


def atualizar(db, abrir=urllib.request.urlopen) -> bool:
    from .catalogo_fixo import ITENS
    from .models import SerieOficial, agora
    registro = db.query(SerieOficial).filter_by(chave=CHAVE).first()
    if registro and registro.tentado_em and agora() - registro.tentado_em < timedelta(days=1):
        return False
    if registro is None:
        registro = SerieOficial(chave=CHAVE, dados=None)
        db.add(registro)
    registro.tentado_em = agora()
    inicio = min(_mes_seguinte(i["data_coleta"][:4] + i["data_coleta"][5:7]) for i in ITENS)
    try:
        registro.dados = {"series": consultar(inicio, abrir), "fonte": FONTE, "consultado_em": agora().date().isoformat()}
        registro.erro = None
    except Exception as erro:  # mês ainda não publicado ou falha de rede
        registro.erro = str(erro)[:500]
        logging.getLogger(__name__).warning("IPCA do catálogo não atualizado: %s", erro)
        db.commit()
        return False
    db.commit()
    return True


def ciclo() -> None:
    from .database import SessionLocal
    with SessionLocal() as db:
        atualizar(db)


def preco_corrigido(item: dict, db=None, series: dict | None = None) -> dict:
    codigo, nome, nivel = indice_do_produto(item["setor"], item["nome"])
    series = series if series is not None else series_vigentes(db).get("series", {})
    valor, de, ate = fator(series.get(str(codigo)), item["data_coleta"])
    return {
        "preco": round(item["preco_mediana"] * valor, 2), "fator": round(valor, 6),
        "indice": f"{nome} ({nivel})" if nivel != "geral" else "Índice geral (IPCA)",
        "codigo_ipca": codigo, "periodo": f"{de} a {ate}" if de else None,
    }
