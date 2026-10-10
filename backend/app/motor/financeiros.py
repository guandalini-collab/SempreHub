"""Apresentação contábil e indicadores sustentados pelos snapshots mensais."""
from decimal import Decimal, ROUND_HALF_UP


def dinheiro(v):
    return float(Decimal(str(v)).quantize(Decimal('.01'), rounding=ROUND_HALF_UP))


def reconciliar_financeiros(balanco, estado, dre, rodada, taxa_cheque, compras=None, modo='TRADICIONAL'):
    # Saldo assinado é preservado no DFC e no campo legado; nunca vira segunda dívida.
    caixa = balanco['caixa']
    disponivel, cheque = max(0, caixa), max(0, -caixa)
    balanco.update(disponibilidades=disponivel, cheque_especial=cheque,
                   ativo_total=dinheiro(disponivel+balanco['receber']+balanco['estoques']+balanco['imobilizado']),
                   passivo_total=dinheiro(balanco['pagar']+balanco['divida']+cheque),
                   juros_cheque_proxima_rodada=dinheiro(cheque*taxa_cheque))
    def prazos(nome):
        titulos=estado.get(nome)
        if not isinstance(titulos,list) or any(not isinstance(t.get('vencimento'),(int,float)) for t in titulos):
            return None
        return (dinheiro(sum(t['valor'] for t in titulos if t['vencimento'] <= rodada+12)),
                dinheiro(sum(t['valor'] for t in titulos if t['vencimento'] > rodada+12)))
    receber,pagar=prazos('receber'),prazos('pagar')
    divida=balanco['divida']; vencimento=estado.get('vencimento_divida')
    divida_cp = 0 if not divida else (divida if vencimento <= rodada+12 else 0) if isinstance(vencimento,(int,float)) else None
    def razao(a,b):
        return a/b if b is not None and b>0 else None
    geral=razao(disponivel+balanco['receber']+balanco['estoques'],balanco['pagar']+divida+cheque) if receber is not None and pagar is not None else None
    pc=dinheiro(pagar[0]+divida_cp+cheque) if pagar is not None and divida_cp is not None else None
    ac=dinheiro(disponivel+receber[0]+balanco['estoques']) if receber is not None else None
    balanco.update(ativo_circulante=ac,passivo_circulante=pc,
                   realizavel_longo_prazo=receber[1] if receber is not None else None,
                   passivo_nao_circulante=dinheiro(pagar[1]+divida-divida_cp) if pagar is not None and divida_cp is not None else None)
    # Juros estão fora do EBIT; amortização de empréstimo não integra a DRE.
    ebit=dinheiro(dre['lucro_liquido']+dre['juros']) if 'juros' in dre and 'depreciacao' in dre else None
    ebitda=dinheiro(ebit+dre['depreciacao']+dre.get('amortizacao_ativos',0)) if ebit is not None else None
    atuais=lambda nome: dinheiro(sum(t['valor'] for t in estado.get(nome,[]) if t.get('origem')==rodada))
    pmr=razao(atuais('receber'),dre['receita']) if receber is not None else None
    pmp=razao(atuais('pagar'),compras) if pagar is not None and compras is not None else None
    # Classificação explícita do perfil tradicional, não inferida de valores ausentes.
    variaveis=('impostos','cmv','royalties','comissao_canal','frete','refugos')
    fixos=('folha','horas_extras','custos_fixos','marketing','pd','networking','rescisoes','multas','armazenagem','depreciacao','beneficios','treinamento','manutencao')
    margem=None;equilibrio=None;status='Dados indisponíveis'
    if modo=='TRADICIONAL' and all(k in dre for k in variaveis+fixos) and dre['receita']>0:
        margem=(dre['receita']-sum(dre[k] for k in variaveis))/dre['receita']
        if margem<=0:
            status='Não se aplica (Margem Negativa)' if margem<0 else 'Não se aplica (Margem Zero)'
        else:
            equilibrio=dinheiro(sum(dre[k] for k in fixos)/margem);status='Calculado'
    resultado = {'liquidez_corrente':razao(ac,pc) if ac is not None else None,
                 'liquidez_seca':razao(ac-balanco['estoques'],pc) if ac is not None else None,
                 'liquidez_imediata':razao(disponivel,pc), 'liquidez_geral':geral,
                 'ebit':ebit, 'ebitda':ebitda, 'pmr':pmr*30 if pmr is not None else None,
                 'pmp':pmp*30 if pmp is not None else None, 'compras_mes':compras,
                 'margem_contribuicao':margem, 'ponto_equilibrio':equilibrio,
                 'ponto_equilibrio_status':status}
    if modo == 'TRADICIONAL':
        resultado['ltv'] = None
    return resultado
