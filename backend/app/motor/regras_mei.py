"""Regras MEI versionadas pelo calendário simulado.

O motor usa somente regras que tenham vigência verificável. A LC 238/2026
prevê novos tetos, mas condiciona os valores de 2027 e 2028 à previsão
orçamentária. Por isso, o simulador não antecipa tributos: até existir uma
confirmação oficial registrada, preserva o parâmetro vigente da turma e exibe
o aviso pedagógico correspondente.
"""

from .calendario import periodo

FONTE = "https://legis.senado.gov.br/norma/44276013/publicacao/44280206"
NORMA = "Lei Complementar 238/2026"
VERSAO = "lc-238-2026.1"
TETO_BASE = 81_000.0
TETOS_CONDICIONADOS = {2027: 110_000.0, 2028: 140_000.0}


def _ano_simulado(turma, rodada):
    cfg = turma.configuracao_simulacao or {}
    cal = periodo(cfg, rodada or turma.rodada_atual)
    return int(cal["inicio"][:4]) if cal else None


def _confirmacao_orcamentaria(cfg, ano):
    """Lê somente confirmação registrada pelo serviço oficial.

    A chave continua interna ao motor; o professor não escolhe qual regra
    tributária será aplicada. A rotina de fontes oficiais é quem poderá
    confirmá-la quando houver evidência normativa suficiente.
    """
    confirmacoes = cfg.get("confirmacoes_normativas", {})
    return bool(confirmacoes.get(f"LC238-{ano}-ORCAMENTO"))


def regras_mei(turma, rodada=None):
    cfg = turma.configuracao_simulacao or {}
    ano = _ano_simulado(turma, rodada)
    teto_base = float(getattr(turma, "teto_mei_anual", TETO_BASE) or TETO_BASE)
    teto = teto_base
    aplicacao_confirmada = False

    if ano in TETOS_CONDICIONADOS and _confirmacao_orcamentaria(cfg, ano):
        teto = TETOS_CONDICIONADOS[ano]
        aplicacao_confirmada = True

    # A exceção de até dois empregados é exclusivamente para a atividade rural
    # indicada pela norma; uma empresa comum conserva o limite geral de um.
    rural_elegivel = bool(cfg.get("atividade_rural")) and ano is not None and ano >= 2027
    limite_empregados = 2 if rural_elegivel else 1

    if ano in TETOS_CONDICIONADOS and not aplicacao_confirmada:
        estado = (
            "Parâmetro vigente da turma. A LC 238/2026 prevê novo teto, mas a "
            "condição orçamentária da vigência ainda não foi confirmada pelo motor."
        )
    elif aplicacao_confirmada:
        estado = "Regra oficial confirmada pelo motor para o calendário simulado."
    else:
        estado = "Parâmetro vigente da turma."

    return {
        "ano": ano,
        "teto_anual": teto,
        "limite_empregados": limite_empregados,
        "estado": estado,
        "norma": NORMA,
        "versao_regra": VERSAO,
        "publicada_em": "2026-10-21",
        "vigencia": (
            "A regra rural vigora a partir de 2027. Os tetos de R$ 110.000,00 (2027) "
            "e R$ 140.000,00 (a partir de 2028) dependem da condição orçamentária "
            "prevista na própria lei."
        ),
        "aplicacao_confirmada": aplicacao_confirmada,
        "condicoes": (
            "Art. 3º: os novos tetos dependem da consideração da renúncia de receita "
            "nas leis orçamentárias correspondentes."
        ),
        "fonte": FONTE,
    }
