"""Custo de compra da loja a partir do preço de varejo (Grupo 2, item 2).

Aprovado em 16/11/2026:
    custo = preço de varejo × (1 − alíquota efetiva do Simples) ÷ (1 + taxa de margem da PAC)

- Taxa de margem: PAC 2024, tabela 10645 (IBGE), definida como margem de
  comercialização ÷ CMV; a receita líquida de revenda da PAC já desconta os
  impostos sobre vendas, inclusive o Simples Nacional (Notas técnicas da PAC).
- Alíquota efetiva: LC 123/2006, Anexo I (comércio), redação da LC 155/2016:
  (RBT12 × alíquota nominal − parcela a deduzir) ÷ RBT12 (art. 18, § 1º-A).
  No início de atividade, a RBT12 é a receita acumulada proporcionalizada a
  12 meses (art. 18, § 2º); sem receita, vale a primeira faixa (4%).
"""

from __future__ import annotations

from .catalogo_fixo import ATIVIDADE_PAC

# (limite superior da RBT12, alíquota nominal, parcela a deduzir)
ANEXO_I = (
    (180_000.00, 0.040, 0.0),
    (360_000.00, 0.073, 5_940.00),
    (720_000.00, 0.095, 13_860.00),
    (1_800_000.00, 0.107, 22_500.00),
    (3_600_000.00, 0.143, 87_300.00),
    (4_800_000.00, 0.190, 378_000.00),
)
FONTE_SIMPLES = "LC 123/2006, Anexo I (redação da LC 155/2016), art. 18, §§ 1º-A e 2º"
FONTE_PAC = "IBGE, PAC 2024, tabela 10645 (taxa de margem = margem ÷ CMV)"


def rbt12(receitas_mensais: list[float]) -> float:
    """Receita bruta dos últimos 12 meses; proporcionalizada no início de atividade."""
    ultimas = [max(0.0, float(r or 0)) for r in receitas_mensais][-12:]
    if not ultimas or sum(ultimas) == 0:
        return 0.0
    if len(ultimas) < 12:
        return sum(ultimas) / len(ultimas) * 12
    return sum(ultimas)


def aliquota_efetiva(receita_12m: float) -> float:
    if receita_12m <= 0:
        return ANEXO_I[0][1]
    for limite, nominal, deduzir in ANEXO_I:
        if receita_12m <= limite:
            return (receita_12m * nominal - deduzir) / receita_12m
    limite, nominal, deduzir = ANEXO_I[-1]
    return (limite * nominal - deduzir) / limite  # acima do teto: fora do Simples; mantém a última faixa


def custo_compra(preco_varejo: float, setor: str, receitas_mensais: list[float] | None = None) -> dict:
    codigo, atividade, margem, cv = ATIVIDADE_PAC[setor]
    efetiva = aliquota_efetiva(rbt12(receitas_mensais or []))
    custo = preco_varejo * (1 - efetiva) / (1 + margem)
    return {
        "custo_unitario": round(custo, 2),
        "aliquota_efetiva_simples": round(efetiva, 6),
        "taxa_margem_pac": margem,
        "atividade_pac": f"{codigo} – {atividade}",
        "cv_pac": cv,
        "formula": "preço de varejo × (1 − alíquota efetiva do Simples) ÷ (1 + taxa de margem da PAC)",
        "fontes": [FONTE_PAC, FONTE_SIMPLES],
        "aviso": ("Menor precisão: coeficiente de variação da PAC acima de 10%." if cv > 10 else None),
    }
