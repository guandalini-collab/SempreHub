"""Cenário didático do PLP 186/2026. Projeto pendente: não é regra legal vigente."""
from .calendario import periodo

FONTE = 'https://www.presidencia.gov.br/ccivil_03/projetos/ato_2023_2026/2026/plp/plp-186.htm'


def regras_mei(turma, rodada=None):
    cfg = turma.configuracao_simulacao or {}
    cal = periodo(cfg, rodada or turma.rodada_atual)
    ano = int(cal['inicio'][:4]) if cal else None
    projetado = bool(cfg.get('cenario_mei_plp186')) and ano is not None and ano >= 2027
    teto = (110000.0 if ano == 2027 else 140000.0) if projetado else turma.teto_mei_anual
    return {'ano': ano, 'teto_anual': teto, 'limite_empregados': 2 if projetado and cfg.get('atividade_rural') else 1,
            'estado': 'Estimativa do Modelo · cenário PLP 186/2026, ainda não vigente' if projetado else 'Parâmetro da turma', 'fonte': FONTE}
