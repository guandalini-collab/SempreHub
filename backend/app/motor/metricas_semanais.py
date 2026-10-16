"""Telemetria didática determinística, registrada somente em novos fechamentos.

Não altera demanda, vendas, DRE ou notas. Não representa pesquisa ou tráfego real.
"""

VERSAO = '1.0.0-telemetria-didatica'


def gerar_metricas(apuracao, dias=30):
    op = apuracao['detalhes'].get('operacao', {})
    dre = apuracao['dre']
    startup = apuracao['detalhes'].get('modo') == 'STARTUP'
    vendas = max(0, int(apuracao['vendas']))
    marketing = max(0, dre.get('marketing', 0))
    # A coorte sintética possui um comprador por unidade (não clientes reais únicos).
    novos = op.get('clientes_adquiridos', 0) if startup else vendas
    pedidos = novos if startup else vendas
    # CPC de referência R$ 2; tráfego orgânico mínimo de 5 contatos por pedido.
    cliques = int(marketing / 2)
    leads = max(pedidos * 5, cliques)
    satisfacao = max(0, min(100, apuracao.get('satisfacao', 80)))
    promotores = int(vendas * satisfacao / 100)
    detratores = min(vendas - promotores, int(vendas * (100 - satisfacao) / 200))
    funcionarios = apuracao['funcionarios']
    horas = funcionarios * 8 * dias * 5 / 7
    enps = op.get('enps')
    ausencia = min(.10, max(0, -(enps or 0)) / 1000)
    bases = dict(marketing=marketing, anuncios=marketing, novos_clientes=novos,
                 pedidos=pedidos, leads=leads, cliques=cliques,
                 promotores=promotores, neutros=vendas-promotores-detratores, detratores=detratores,
                 horas_contratadas=horas, horas_ausencia=horas*ausencia,
                 horas_extras_realizadas=funcionarios*op.get('horas_extras', 0))
    if startup:
        bases.update(cancelamentos=op.get('clientes_perdidos', 0), base_recorrentes=op.get('clientes_iniciais', 0))
    else:
        producao = op.get('producao_real', 0)
        bases.update(ciclo_minutos=horas*(1-ausencia)*60 if producao else 0,
                     ciclos_concluidos=producao, custo_logistico=dre.get('frete',0)+dre.get('armazenagem',0),
                     pedidos_expedidos=op.get('pedidos_despachados',0),
                     picking_minutos=2 + 3*(1-satisfacao/100),
                     itens_auditados=op.get('pedidos_despachados',0),
                     itens_conformes=max(0,op.get('pedidos_despachados',0)-op.get('pedidos_incompletos_transporte',0)))
    return {'versao': VERSAO, 'bases': bases,
            'convencao': 'Coorte sintética: uma unidade vendida por comprador; tráfego, pesquisa, ausências, ciclos e auditoria de expedição são estimativas didáticas. Frete e armazenagem são os custos logísticos disponíveis.'}
