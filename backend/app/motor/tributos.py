"""Regras tributárias simplificadas para fins didáticos.

Simplificações assumidas (documentadas no README):
- Simples Nacional: Anexo I (comércio), com alíquota efetiva calculada pela
  fórmula da LC 123/2006 (redação da LC 155/2016):
      alíquota efetiva = (RBT12 × alíquota nominal − parcela a deduzir) / RBT12
  Para empresas com menos de 12 meses, a RBT12 é a média mensal × 12.
- Lucro Presumido (comércio): IRPJ 15% sobre presunção de 8%, CSLL 9% sobre
  presunção de 12%, PIS 0,65% e COFINS 3% sobre a receita (total 5,93%), mais
  ICMS sobre o valor agregado (receita − CMV). O adicional de IRPJ é ignorado.
- MEI: DAS mensal fixo. Teto anual com tolerância de 20%.
- Não estão modelados os efeitos da transição da reforma tributária (CBS/IBS).
"""

from typing import List, Tuple

from ..models import RegimeTributario

# (limite superior da faixa de RBT12, alíquota nominal, parcela a deduzir)
FAIXAS_SIMPLES_ANEXO_I: List[Tuple[float, float, float]] = [
    (180_000.00, 0.040, 0.00),
    (360_000.00, 0.073, 5_940.00),
    (720_000.00, 0.095, 13_860.00),
    (1_800_000.00, 0.107, 22_500.00),
    (3_600_000.00, 0.143, 87_300.00),
    (4_800_000.00, 0.190, 378_000.00),
]

ALIQUOTA_FEDERAL_LUCRO_PRESUMIDO = 0.15 * 0.08 + 0.09 * 0.12 + 0.0065 + 0.03  # 5,93%

# Multiplicador sobre o salário-base que representa encargos trabalhistas (CLT).
# No Simples Nacional (Anexo I) a contribuição patronal está dentro do DAS, por isso o fator é menor.
FATOR_CLT = {
    RegimeTributario.MEI: 1.45,
    RegimeTributario.SIMPLES_NACIONAL: 1.45,
    RegimeTributario.LUCRO_PRESUMIDO: 1.82,
}

MAX_FUNCIONARIOS_MEI = 1
TOLERANCIA_TETO_MEI = 0.20


def aliquota_efetiva_simples(rbt12: float) -> float:
    if rbt12 <= 0:
        return FAIXAS_SIMPLES_ANEXO_I[0][1]
    for limite, nominal, deduzir in FAIXAS_SIMPLES_ANEXO_I:
        if rbt12 <= limite:
            return max(0.0, (rbt12 * nominal - deduzir) / rbt12)
    # Acima do teto do Simples: aplica a última faixa (o jogo sinaliza o excesso em alerta)
    _, nominal, deduzir = FAIXAS_SIMPLES_ANEXO_I[-1]
    return (rbt12 * nominal - deduzir) / rbt12


def rbt12(receitas_anteriores: List[float]) -> float:
    """Receita bruta acumulada dos 12 meses anteriores (proporcionalizada no início de atividade)."""
    ultimos = receitas_anteriores[-12:]
    if not ultimos:
        return 0.0
    if len(ultimos) < 12:
        return sum(ultimos) / len(ultimos) * 12
    return sum(ultimos)


def calcular_imposto(
    regime: RegimeTributario,
    receita: float,
    cmv: float,
    receitas_anteriores: List[float],
    das_mei: float,
    aliquota_icms: float,
) -> Tuple[float, float]:
    """Retorna (imposto da rodada, alíquota efetiva sobre a receita)."""
    if regime == RegimeTributario.MEI:
        return das_mei, (das_mei / receita if receita > 0 else 0.0)

    if regime == RegimeTributario.SIMPLES_NACIONAL:
        # Na primeira receita, a própria receita do mês é a base de cálculo da média
        base = rbt12(receitas_anteriores) if receitas_anteriores else receita * 12
        aliquota = aliquota_efetiva_simples(base)
        return receita * aliquota, aliquota

    federal = receita * ALIQUOTA_FEDERAL_LUCRO_PRESUMIDO
    icms = max(0.0, receita - cmv) * aliquota_icms
    total = federal + icms
    return total, (total / receita if receita > 0 else 0.0)
