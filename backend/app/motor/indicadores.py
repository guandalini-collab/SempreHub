"""Indicadores didáticos determinísticos; frações internas e snapshots por rodada."""
from decimal import Decimal, ROUND_HALF_UP


def disponibilidade_maquinas(maquinas, investimento):
    """Um único desgaste operacional por equipamento; valor contábil é independente."""
    cobertura = min(Decimal(1), Decimal(str(max(0, investimento))) / 1000)
    incremento = Decimal('.05') * (1 - cobertura)
    total = Decimal(0)
    disponivel = Decimal(0)
    for maquina in maquinas:
        # Compatibilidade: condição histórica vira risco uma única vez.
        anterior = Decimal(str(maquina.get('risco_quebra', 1 - maquina.get('condicao', 1))))
        anterior = min(Decimal(1), max(Decimal(0), anterior))
        risco = Decimal(0) if cobertura == 1 else min(Decimal(1), anterior + incremento)
        maquina['risco_quebra'] = float(risco)
        maquina['condicao'] = float(1 - risco)
        capacidade = Decimal(str(max(0, maquina.get('capacidade', 0))))
        total += capacidade
        disponivel += capacidade * (1 - risco)
    return float(disponivel / total) if total > 0 else 1.0


def oee(estado, manutencao, treinamento, funcionarios, maquinas, producao):
    anterior = estado.get('indicadores_didaticos', {})
    performance = Decimal(str(anterior.get('performance', 1)))
    defeito = Decimal(str(anterior.get('taxa_defeito', .02)))
    disponibilidade = Decimal(str(disponibilidade_maquinas(maquinas, manutencao)))
    if maquinas:
        if funcionarios > 0 and treinamento > 0:
            unidades = Decimal(str(treinamento)) / (100 * funcionarios)
            performance = min(Decimal(1), performance + Decimal('.02') * unidades)
            defeito = max(Decimal('.005'), defeito - Decimal('.005') * unidades)
        elif treinamento == 0:
            performance = max(Decimal(0), performance - Decimal('.005'))
    estado['indicadores_didaticos'] = {**anterior, 'risco_quebra': float(1 - disponibilidade), 'performance': float(performance), 'taxa_defeito': float(defeito)}
    qualidade = 1 - defeito
    return {'oee': float(disponibilidade * performance * qualidade) if maquinas and producao > 0 else None,
            'disponibilidade': float(disponibilidade), 'performance': float(performance), 'qualidade_oee': float(qualidade), 'taxa_defeito': float(defeito)}


def capacidades_producao(capacidade_nominal, funcionarios, produtividade, fator_rh, horas_extras, disponibilidade, performance):
    """Horas extras aumentam tempo; disponibilidade e performance reduzem rendimento."""
    horas = max(0, min(40, horas_extras)) if funcionarios > 0 else 0
    fator_tempo = 1 + horas / 220
    trabalho_regular = (1 + funcionarios) * produtividade * fator_rh
    trabalho_extra = funcionarios * horas / 220 * produtividade * fator_rh
    nominal_periodo = capacidade_nominal * fator_tempo
    disponivel = nominal_periodo * disponibilidade
    efetiva_maquinas = disponivel * performance
    return {'capacidade_nominal': capacidade_nominal, 'horas_regulares_por_pessoa': 220,
            'fator_tempo_maquinas': fator_tempo, 'capacidade_nominal_periodo': nominal_periodo,
            'capacidade_trabalho_regular': trabalho_regular, 'capacidade_trabalho_extra': trabalho_extra,
            'capacidade_maquinas_disponivel': disponivel, 'capacidade_maquinas_efetiva': efetiva_maquinas,
            'capacidade_produtiva': min(trabalho_regular + trabalho_extra, efetiva_maquinas)}


