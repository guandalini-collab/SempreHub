"""Sazonalidade mensal das vendas a partir da Pesquisa Mensal de Comércio (IBGE).

Fonte: IBGE, PMC, tabela 8882 (volume de vendas do varejo por atividades,
2022 = 100), variável 7169 (número-índice sem ajuste sazonal), Brasil.

Método (estimativa técnica, não é o ajuste X-12 ARIMA do IBGE): para cada ano
completo, índice do mês ÷ média do ano; o fator do mês é a média dos quatro
últimos anos completos. Fator 1,00 = mês médio.

Associação aos setores (Notas Metodológicas da PMC, Quadro I, conferidas em
16/11/2026):
- Colchões e Móveis → "Móveis" (CNAE 4754-7 inclui 4754-7/02, colchoaria).
- Vestuário e Mochilas/Malas/Bolsas → "Tecidos, vestuário e calçados"
  (4781-4 e 4782-2, que inclui 4782-2/02, artigos de viagem).
- Bicicletas e Pet Shop → "Outros artigos de uso pessoal e doméstico"
  (4763-6/03, bicicletas; 4789-0/04, artigos e alimentos para animais).
"""
from __future__ import annotations

import json
import logging
import unicodedata
import urllib.request
from datetime import datetime, timedelta
from statistics import mean

FONTE = "IBGE, Pesquisa Mensal de Comércio, tabela 8882 (volume de vendas, sem ajuste sazonal)"
ESTADO = "Estimativa técnica calculada a partir do IBGE/PMC"
TABELA, VARIAVEL = 8882, 7169
ATIVIDADES = {
    "MOVEIS": {"codigo": 31555, "nome": "Móveis"},
    "VESTUARIO": {"codigo": 90673, "nome": "Tecidos, vestuário e calçados"},
    "OUTROS": {"codigo": 103158, "nome": "Outros artigos de uso pessoal e doméstico"},
}
# Edição de base, consultada na API do IBGE em 15/11/2026 (anos 2022–2025).
BASE = {
    "periodo": "2022–2025",
    "consultado_em": "2026-11-15",
    "fonte": FONTE,
    "series": {
        "MOVEIS": [0.987, 0.897, 0.966, 0.934, 1.039, 0.948, 1.022, 0.956, 0.920, 0.946, 1.190, 1.194],
        "VESTUARIO": [0.812, 0.756, 0.848, 0.913, 1.101, 1.067, 0.996, 0.963, 0.856, 0.910, 1.048, 1.730],
        "OUTROS": [0.977, 0.848, 0.960, 0.927, 0.993, 0.922, 0.991, 0.948, 0.906, 1.002, 1.251, 1.276],
    },
}
CHAVE_EDICAO = "sazonalidade_pmc"
_PALAVRAS = (
    ("MOVEIS", ("colch", "dormit", "move")),
    ("VESTUARIO", ("vestu", "moda", "mochil", "mala", "bolsa")),
    ("OUTROS", ("bicic", "mobilidade", "pet")),
)


