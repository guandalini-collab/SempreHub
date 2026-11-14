"""Relatório gerencial determinístico da rodada.

Gerado no fechamento sem depender de serviço externo: apresenta resultado,
DRE, fluxo de caixa e balanço em seções separadas e, quando um indicador
mostra desempenho fraco, indica a leitura teórica correspondente.

As indicações de leitura vêm de um catálogo fechado: só entram obras e
capítulos conferidos no acervo indicado pelo professor. Uma falha sem obra
conferida não recebe indicação, em vez de uma referência presumida.
"""

from __future__ import annotations

# Catálogo de leituras conferidas (obra e capítulo; edições do acervo
# Minha Biblioteca do IFFar, para que o aluno consiga consultá-las).
LEITURAS = {
    "capacidade": (
        "SLACK, Nigel; BRANDON-JONES, Alistair; BURGESS, Nicola. Administração da produção. "
        "10. ed. São Paulo: Atlas, 2023. Cap. 11 — gestão da capacidade produtiva."
    ),
    "custo_pessoal": (
        "MARTINS, Eliseu. Contabilidade de custos. 12. ed. Barueri: Atlas, 2025. "
        "Cap. 11 — mão de obra direta e encargos."
    ),
    "pro_labore": (
        "DORNELAS, José. Empreendedorismo: transformando ideias em negócios. 9. ed. "
        "São Paulo: Atlas, 2023. Cap. 6 — plano de negócios: sócios, pró-labore e custos fixos."
    ),
}

ROTULOS_DRE = {
    "receita": "Receita",
    "impostos": "Impostos sobre vendas",
    "cmv": "Custo das mercadorias vendidas",
    "folha": "Folha de pagamento",
    "pro_labore": "Pró-labore",
    "encargos_pro_labore": "Encargos sobre pró-labore",
    "horas_extras": "Horas extras",
    "marketing": "Marketing",
    "pd": "P&D",
    "custos_fixos": "Custos fixos",
    "frete": "Frete",
    "armazenagem": "Armazenagem",
    "depreciacao": "Depreciação",
    "juros": "Juros",
}

ROTULOS_BALANCO = {
    "disponibilidades": "Disponibilidades",
    "caixa": "Caixa",
    "estoques": "Estoques",
    "contas_receber": "Contas a receber",
    "imobilizado": "Imobilizado",
    "ativo_total": "Ativo total",
    "cheque_especial": "Cheque especial",
    "emprestimos": "Empréstimos",
    "passivo_total": "Passivo total",
    "patrimonio_liquido": "Patrimônio líquido",
}


def _num(valor):
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def reais(valor) -> str:
    numero = _num(valor)
    if numero is None:
        return "Dados indisponíveis"
    texto = f"{abs(numero):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"-R$ {texto}" if numero < 0 else f"R$ {texto}"


def _secao_dre(dre: dict) -> list[str]:
    linhas = ["DRE da rodada"]
    usadas = set()
    for chave, rotulo in ROTULOS_DRE.items():
        if _num(dre.get(chave)) is not None and (chave == "receita" or _num(dre.get(chave))):
            linhas.append(f"- {rotulo}: {reais(dre[chave])}")
            usadas.add(chave)
    demais = sum(
        _num(v) or 0 for k, v in dre.items()
        if k not in usadas and k not in ("lucro_liquido", "receita") and _num(v) is not None
    )
    if demais:
        linhas.append(f"- Demais despesas: {reais(demais)}")
    linhas.append(f"- Resultado líquido: {reais(dre.get('lucro_liquido'))}")
    return linhas


def _secao_caixa(dfc) -> list[str]:
    linhas = ["Fluxo de caixa"]
    if not isinstance(dfc, dict) or not dfc:
        return linhas + ["- Dados indisponíveis para esta rodada."]
    for chave, rotulo in (("operacional", "Atividades operacionais"), ("investimento", "Investimentos"),
                          ("financiamento", "Financiamentos"), ("variacao", "Variação do caixa"),
                          ("caixa_final", "Caixa final")):
        if _num(dfc.get(chave)) is not None:
            linhas.append(f"- {rotulo}: {reais(dfc[chave])}")
    return linhas


def _secao_balanco(balanco) -> list[str]:
    linhas = ["Balanço patrimonial"]
    if not isinstance(balanco, dict) or not balanco:
        return linhas + ["- Dados indisponíveis para esta rodada."]
    for chave, rotulo in ROTULOS_BALANCO.items():
        if _num(balanco.get(chave)) is not None:
            linhas.append(f"- {rotulo}: {reais(balanco[chave])}")
    if len(linhas) == 1:
        linhas.append("- Dados indisponíveis para esta rodada.")
    return linhas


def leituras_recomendadas(dados: dict) -> list[str]:
    """Leituras indicadas pelos sinais de desempenho fraco da rodada."""
    dre = dados.get("dre") or {}
    operacao = dados.get("operacao") or {}
    alertas = " ".join(str(a) for a in dados.get("alertas") or []).lower()
    demanda = _num(dados.get("demanda")) or 0
    vendas = _num(dados.get("unidades_vendidas")) or 0
    receita = _num(dre.get("receita")) or 0
    pessoal = sum(_num(dre.get(k)) or 0 for k in ("folha", "horas_extras", "pro_labore", "encargos_pro_labore"))
    indicadas = []
    motivos = []
    if demanda > 0 and vendas < demanda:
        indicadas.append("capacidade")
        motivos.append(f"vendas abaixo da demanda ({vendas:.0f} de {demanda:.0f} unidades)")
    if pessoal > 0 and pessoal > receita:
        indicadas.append("custo_pessoal")
        motivos.append("custo de pessoal acima da receita")
    pro_labore = _num(dre.get("pro_labore")) or _num(operacao.get("pro_labore")) or 0
    if "dedica" in alertas or (pro_labore == 0 and "fundador" in alertas):
        indicadas.append("pro_labore")
        motivos.append("dedicação do fundador limitada pelo pró-labore")
    if not indicadas:
        return []
    linhas = ["Leituras recomendadas", f"Pontos de atenção: {'; '.join(motivos)}."]
    linhas += [f"- {LEITURAS[chave]}" for chave in dict.fromkeys(indicadas)]
    return linhas


def montar_relatorio(dados: dict) -> str:
    dre = dados.get("dre") or {}
    partes = [
        [f"Relatório gerencial — rodada {dados.get('rodada')}",
         f"Demanda: {_num(dados.get('demanda')) or 0:.0f} unidades · Vendas: "
         f"{_num(dados.get('unidades_vendidas')) or 0:.0f} unidades · Preço: {reais(dados.get('preco'))}"],
        _secao_dre(dre),
        _secao_caixa(dados.get("dfc")),
        _secao_balanco(dados.get("balanco") or dados.get("balanco_basico")),
    ]
    alertas = [str(a) for a in dados.get("alertas") or []]
    if alertas:
        partes.append(["Alertas registrados no fechamento"] + [f"- {a}" for a in alertas[:12]])
    leituras = leituras_recomendadas(dados)
    if leituras:
        partes.append(leituras)
    return "\n\n".join("\n".join(p) for p in partes)
