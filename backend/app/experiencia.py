"""Progresso e conquistas derivados do histórico; não altera o motor financeiro."""

def jornada_empresa(empresa):
    resultados = sorted(empresa.resultados, key=lambda r: r.rodada)
    decisoes = [d for d in empresa.decisoes if not d.automatica]
    lucro = lambda r: r.lucro_liquido
    positivas = [r for r in resultados if lucro(r) > 0]
    viradas = [b for a, b in zip(resultados, resultados[1:]) if lucro(a) < 0 < lucro(b)]
    crescimento = [b for a, b in zip(resultados, resultados[1:]) if b.participacao_mercado > a.participacao_mercado]
    marcos = [
        ('primeiro-movimento', 'Primeiro movimento', 'Envie sua primeira decisão.', min((d.rodada for d in decisoes), default=None)),
        ('empresa-em-acao', 'Empresa em ação', 'Conclua sua primeira rodada.', resultados[0].rodada if resultados else None),
        ('resultado-positivo', 'No azul', 'Encerre uma rodada com lucro positivo.', positivas[0].rodada if positivas else None),
        ('virada', 'Virada financeira', 'Passe de prejuízo para lucro na rodada seguinte.', viradas[0].rodada if viradas else None),
        ('presenca', 'Presença de mercado', 'Aumente sua participação entre duas rodadas.', crescimento[0].rodada if crescimento else None),
    ]
    feed = []
    for r in reversed(resultados[-6:]):
        feed.append({'id': f'resultado-{r.rodada}', 'rodada': r.rodada,
                     'titulo': 'Sua empresa fechou no azul' if lucro(r) > 0 else 'O mercado pediu ajustes' if lucro(r) < 0 else 'Receitas e despesas empataram',
                     'texto': 'Confira vendas, despesas e resultado antes de preparar a próxima decisão.',
                     'lucro': lucro(r), 'participacao': r.participacao_mercado})
    return {'rodadas_concluidas': len(resultados), 'conquistas': [
        {'id': id, 'titulo': titulo, 'descricao': descricao, 'rodada': rodada, 'obtida': rodada is not None}
        for id, titulo, descricao, rodada in marcos], 'feed': feed}