def enps(estado, funcionarios, salario, mercado, beneficio, horas_extras):
    historico = estado.setdefault('indicadores_didaticos', {})
    anteriores = historico.get('rodadas_horas_extras', 0)
    consecutivas = anteriores + 1 if horas_extras > 0 and funcionarios > 0 else 0
    historico['rodadas_horas_extras'] = consecutivas
    mod_salario = (1 if salario > mercado else -2 if salario < mercado else 0) if mercado > 0 else 0
    mod_beneficio = 1 if beneficio >= 150 else 0
    mod_he = -1 if consecutivas >= 2 else 0
    # Percentuais em inteiros, sem erro de ponto flutuante na distribuição.
    padrao = max(1, funcionarios * 2 // 5) if funcionarios else 0
    exigente = funcionarios * 2 // 5
    engajado = funcionarios - padrao - exigente
    limitar = lambda nota: max(0.0, min(10.0, nota))
    grupos = [
        {'perfil': 'PADRAO', 'quantidade': padrao,
         'nota': limitar(7 + mod_salario + mod_beneficio + mod_he)},
        {'perfil': 'EXIGENTE', 'quantidade': exigente,
         'nota': limitar(7 + (mod_salario * 1.5 if mod_salario < 0 else mod_salario) + mod_beneficio + mod_he * 1.5)},
        {'perfil': 'ENGAJADO', 'quantidade': engajado,
         'nota': limitar(7 + (mod_salario * 1.5 if mod_salario > 0 else mod_salario) + mod_beneficio * 1.5 + mod_he)},
    ]
    promotores = sum(g['quantidade'] for g in grupos if g['nota'] >= 9)
    neutros = sum(g['quantidade'] for g in grupos if 7 <= g['nota'] < 9)
    detratores = sum(g['quantidade'] for g in grupos if g['nota'] < 7)
    return {'enps': 100.0 * promotores / funcionarios - 100.0 * detratores / funcionarios if funcionarios else None,
            # Campo compatível: agora é a média ponderada das notas dos perfis.
            'enps_nota': sum(g['nota'] * g['quantidade'] for g in grupos) / funcionarios if funcionarios else None,
            'enps_perfis': grupos if funcionarios else [], 'enps_respondentes': funcionarios,
            'enps_modelo': 'deterministico_perfis_v2', 'enps_beneficio_minimo_por_funcionario': 150,
            'enps_referencia_salarial_valida': mercado > 0,
            'enps_promotores': promotores, 'enps_neutros': neutros,
            'enps_detratores': detratores, 'horas_extras_recorrentes': int(consecutivas >= 2)}


def otif(pedidos, atendidos, modal):
    """Um pedido didático por unidade; falhas inteiras conciliadas pela união."""
    def inteiro(valor):
        return int(Decimal(str(max(0, valor))).quantize(Decimal(1), rounding=ROUND_HALF_UP))

    total = inteiro(pedidos)
    entregues = min(total, inteiro(atendidos))
    falta = total - entregues
    atraso, incompleto, sobreposicao = {
        'ECONOMICO': (Decimal('.10'), Decimal('.05'), Decimal('.5')),
        'PADRAO': (Decimal('.04'), Decimal('.02'), Decimal('.3')),
        'RAPIDO': (Decimal(0), Decimal(0), Decimal(0)),
    }[modal]
    taxa = Decimal('.01') if modal == 'RAPIDO' else atraso + incompleto * (1 - sobreposicao)
    falhas_transporte = min(entregues, inteiro(entregues * taxa))
    # Arredondar a união primeiro evita que arredondamentos separados alterem o OTIF.
    incompletos_transporte = min(falhas_transporte, inteiro(entregues * incompleto))
    dupla = min(incompletos_transporte, inteiro(entregues * incompleto * sobreposicao))
    gerais = falhas_transporte if modal == 'RAPIDO' else 0
    atrasados = 0 if gerais else falhas_transporte - incompletos_transporte + dupla
    falhas = falta + falhas_transporte
    perfeitos = total - falhas
    return {
        'otif': perfeitos / total if total else None,
        'pedidos_totais': total, 'pedidos_despachados': entregues,
        'pedidos_nao_atendidos': falta, 'pedidos_atrasados': atrasados,
        'pedidos_incompletos': falta + incompletos_transporte,
        'pedidos_incompletos_transporte': incompletos_transporte,
        'pedidos_falha_dupla': dupla, 'pedidos_falhas_gerais': gerais,
        'pedidos_com_falha': falhas, 'pedidos_perfeitos': perfeitos,
        'taxa_falha_transporte': float(taxa),
        'convencao_pedidos': 'Uma unidade demandada representa um pedido didático.',
    }
