from __future__ import annotations

"""Calendário econômico semanal e sazonalidade pedagógica explícita.

O calendário não usa datas reais de entrega das atividades. Cada rodada representa
sete dias do calendário *simulado*. Eventos nacionais conhecidos são calculados de
forma determinística a partir da data inicial da turma, para que uma decisão seja
comparável entre as empresas da mesma rodada.
"""
from calendar import monthrange
from copy import deepcopy
from datetime import date, timedelta

VERSAO_SEMANAL = '3.2.0-seasonal-sector-calendar'


def _pascoa(ano: int) -> date:
    """Domingo de Páscoa pelo algoritmo gregoriano de Meeus/Jones/Butcher."""
    a = ano % 19
    b, c = divmod(ano, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes = (h + l - 7 * m + 114) // 31
    dia = (h + l - 7 * m + 114) % 31 + 1
    return date(ano, mes, dia)


def _segundo_domingo(ano: int, mes: int) -> date:
    primeiro = date(ano, mes, 1)
    return primeiro + timedelta(days=(6 - primeiro.weekday()) % 7 + 7)


def _black_friday(ano: int) -> date:
    novembro = date(ano, 11, 30)
    return novembro - timedelta(days=(novembro.weekday() - 4) % 7)


def _primeira_segunda(ano: int, mes: int) -> date:
    primeiro = date(ano, mes, 1)
    return primeiro + timedelta(days=(-primeiro.weekday()) % 7)


def _eventos_do_ano(ano: int) -> list[dict]:
    """Marcos brasileiros que podem alterar a procura, não feriados de trabalho."""
    pascoa = _pascoa(ano)
    carnaval = pascoa - timedelta(days=47)
    return [
        {"nome": "Volta às aulas", "data": _primeira_segunda(ano, 2), "pico": .45, "antec": 28, "pos": 7},
        {"nome": "Carnaval", "data": carnaval, "pico": .35, "antec": 21, "pos": 7},
        {"nome": "Semana do Consumidor", "data": date(ano, 3, 15), "pico": .25, "antec": 14, "pos": 3},
        {"nome": "Páscoa", "data": pascoa, "pico": .50, "antec": 35, "pos": 7},
        {"nome": "Dia das Mães", "data": _segundo_domingo(ano, 5), "pico": .50, "antec": 35, "pos": 7},
        {"nome": "Dia dos Namorados", "data": date(ano, 6, 12), "pico": .45, "antec": 28, "pos": 7},
        {"nome": "Dia dos Pais", "data": _segundo_domingo(ano, 8), "pico": .35, "antec": 28, "pos": 7},
        {"nome": "Dia das Crianças", "data": date(ano, 10, 12), "pico": .40, "antec": 35, "pos": 7},
        {"nome": "Black Friday", "data": _black_friday(ano), "pico": .55, "antec": 42, "pos": 4},
        {"nome": "Natal", "data": date(ano, 12, 25), "pico": .65, "antec": 42, "pos": 9},
        {"nome": "Ano-Novo", "data": date(ano + 1, 1, 1), "pico": .30, "antec": 14, "pos": 7},
    ]


# Intensidade relativa por setor. Zero significa que o marco continua visível no
# calendário, porém não altera automaticamente a procura daquele segmento.
PESOS_SETORIAIS = {
    "Eletrônicos e Tecnologia": {"Semana do Consumidor": .8, "Dia das Crianças": .7, "Black Friday": 1, "Natal": .8},
    "Alimentos e Bebidas": {"Carnaval": .7, "Páscoa": 1, "Dia das Mães": .5, "Natal": 1, "Ano-Novo": .8},
    "Vestuário e Moda": {"Dia das Mães": .8, "Dia dos Namorados": 1, "Dia dos Pais": .6, "Black Friday": .8, "Natal": 1},
    "Cosméticos e Beleza": {"Dia das Mães": 1, "Dia dos Namorados": .6, "Black Friday": .7, "Natal": 1},
    "Móveis e Decoração": {"Semana do Consumidor": .4, "Black Friday": .8, "Natal": .3},
    "Automotivo": {"Semana do Consumidor": .5, "Black Friday": .5, "Natal": .2},
    "Esportes e Fitness": {"Ano-Novo": 1, "Carnaval": .5, "Dia dos Pais": .4, "Black Friday": .5},
    "Saúde e Bem-estar": {"Ano-Novo": .9, "Dia das Mães": .4, "Black Friday": .3},
    "Educação e Cursos": {"Volta às aulas": 1, "Semana do Consumidor": .2},
    "Pet Care": {"Black Friday": .4, "Natal": .6},
    "Construção e Materiais": {"Semana do Consumidor": .3, "Black Friday": .6},
    "Entretenimento e Mídia": {"Carnaval": 1, "Dia das Crianças": .8, "Natal": .7, "Ano-Novo": .6},
}


def _peso_evento(nome: str, setor: str | None, perfil: str) -> float:
    if setor:
        return PESOS_SETORIAIS.get(setor, {}).get(nome, 0.0)
    # Perfil é o fallback das turmas que ainda não têm uma pesquisa de mercado
    # publicada. O perfil neutro preserva o comportamento histórico sem viés.
    if perfil == "VAREJO":
        return .70 if nome not in {"Carnaval", "Volta às aulas"} else .30
    if perfil == "ALIMENTACAO":
        return PESOS_SETORIAIS["Alimentos e Bebidas"].get(nome, .08)
    if perfil == "SERVICOS":
        return .18 if nome in {"Ano-Novo", "Semana do Consumidor", "Volta às aulas"} else .08
    return 0.0


def _contribuicao(dia: date, evento: dict, peso: float) -> tuple[float, str | None]:
    """Retorna o efeito diário e a fase do evento, sem aleatoriedade."""
    if peso <= 0:
        return 0.0, None
    distancia = (evento["data"] - dia).days
    if 0 <= distancia <= evento["antec"]:
        # A procura cresce gradualmente até a data do marco.
        return evento["pico"] * peso * (1 - distancia / (evento["antec"] + 7)), "preparação"
    if -evento["pos"] <= distancia < 0:
        # Depois da data, parte da compra foi antecipada; não é uma crise.
        return -.12 * peso * (1 - abs(distancia) / (evento["pos"] + 1)), "pós-evento"
    return 0.0, None


def _orientacao(fase: str) -> str:
    if fase == "preparação":
        return "Revise procura, estoque/capacidade, orçamento de campanha e prazo de entrega antes do pico."
    return "Revise caixa, estoque remanescente e capacidade antes de manter o ritmo do período anterior."


def periodo(config, rodada):
    if config.get('periodicidade', 'MENSAL') != 'SEMANAL':
        return None
    primeira = config.get('rodada_inicio_calendario', 1)
    if rodada < primeira:
        return None
    inicio = date.fromisoformat(config['data_inicio_simulada']) + timedelta(days=7 * (rodada - primeira))
    dias = [inicio + timedelta(days=i) for i in range(7)]
    fator = sum(1 / monthrange(d.year, d.month)[1] for d in dias)
    perfil = config.get('perfil_sazonal', 'NEUTRO')
    setor = config.get('setor_mercado')
    eventos_ano = [evento for ano in range(inicio.year - 1, inicio.year + 2) for evento in _eventos_do_ano(ano)]
    efeitos: dict[tuple[str, str], list[float]] = {}
    for dia in dias:
        for evento in eventos_ano:
            valor, fase = _contribuicao(dia, evento, _peso_evento(evento['nome'], setor, perfil))
            if fase:
                efeitos.setdefault((evento['nome'], fase), []).append(valor)

    detalhes_eventos = []
    for (nome, fase), valores in efeitos.items():
        evento = next(e for e in eventos_ano if e['nome'] == nome)
        impacto = round(sum(valores) / 7, 4)
        if abs(impacto) < .001:
            continue
        detalhes_eventos.append({
            "nome": nome,
            "data": evento['data'].isoformat(),
            "fase": fase,
            "impacto_demanda": impacto,
            "orientacao": _orientacao(fase),
            "fonte": "Calendário civil brasileiro · Estimativa do Modelo",
        })
    detalhes_eventos.sort(key=lambda item: (item['data'], item['nome']))
    demanda = max(.60, min(1.75, 1 + sum(item['impacto_demanda'] for item in detalhes_eventos)))
    eventos = [f"{'Pós-' if item['fase'] == 'pós-evento' else ''}{item['nome']}" for item in detalhes_eventos]
    proximos = []
    for evento in sorted(eventos_ano, key=lambda e: e['data']):
        if not inicio <= evento['data'] <= inicio + timedelta(days=90):
            continue
        peso = _peso_evento(evento['nome'], setor, perfil)
        if peso <= 0:
            continue
        proximos.append({
            "nome": evento['nome'], "data": evento['data'].isoformat(),
            "impacto": "Sazonalidade setorial prevista", "peso_setorial": peso,
        })

    return {
        'periodicidade': 'SEMANAL', 'inicio': inicio.isoformat(), 'fim': dias[-1].isoformat(),
        'dias': 7, 'fator_mensal': fator, 'semana_iso': inicio.isocalendar().week,
        'ano_iso': inicio.isocalendar().year, 'ano_fiscal': dias[-1].year,
        'meses': [{'data': d.isoformat(), 'peso_mensal': 1 / monthrange(d.year, d.month)[1]} for d in dias],
        'sazonalidade': {
            'estado': 'Estimativa do Modelo', 'perfil': perfil, 'setor': setor,
            'eventos': eventos, 'detalhes_eventos': detalhes_eventos,
            'demanda': round(demanda, 4),
            'insumos': round(1 + max(0, demanda - 1) * .08, 4),
            'frete': round(1 + max(0, demanda - 1) * .20, 4),
        },
        'proximos_eventos': proximos[:5],
    }


def adaptar(parametros, rodada):
    p = deepcopy(parametros)
    if '_calendario' in p:
        return p
    cal = periodo(p.get('configuracao_simulacao') or {}, rodada)
    if not cal:
        return p
    # Startups sofrem a procura sazonal, mas não recebem custos fictícios de
    # insumos ou frete físico. A infraestrutura digital já é tratada à parte.
    if p.get('modo_jogo') == 'STARTUP':
        cal['sazonalidade']['insumos'] = 1.0
        cal['sazonalidade']['frete'] = 1.0
    from ..schemas import ConfiguracaoSimulacao
    p['configuracao_simulacao'] = ConfiguracaoSimulacao.model_validate(p.get('configuracao_simulacao') or {}).model_dump()
    for k, v in {'custos_fixos_mensais': 1500, 'produtividade_por_pessoa': 120, 'demanda_base_por_empresa': 220, 'das_mei_mensal': 82.05, 'taxa_juros_mensal': .025, 'taxa_cheque_especial': .08, 'crescimento_mercado_mensal': .01}.items():
        p.setdefault(k, v)
    p['_calendario'] = cal
    f = cal['fator_mensal']
    for k in ('custos_fixos_mensais', 'produtividade_por_pessoa', 'demanda_base_por_empresa', 'das_mei_mensal'):
        if k in p:
            p[k] *= f
    for k in ('taxa_juros_mensal', 'taxa_cheque_especial', 'crescimento_mercado_mensal'):
        if k in p:
            p[k] = (1 + p[k]) ** f - 1
    cfg = p['configuracao_simulacao']
    for k in ('custo_armazenagem', 'custo_nuvem_cliente'):
        if k in cfg:
            cfg[k] *= f
    if 'churn_base' in cfg:
        cfg['churn_base'] = 1 - (1 - cfg['churn_base']) ** f
    for k in ('frete_rapido', 'frete_padrao', 'frete_economico', 'custo_frete_km'):
        if k in cfg:
            cfg[k] *= cal['sazonalidade']['frete']
    return p