def _sem_acento(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn")


def atividade_do_setor(setor: str | None) -> str | None:
    """Atividade da PMC associada ao setor; None quando não há série associada."""
    if not setor:
        return None
    texto = _sem_acento(setor)
    for atividade, palavras in _PALAVRAS:
        if any(p in texto for p in palavras):
            return atividade
    return None


def fator(edicao: dict | None, setor: str | None, mes: int, ano: int | None = None) -> dict:
    """Fator do mês (1–12) para o setor, com a origem explícita."""
    if edicao is None:
        from .sazonalidade_x13 import edicao_base
        edicao = edicao_base()
    if edicao.get("metodo") == "X13":
        return _fator_x13(edicao, setor, mes, ano)
    atividade = atividade_do_setor(setor)
    if atividade is None or atividade not in edicao.get("series", {}):
        return {
            "fator": 1.0, "atividade": None,
            "observacao": "Setor sem série do IBGE associada; nenhuma sazonalidade foi aplicada à procura.",
        }
    return {
        "fator": float(edicao["series"][atividade][mes - 1]),
        "atividade": ATIVIDADES[atividade]["nome"],
        "periodo": edicao.get("periodo"),
        "observacao": f"Média de {edicao.get('periodo')} do índice sem ajuste sazonal (mês ÷ média do ano).",
    }


def _fator_x13(edicao: dict, setor: str | None, mes: int, ano: int | None) -> dict:
    """Fator previsto pela replicação do X-13 para o mês; fora do horizonte,
    vale o mesmo mês do último ano previsto (com aviso)."""
    atividade = atividade_do_setor(setor)
    serie = (edicao.get("previsto") or {}).get(atividade or "")
    if not serie:
        return {"fator": 1.0, "atividade": None,
                "observacao": "Setor sem série do IBGE associada; nenhuma sazonalidade foi aplicada à procura."}
    detalhes = (edicao.get("detalhes") or {}).get(atividade, {})
    chave = f"{ano}{mes:02d}" if ano else None
    if chave in serie:
        valor, nota = serie[chave], ""
    else:
        mesmo_mes = sorted(p for p in serie if p.endswith(f"{mes:02d}"))
        valor = serie[mesmo_mes[-1]]
        nota = f" Mês fora do horizonte previsto: usado o fator de {mesmo_mes[-1][4:]}/{mesmo_mes[-1][:4]}."
    conversao = f" Ajuste aditivo convertido em percentual: {detalhes['conversao']}." if detalhes.get("ajuste") == "aditivo" else ""
    return {"fator": float(valor), "atividade": detalhes.get("atividade"), "periodo": f"série até {edicao.get('dados_ate')}",
            "observacao": f"Fator sazonal e de calendário previsto pela replicação do X-13 (modelo ARIMA {detalhes.get('arima')}).{conversao}{nota}"}


def calcular(valores: dict[str, float]) -> list[float]:
    """Calcula os 12 fatores a partir de {"AAAAMM": índice}; exige anos completos."""
    anos: dict[int, dict[int, float]] = {}
    for periodo, valor in valores.items():
        anos.setdefault(int(periodo[:4]), {})[int(periodo[4:])] = float(valor)
    completos = sorted(a for a, meses in anos.items() if len(meses) == 12)
    if len(completos) < 4:
        raise ValueError("A série do IBGE não tem quatro anos completos.")
    usados = completos[-4:]
    razoes = {m: [] for m in range(1, 13)}
    for ano in usados:
        media_ano = mean(anos[ano].values())
        for mes in range(1, 13):
            razoes[mes].append(anos[ano][mes] / media_ano)
    return [round(mean(razoes[m]), 3) for m in range(1, 13)]


def consultar_ibge(ano_final: int, abrir=urllib.request.urlopen) -> dict:
    """Consulta a API de agregados do IBGE para os quatro anos até ``ano_final``."""
    codigos = ",".join(str(a["codigo"]) for a in ATIVIDADES.values())
    url = (
        f"https://servicodados.ibge.gov.br/api/v3/agregados/{TABELA}/periodos/{ano_final - 3}01-{ano_final}12"
        f"/variaveis/{VARIAVEL}?localidades=N1[all]&classificacao=11046[56734]|85[{codigos}]"
    )
    with abrir(url, timeout=30) as resposta:
        dados = json.loads(resposta.read().decode("utf-8"))
    por_codigo = {}
    for resultado in dados[0]["resultados"]:
        categorias = {}
        for classificacao in resultado["classificacoes"]:
            if classificacao["id"] == "85":
                categorias = classificacao["categoria"]
        codigo = int(next(iter(categorias)))
        serie = resultado["series"][0]["serie"]
        por_codigo[codigo] = {p: v for p, v in serie.items() if v not in ("-", "...", "X", "")}
    series = {chave: calcular(por_codigo[a["codigo"]]) for chave, a in ATIVIDADES.items()}
    return {
        "periodo": f"{ano_final - 3}–{ano_final}",
        "consultado_em": datetime.now().date().isoformat(),
        "fonte": FONTE,
        "series": series,
    }


def edicao_vigente(db) -> dict:
    """Última edição gravada; sem gravação, a edição de base."""
    from ..models import SerieOficial
    registro = db.query(SerieOficial).filter_by(chave=CHAVE_EDICAO).first()
    return dict(registro.dados) if registro and registro.dados else dict(BASE)


def atualizar(db, hoje=None, abrir=urllib.request.urlopen) -> bool:
    """Atualização anual: quando há um ano completo novo, recalcula pela API.

    Uma falha mantém a edição anterior e só tenta de novo no dia seguinte.
    Turmas em andamento não mudam: o calendário guarda a edição do início.
    """
    from ..models import SerieOficial, agora
    hoje = hoje or datetime.now().date()
    ano_final = hoje.year - 1
    registro = db.query(SerieOficial).filter_by(chave=CHAVE_EDICAO).first()
    atual = registro.dados if registro and registro.dados else BASE
    if str(atual.get("periodo", "")).endswith(str(ano_final)):
        return False
    if registro and registro.tentado_em and agora() - registro.tentado_em < timedelta(days=1):
        return False
    if registro is None:
        registro = SerieOficial(chave=CHAVE_EDICAO, dados=None)
        db.add(registro)
    registro.tentado_em = agora()
    try:
        registro.dados = consultar_ibge(ano_final, abrir)
        registro.erro = None
    except Exception as erro:  # a fonte pode ainda não ter publicado dezembro
        registro.erro = str(erro)[:500]
        logging.getLogger(__name__).warning("Sazonalidade do IBGE não atualizada: %s", erro)
        db.commit()
        return False
    db.commit()
    return True


def ciclo() -> None:
    """Chamado pelo laço de fontes oficiais; consulta o IBGE só quando há ano novo."""
    from ..database import SessionLocal
    with SessionLocal() as db:
        atualizar(db)
