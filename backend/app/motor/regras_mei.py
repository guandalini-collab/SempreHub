"""LC 238/2026: cronograma publicado, com condições orçamentárias explícitas."""
from .calendario import periodo

FONTE = 'https://legis.senado.gov.br/norma/44276013/publicacao/44280206'


def regras_mei(turma, rodada=None):
    cfg = turma.configuracao_simulacao or {}
    cal = periodo(cfg, rodada or turma.rodada_atual)
    ano = int(cal['inicio'][:4]) if cal else None
    projetado = bool(cfg.get('cenario_mei_plp186')) and ano is not None and ano >= 2027
    teto = (110000.0 if ano == 2027 else 140000.0) if projetado else turma.teto_mei_anual
    return {'ano': ano, 'teto_anual': teto, 'limite_empregados': 2 if projetado and cfg.get('atividade_rural') else 1,
            'estado': 'Estimativa do Modelo · LC 238/2026: cronograma publicado, aplicação condicionada ao art. 3º; condição orçamentária não verificada pelo motor' if projetado else 'Parâmetro da turma',
            'norma':'Lei Complementar 238/2026', 'publicada_em':'2026-10-21',
            'condicoes':'Art. 3º: consideração da renúncia de receita nas leis orçamentárias de 2027 a 2029.', 'fonte': FONTE}
